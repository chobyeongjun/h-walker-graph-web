// Zustand workspace store — per HANDOFF §1
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { SEED_CELLS } from '../data/seedCells';
import { SEED_DATASETS } from '../data/seedDatasets';

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
  kind: 'force' | 'imu' | 'cop' | 'emg' | 'trials';
  rows: number;
  dur: string;
  hz: string;
  cols: DatasetColumn[];
  active: boolean;
  recipeState: Record<string, boolean>;
}

export type WorkspaceMode = 'quick' | 'pub';
export type DrawerKind = null | 'history' | 'exports' | 'stats' | 'settings';

interface WorkspaceState {
  cells: Cell[];
  datasets: Dataset[];
  currentPreset: string;
  mode: WorkspaceMode;
  globalPreset: string;
  pageTitle: string;
  drawer: DrawerKind;
  focusCellId: string | null;
  cmdkOpen: boolean;
  mapperOpen: boolean;
  mapperDsId: string | null;
  helpOpen: boolean;
  toast: { msg: string; id: number } | null;

  addCell: (c: Cell, at?: number) => void;
  updateCell: (id: string, patch: Partial<Cell>) => void;
  removeCell: (id: string) => void;
  duplicateCell: (id: string) => void;
  reorderCells: (from: number, to: number) => void;

  addDataset: (d: Dataset) => void;
  removeDataset: (id: string) => void;
  setActiveDataset: (id: string) => void;
  toggleRecipe: (dsId: string, recipeId: string) => void;
  applyRecipes: (dsId: string) => void;

  setMode: (m: WorkspaceMode) => void;
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
}

let _toastSeq = 0;

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      cells: SEED_CELLS,
      datasets: SEED_DATASETS,
      currentPreset: 'ieee',
      mode: 'quick',
      globalPreset: 'ieee',
      pageTitle: 'Pilot subject 03 · Treadmill 0.8 m/s',
      drawer: null,
      focusCellId: null,
      cmdkOpen: false,
      mapperOpen: false,
      mapperDsId: null,
      helpOpen: false,
      toast: null,

      addCell: (c, at) => set((s) => {
        const cells = [...s.cells];
        if (at == null) cells.push(c);
        else cells.splice(at, 0, c);
        return { cells };
      }),
      updateCell: (id, patch) => set((s) => ({
        cells: s.cells.map((c) => (c.id === id ? { ...c, ...patch } : c)),
      })),
      removeCell: (id) => set((s) => ({ cells: s.cells.filter((c) => c.id !== id) })),
      duplicateCell: (id) => set((s) => {
        const idx = s.cells.findIndex((c) => c.id === id);
        if (idx < 0) return {};
        const src = s.cells[idx];
        const copy: Cell = { ...src, id: 'c' + Date.now() };
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

      addDataset: (d) => set((s) => ({ datasets: [...s.datasets, d] })),
      removeDataset: (id) => set((s) => ({ datasets: s.datasets.filter((d) => d.id !== id) })),
      setActiveDataset: (id) => set((s) => ({
        datasets: s.datasets.map((d) => ({ ...d, active: d.id === id })),
      })),
      toggleRecipe: (dsId, recipeId) => set((s) => ({
        datasets: s.datasets.map((d) =>
          d.id === dsId ? { ...d, recipeState: { ...d.recipeState, [recipeId]: !d.recipeState[recipeId] } } : d,
        ),
      })),
      applyRecipes: (dsId) => {
        // Placeholder — real impl will add cells based on selected recipes.
        // Wired in Phase B.
        get().showToast(`Recipes applied for ${dsId}`);
      },

      setMode: (m) => set({ mode: m }),
      setCurrentPreset: (p) => set({ currentPreset: p }),
      setGlobalPreset: (p) => set({ globalPreset: p, currentPreset: p }),
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
      name: 'hw_workspace_v1',
      partialize: (s) => ({
        cells: s.cells,
        datasets: s.datasets,
        currentPreset: s.currentPreset,
        mode: s.mode,
        globalPreset: s.globalPreset,
        pageTitle: s.pageTitle,
      }),
    },
  ),
);
