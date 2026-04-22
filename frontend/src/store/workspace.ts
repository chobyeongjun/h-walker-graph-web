// Zustand workspace store — per HANDOFF §1
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { SEED_CELLS } from '../data/seedCells';
import { SEED_DATASETS } from '../data/seedDatasets';
import { CANONICAL_RECIPES } from '../data/canonicalRecipes';
import {
  analyzeDataset, computeMetric, renderGraph, runStats,
  type ComputeMetricKey, type StatOpKey, type StatsResponse, type ComputeResponse,
  type AnalyzeResponse, type AnalysisPayload,
} from '../api';

export type CellType = 'graph' | 'stat' | 'compute' | 'llm';

export interface Cell {
  id: string;
  type: CellType;
  graph?: string;
  op?: string;
  metric?: string;
  dsIds: string[];
  preset?: string;
  strideAvg?: boolean;
  fmt?: 'apa' | 'ieee' | 'csv';
  inputs?: { a: string; b: string };
  title?: string;
  // LLM cell extras
  prompt?: string;
  refs?: string[];
  answer?: { text: string[]; spawns?: Array<{ label: string; action: string }> };
  // Phase 2B: live backend state
  loading?: boolean;
  error?: string;
  computeData?: ComputeResponse;
  statData?: StatsResponse;
  previewBlobUrl?: string;
  previewVariant?: 'col1' | 'col2' | 'onehalf';
  // Phase 1: multi-dataset overlay. When `series` has ≥ 2 entries, the
  // graph renders as a multi-subject overlay with one colored trace per
  // entry. dsIds mirrors `series[].dsId` for backwards compat + filtering.
  series?: Array<{ dsId: string; label?: string; color?: string }>;
}

export interface DatasetColumn {
  name: string;
  unit: string;
  mapped?: string;
  mappedManual?: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  tag: string;
  kind: 'force' | 'imu' | 'cop' | 'emg' | 'trials' | 'mixed';
  rows: number;
  dur: string;
  hz: string;
  cols: DatasetColumn[];
  active: boolean;
  recipeState: Record<string, boolean>;
  // Phase 2B: analysis state
  analysis?: AnalyzeResponse;
  analyzing?: boolean;
  analyzeError?: string;
}

export type DrawerKind = null | 'history' | 'exports' | 'stats' | 'settings';

export interface HistoryEntry {
  id: string;
  ts: number;                // unix ms
  kind: 'upload' | 'apply' | 'add' | 'remove' | 'run' | 'preset' | 'chat' | 'tool';
  label: string;
  actor: 'you' | 'Claude';
  meta?: Record<string, unknown>;
}

interface WorkspaceState {
  cells: Cell[];
  datasets: Dataset[];
  currentPreset: string;
  globalPreset: string;
  pageTitle: string;
  history: HistoryEntry[];
  drawer: DrawerKind;
  focusCellId: string | null;
  cmdkOpen: boolean;
  mapperOpen: boolean;
  mapperDsId: string | null;
  helpOpen: boolean;
  toast: { msg: string; id: number } | null;
  runAllBusy: boolean;

  addCell: (c: Cell, at?: number) => void;
  updateCell: (id: string, patch: Partial<Cell>) => void;
  removeCell: (id: string) => void;
  duplicateCell: (id: string) => void;
  reorderCells: (from: number, to: number) => void;

  addDataset: (d: Dataset) => void;
  removeDataset: (id: string) => void;
  setActiveDataset: (id: string) => void;
  toggleRecipe: (dsId: string, recipeId: string) => void;
  applyRecipes: (dsId: string) => Promise<void>;
  analyzeIfNeeded: (dsId: string) => Promise<AnalyzeResponse | undefined>;

  runCompute: (cellId: string) => Promise<void>;
  runStat: (cellId: string) => Promise<void>;
  runPreview: (cellId: string, variant?: 'col1' | 'col2' | 'onehalf') => Promise<void>;
  runCell: (cellId: string) => Promise<void>;
  runAll: () => Promise<void>;

  setCurrentPreset: (p: string) => void;
  setGlobalPreset: (p: string) => void;
  setPageTitle: (t: string) => void;

  openDrawer: (k: DrawerKind) => void;
  closeDrawer: () => void;
  toggleCmdK: (v?: boolean) => void;
  openMapper: (dsId: string) => void;
  closeMapper: () => void;
  toggleHelp: (v?: boolean) => void;
  focusCell: (id: string | null) => void;
  showToast: (msg: string) => void;

  logHistory: (entry: Omit<HistoryEntry, 'id' | 'ts'>) => void;
  clearHistory: () => void;
}

let _toastSeq = 0;
let _cellSeq = 0;
const nextCellId = () => {
  _cellSeq = (_cellSeq + 1) % 10000;
  return `c${Date.now().toString(36)}${_cellSeq.toString(36)}`;
};

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      cells: SEED_CELLS,
      datasets: SEED_DATASETS,
      currentPreset: 'ieee',
      globalPreset: 'ieee',
      pageTitle: 'Pilot subject 03 · Treadmill 0.8 m/s',
      history: [],
      drawer: null,
      focusCellId: null,
      cmdkOpen: false,
      mapperOpen: false,
      mapperDsId: null,
      helpOpen: false,
      toast: null,
      runAllBusy: false,

      logHistory: (entry) => set((s) => {
        const next: HistoryEntry = {
          id: 'h' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5),
          ts: Date.now(),
          ...entry,
        };
        // Keep the most recent 200 entries
        const history = [next, ...s.history].slice(0, 200);
        return { history };
      }),
      clearHistory: () => set({ history: [] }),

      addCell: (c, at) => set((s) => {
        const cells = [...s.cells];
        if (at == null) cells.push(c);
        else cells.splice(at, 0, c);
        return { cells };
      }),
      updateCell: (id, patch) => set((s) => ({
        cells: s.cells.map((c) => (c.id === id ? { ...c, ...patch } : c)),
      })),
      removeCell: (id) => set((s) => {
        const cell = s.cells.find((c) => c.id === id);
        if (cell?.previewBlobUrl) URL.revokeObjectURL(cell.previewBlobUrl);
        return { cells: s.cells.filter((c) => c.id !== id) };
      }),
      duplicateCell: (id) => set((s) => {
        const idx = s.cells.findIndex((c) => c.id === id);
        if (idx < 0) return {};
        const src = s.cells[idx];
        // Don't copy live state/blob URLs — re-run on demand
        const { loading: _l, error: _e, computeData: _cd, statData: _sd,
                previewBlobUrl: _pb, ...rest } = src;
        void _l; void _e; void _cd; void _sd; void _pb;
        const copy: Cell = { ...rest, id: nextCellId() };
        const cells = [...s.cells];
        cells.splice(idx + 1, 0, copy);
        return { cells };
      }),
      reorderCells: (from, to) => set((s) => {
        const cells = [...s.cells];
        const [m] = cells.splice(from, 1);
        cells.splice(to, 0, m);
        return { cells };
      }),

      addDataset: (d) => {
        set((s) => ({ datasets: [...s.datasets, d] }));
        get().logHistory({
          kind: 'upload', actor: 'you',
          label: `Imported ${d.name} (${d.rows.toLocaleString()} rows, ${d.kind})`,
          meta: { dsId: d.id, kind: d.kind },
        });
      },
      removeDataset: (id) => {
        const d = get().datasets.find((x) => x.id === id);
        set((s) => ({ datasets: s.datasets.filter((x) => x.id !== id) }));
        if (d) get().logHistory({
          kind: 'remove', actor: 'you',
          label: `Removed dataset ${d.name}`,
        });
      },
      setActiveDataset: (id) => set((s) => ({
        datasets: s.datasets.map((d) => ({ ...d, active: d.id === id })),
      })),
      toggleRecipe: (dsId, recipeId) => set((s) => ({
        datasets: s.datasets.map((d) =>
          d.id === dsId ? { ...d, recipeState: { ...d.recipeState, [recipeId]: !d.recipeState[recipeId] } } : d,
        ),
      })),

      analyzeIfNeeded: async (dsId) => {
        const ds = get().datasets.find((d) => d.id === dsId);
        if (!ds) return undefined;
        if (ds.analysis) return ds.analysis;
        set((s) => ({
          datasets: s.datasets.map((d) =>
            d.id === dsId ? { ...d, analyzing: true, analyzeError: undefined } : d,
          ),
        }));
        try {
          const payload = await analyzeDataset(dsId);
          set((s) => ({
            datasets: s.datasets.map((d) =>
              d.id === dsId ? { ...d, analysis: payload, analyzing: false } : d,
            ),
          }));
          return payload;
        } catch (e) {
          const msg = (e as Error).message;
          set((s) => ({
            datasets: s.datasets.map((d) =>
              d.id === dsId ? { ...d, analyzing: false, analyzeError: msg } : d,
            ),
          }));
          get().showToast(`Analyze failed: ${msg}`);
          return undefined;
        }
      },

      applyRecipes: async (dsId) => {
        const ds = get().datasets.find((d) => d.id === dsId);
        if (!ds) return;
        const recipes = CANONICAL_RECIPES[ds.kind] || CANONICAL_RECIPES.force;
        const chosen = recipes.filter((r) => ds.recipeState[r.id] ?? r.default);
        if (chosen.length === 0) {
          get().showToast('No recipes selected');
          return;
        }

        // Kick off analyzer cache warming (non-blocking for graph cells)
        const analyzePromise = get().analyzeIfNeeded(dsId);

        const newCells: Cell[] = [];
        for (const r of chosen) {
          const id = nextCellId();
          if (r.type === 'graph' && r.graph) {
            newCells.push({
              id, type: 'graph', graph: r.graph,
              dsIds: [dsId],
              strideAvg: r.graph === 'force_avg',
              loading: true,
            });
          } else if (r.type === 'compute' && r.compute) {
            newCells.push({
              id, type: 'compute', metric: r.compute,
              dsIds: [dsId],
              loading: true,
            });
          }
        }
        set((s) => ({ cells: [...s.cells, ...newCells] }));
        get().logHistory({
          kind: 'apply', actor: 'you',
          label: `Applied ${newCells.length} recipe cells for ${ds.name}`,
          meta: { dsId, count: newCells.length },
        });

        await analyzePromise;

        // Fire requests in parallel
        await Promise.all(newCells.map((c) => get().runCell(c.id)));
        get().showToast(`Applied ${newCells.length} cells for ${ds.name}`);
      },

      runCell: async (cellId) => {
        const cell = get().cells.find((c) => c.id === cellId);
        if (!cell) return;
        if (cell.type === 'compute') return get().runCompute(cellId);
        if (cell.type === 'stat') return get().runStat(cellId);
        if (cell.type === 'graph') return get().runPreview(cellId);
      },

      runCompute: async (cellId) => {
        const cell = get().cells.find((c) => c.id === cellId);
        if (!cell || cell.type !== 'compute' || !cell.metric || !cell.dsIds[0]) return;
        get().updateCell(cellId, { loading: true, error: undefined });
        try {
          const data = await computeMetric({
            dataset_id: cell.dsIds[0],
            metric: cell.metric as ComputeMetricKey,
          });
          get().updateCell(cellId, { loading: false, computeData: data });
        } catch (e) {
          get().updateCell(cellId, { loading: false, error: (e as Error).message });
        }
      },

      runStat: async (cellId) => {
        const cell = get().cells.find((c) => c.id === cellId);
        if (!cell || cell.type !== 'stat' || !cell.op) return;
        get().updateCell(cellId, { loading: true, error: undefined });
        try {
          const dsId = cell.dsIds[0];
          const a_col = cell.inputs?.a?.trim();
          const b_col = cell.inputs?.b?.trim();
          if (!dsId || !a_col) {
            throw new Error('dataset_id + a_col required');
          }
          const needsB = cell.op !== 'shapiro' && cell.op !== 'anova1';
          const data = await runStats({
            op: cell.op as StatOpKey,
            dataset_id: dsId,
            a_col,
            b_col: needsB ? b_col : undefined,
          });
          get().updateCell(cellId, { loading: false, statData: data });
        } catch (e) {
          get().updateCell(cellId, { loading: false, error: (e as Error).message });
        }
      },

      runPreview: async (cellId, variant) => {
        const cell = get().cells.find((c) => c.id === cellId);
        if (!cell || cell.type !== 'graph' || !cell.graph) return;
        const preset = cell.preset || get().globalPreset;
        const v = variant || cell.previewVariant || 'col2';
        get().updateCell(cellId, { loading: true, error: undefined });
        try {
          // Phase 1: multi-dataset overlay when series present
          const seriesList: Array<{ dsId: string; label?: string; color?: string }> =
            (cell.series && cell.series.length > 0)
              ? cell.series
              : cell.dsIds.map((id) => ({ dsId: id }));
          const datasets = seriesList.length >= 2
            ? seriesList.map((s) => ({ id: s.dsId, label: s.label, color: s.color }))
            : undefined;
          const blob = await renderGraph({
            template: cell.graph,
            preset,
            variant: v,
            format: 'svg',
            dataset_id: datasets ? undefined : seriesList[0]?.dsId,
            datasets,
            stride_avg: !!cell.strideAvg,
            title: cell.title || '',
          });
          // Revoke old preview URL
          if (cell.previewBlobUrl) URL.revokeObjectURL(cell.previewBlobUrl);
          const url = URL.createObjectURL(blob);
          get().updateCell(cellId, {
            loading: false,
            previewBlobUrl: url,
            previewVariant: v,
          });
        } catch (e) {
          get().updateCell(cellId, { loading: false, error: (e as Error).message });
        }
      },

      runAll: async () => {
        if (get().runAllBusy) return;
        set({ runAllBusy: true });
        try {
          const cells = get().cells.filter((c) => c.type !== 'llm' && c.dsIds[0]);
          const dsIds = Array.from(new Set(cells.flatMap((c) => c.dsIds))).filter(Boolean);
          await Promise.all(dsIds.map((id) => get().analyzeIfNeeded(id)));
          await Promise.all(cells.map((c) => get().runCell(c.id)));
          get().logHistory({
            kind: 'run', actor: 'you',
            label: `Ran ALL · ${cells.length} cells across ${dsIds.length} datasets`,
          });
          get().showToast(`Ran ${cells.length} cells across ${dsIds.length} datasets`);
        } finally {
          set({ runAllBusy: false });
        }
      },

      setCurrentPreset: (p) => set({ currentPreset: p }),
      setGlobalPreset: (p) => {
        const prev = get().globalPreset;
        set({ globalPreset: p, currentPreset: p });
        if (prev !== p) {
          get().logHistory({
            kind: 'preset', actor: 'you',
            label: `Journal preset → ${p.toUpperCase()}`,
            meta: { from: prev, to: p },
          });
        }
      },
      setPageTitle: (t) => set({ pageTitle: t }),

      openDrawer: (k) => set({ drawer: k }),
      closeDrawer: () => set({ drawer: null }),
      toggleCmdK: (v) => set((s) => ({ cmdkOpen: v ?? !s.cmdkOpen })),
      openMapper: (dsId) => set({ mapperOpen: true, mapperDsId: dsId }),
      closeMapper: () => set({ mapperOpen: false, mapperDsId: null }),
      toggleHelp: (v) => set((s) => ({ helpOpen: v ?? !s.helpOpen })),
      focusCell: (id) => set({ focusCellId: id }),
      showToast: (msg) => set({ toast: { msg, id: ++_toastSeq } }),
    }),
    {
      name: 'hw_workspace_v3',
      // Strip live (non-serializable) state before persisting
      partialize: (s) => ({
        cells: s.cells.map((c) => {
          const { loading: _l, error: _e, computeData: _cd, statData: _sd,
                  previewBlobUrl: _p, ...rest } = c;
          void _l; void _e; void _cd; void _sd; void _p;
          return rest;
        }),
        datasets: s.datasets.map((d) => {
          const { analyzing: _a, analyzeError: _ae, analysis: _an, ...rest } = d;
          void _a; void _ae; void _an;
          return rest;
        }),
        currentPreset: s.currentPreset,
        globalPreset: s.globalPreset,
        pageTitle: s.pageTitle,
        history: s.history,
      }),
    },
  ),
);

// Re-export for components that need payload types
export type { AnalysisPayload };
