# H-Walker CORE · Claude Code Handoff

This document is designed to be **copy-pasted directly into Claude Code** (or any codebase-aware AI) to port the HTML mockup at `phase2/core_v3.html` into a production React app with a FastAPI backend.

---

## 0. TL;DR — paste this first

> I'm porting a single-file HTML mockup (`phase2/core_v3.html`) into my existing React + FastAPI app. The mockup is a biomechanics analysis workspace — users upload CSV datasets, Claude suggests "canonical recipes," and the page fills with cells (Graph / Stat / Compute). I need you to:
> 1. Read `phase2/core_v3.html` end-to-end.
> 2. Split it into React components (tree below).
> 3. Implement the FastAPI backend contract below.
> 4. Keep visual fidelity 1:1 — fonts, colors, spacing, animations.
> 5. Ask me before substituting any library I haven't listed.

---

## 1. React component tree

```
<App>
├── <TopNav>                       // page title, mode toggle, nav pill
├── <Sidebar>                      // 56px rail, expands on hover
│    ├── <SideItem icon=Home />
│    ├── <SideItem icon=History onClick=openDrawer('history') />
│    ├── <SideItem icon=Stats   onClick=openDrawer('stats')   />
│    ├── <SideItem icon=Exports onClick=openDrawer('exports') />
│    └── <SideItem icon=Settings onClick=openDrawer('settings')/>
├── <PublicationBar visible={mode==='pub'} />  // journal tabs + specs
├── <Canvas>                       // scroll region
│    ├── <DatasetPanel>            // sources, recipes, mapping button
│    └── <Cells>
│         ├── <Cell type="graph"   ...  />   // <GraphCell>
│         ├── <Cell type="stat"    ...  />   // <StatCell>
│         └── <Cell type="compute" ...  />   // <ComputeCell>
├── <LlmDock>                      // sticky bottom input
├── <FocusOverlay>                 // full-screen graph focus
├── <CmdK>                         // ⌘K palette
├── <ColumnMapperModal>
├── <Drawer kind={'history'|'exports'|'stats'|'settings'} />
├── <HelpOverlay>
└── <Toast />
```

### State (Zustand recommended — one store)

```ts
// src/store/workspace.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type CellType = 'graph' | 'stat' | 'compute';

interface Cell {
  id: string;
  type: CellType;
  graph?: string;       // GRAPH_TPLS key
  op?: string;          // STAT_OPS key
  metric?: string;      // COMPUTE_METRICS key
  dsIds: string[];
  preset?: string;      // journal preset override
  strideAvg?: boolean;
  fmt?: 'apa' | 'ieee' | 'csv';
  inputs?: { a: string; b: string };
}

interface Dataset {
  id: string;
  name: string;
  kind: 'force' | 'imu' | 'cop' | 'emg';
  tag: string;
  rows: number;
  dur: number;
  hz: number;
  cols: Array<{ name: string; unit: string; mapped?: string; mappedManual?: boolean }>;
  active: boolean;
  recipeState: Record<string, boolean>;
}

interface WorkspaceState {
  cells: Cell[];
  datasets: Dataset[];
  currentPreset: string;     // 'ieee' | 'nature' | 'apa' | 'elsevier' | 'mdpi'
  mode: 'quick' | 'pub';
  globalPreset: string;
  // actions
  addCell: (c: Cell, at?: number) => void;
  updateCell: (id: string, patch: Partial<Cell>) => void;
  removeCell: (id: string) => void;
  setActiveDataset: (id: string) => void;
  setCurrentPreset: (p: string) => void;
}

export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set) => ({
      cells: [],
      datasets: [],
      currentPreset: 'ieee',
      mode: 'quick',
      globalPreset: 'ieee',
      addCell: (c, at) => set((s) => {
        const cells = [...s.cells];
        if (at == null) cells.push(c); else cells.splice(at, 0, c);
        return { cells };
      }),
      updateCell: (id, patch) => set((s) => ({
        cells: s.cells.map(c => c.id === id ? { ...c, ...patch } : c)
      })),
      removeCell: (id) => set((s) => ({ cells: s.cells.filter(c => c.id !== id) })),
      setActiveDataset: (id) => set((s) => ({
        datasets: s.datasets.map(d => ({ ...d, active: d.id === id }))
      })),
      setCurrentPreset: (p) => set({ currentPreset: p }),
    }),
    { name: 'hw_workspace_v1' }
  )
);
```

### Constants to extract verbatim from `core_v3.html`

These are plain JS objects inside the HTML — move them to their own modules:

- `JOURNAL_PRESETS` → `src/data/journalPresets.ts`
- `GRAPH_TPLS` → `src/data/graphTemplates.ts`
- `STAT_OPS` → `src/data/statOps.ts`
- `COMPUTE_METRICS` → `src/data/computeMetrics.ts`
- `CANONICAL_RECIPES` → `src/data/canonicalRecipes.ts`
- `STATS_LIB`, `EXPORT_FORMATS`, `HISTORY` (seed) → `src/data/catalogs.ts`

Keep shape identical — renderers read these directly.

---

## 2. FastAPI backend contract

### Base URL: `http://localhost:8000`

### 2.1 · Datasets

```
POST /api/datasets/upload
  multipart/form-data: file=<csv|tsv>
  → 201 {
      id: str, name: str, kind: 'force'|'imu'|'cop'|'emg',
      rows: int, dur: float, hz: int,
      cols: [{name: str, unit: str, inferred_role: str, confidence: float, preview: [any]}]
    }

GET /api/datasets
  → 200 [Dataset, ...]

GET /api/datasets/{id}
  → 200 Dataset + first 500 rows sample

DELETE /api/datasets/{id}
  → 204

POST /api/datasets/{id}/mapping
  body: {columns: {<col_name>: <role>}}
  → 200 {updated: int}
```

### 2.2 · Compute (per-stride, per-window, etc.)

```
POST /api/compute
  body: {
    dataset_id: str,
    metric: 'per_stride' | 'per_trial' | 'per_window',
    params: {
      detect: 'heel-strike' | 'toe-off' | 'threshold',
      window: [float, float] | null,
      smoothing: {method: 'lowpass', cutoff: 6.0} | null
    }
  }
  → 200 {
      rows: [[...]],      // first 200 rows
      columns: [str],     // column headers
      summary: {
        mean: [float], sd: [float], n: int
      },
      csv_url: str        // signed URL for full CSV
    }
```

### 2.3 · Stats

```
POST /api/stats
  body: {
    op: 'ttest_paired'|'ttest_welch'|'anova'|'corr'|'cohen'|'mwu'|'wilcoxon'|'shapiro'|'levene',
    inputs: {a: 'c2.L_peak', b: 'c2.R_peak'},   // cross-cell refs
    fmt: 'apa'|'ieee'|'csv',
    dataset_id: str
  }
  → 200 {
      stat: float, p: float, df: number, effect_size: {name: str, value: float},
      ci95: [float, float] | null,
      text_apa: str,       // e.g. "t(13) = 2.84, p = .014, d = 0.76"
      text_ieee: str,
      passed_assumptions: {normality: bool, equal_var: bool}
    }
```

### 2.4 · Graphs (server-side render for publication DPI)

```
POST /api/graphs/render
  body: {
    template: str,          // GRAPH_TPLS key
    dataset_id: str,
    preset: str,            // 'ieee'|'nature'|...
    width_mm: float,        // from JOURNAL_PRESETS[preset].col1.w
    dpi: int,               // 300 or 600
    format: 'svg'|'pdf'|'eps'|'tiff'|'png',
    options: {stride_avg: bool, colorblind_safe: bool}
  }
  → 200 <binary asset with correct Content-Type>
```

### 2.5 · Export bundles

```
POST /api/export/bundle
  body: {
    preset: str,
    include: {graphs: bool, stats: bool, notebook: bool, html: bool},
    cell_ids: [str]
  }
  → 200 <application/zip>, filename from Content-Disposition
```

### 2.6 · Claude proxy (server-side to protect API key)

```
POST /api/claude/complete
  body: { prompt: str, context: {cells: [...], active_dataset_id: str} }
  → 200 { reply: str, suggested_cells?: [{type, ...}] }
```

---

## 3. Copy-paste commands for Claude Code

### 3.1 · Scaffold the component tree

```
@claude Read phase2/core_v3.html. Create these files with empty shells:

src/
  App.tsx
  components/
    TopNav.tsx
    Sidebar.tsx
    PublicationBar.tsx
    Canvas.tsx
    DatasetPanel.tsx
    cells/
      Cell.tsx
      GraphCell.tsx
      StatCell.tsx
      ComputeCell.tsx
    LlmDock.tsx
    FocusOverlay.tsx
    CmdK.tsx
    ColumnMapperModal.tsx
    Drawer.tsx
    HelpOverlay.tsx
    Toast.tsx
  store/
    workspace.ts
  data/
    journalPresets.ts
    graphTemplates.ts
    statOps.ts
    computeMetrics.ts
    canonicalRecipes.ts
    catalogs.ts
  styles/
    tokens.css      // --accent, --bg, etc. from :root in mockup
    app.css         // layout grid
    cells.css
    drawers.css

Then populate store/workspace.ts from section 1 of HANDOFF_CLAUDE_CODE.md.
Then populate all data/*.ts by extracting verbatim object literals from core_v3.html.
```

### 3.2 · Port a single component (do this iteratively)

```
@claude Port <GraphCell> next. Reference:
- core_v3.html lines ~1400–1600 (buildCell for type='graph', plot SVG rendering)
- phase2/core_v3.html :root CSS variables for colors
- Use <svg> + D3-scale (but NOT d3-selection). Render in React.
- Props: {cell: Cell, index: number}.
- Must support: drag handle, duplicate, delete, title edit, journal preset override,
  strideAvg toggle, export SVG button, focus click.
- Extract inline event handlers into a useCell(cellId) hook.
```

### 3.3 · Wire the backend

```
@claude Implement the FastAPI routes in HANDOFF_CLAUDE_CODE.md section 2.
Stack: FastAPI + pandas + scipy + matplotlib (for render) + pingouin.
Put routes in app/api/{datasets,compute,stats,graphs,export,claude}.py.
Use SQLite for dataset metadata; put raw CSVs in ./data/uploads/{id}.csv.
For /api/graphs/render, use matplotlib with rcParams set from JOURNAL_PRESETS.
```

### 3.4 · Claude proxy

```
@claude Add /api/claude/complete. Use anthropic SDK (claude-haiku-4-5).
System prompt: "You are a biomechanics research assistant inside H-Walker CORE.
Given the current workspace state (cells, active dataset), answer the user's question
in ≤3 sentences. If appropriate, suggest follow-up cells by returning
suggested_cells array. Use Korean if user writes Korean."
Stream responses via SSE on /api/claude/stream.
```

### 3.5 · Tests

```
@claude Write Playwright e2e tests mirroring these flows:
1. Upload CSV → dataset appears → mapping modal auto-opens → save mapping → cell list fills.
2. Click journal preset → verify graph CSS vars update + palette swaps.
3. ⌘K → type "ttest" → Enter → stat cell appears.
4. Focus a graph → brush-zoom → export SVG → verify Blob.
```

---

## 4. Library pinning

| Purpose          | Library               | Version  |
| ---------------- | --------------------- | -------- |
| State            | zustand               | ^4.5     |
| Data fetch       | @tanstack/react-query | ^5       |
| Drag / reorder   | @dnd-kit/sortable     | ^8       |
| Icons            | lucide-react          | ^0.400   |
| SVG charts       | **roll your own**     | —        |
| CSV parse client | papaparse             | ^5       |
| Date / history   | date-fns              | ^3       |
| Server stats     | scipy + pingouin      | latest   |
| Server render    | matplotlib            | ^3.8     |
| Server CSV       | pandas                | ^2.2     |

**Do not** introduce Recharts / Nivo / Plotly — the mockup's SVG is intentionally
hand-rolled to match journal specs exactly.

---

## 5. Visual fidelity checklist

- [ ] Background: `#0B0E2E` + two radial gradients (see `body` rule at top of mockup)
- [ ] Accent: `#F09708` (orange), success: `#00FFB2`
- [ ] Fonts: Pretendard (UI), JetBrains Mono (data/code)
- [ ] Sidebar: 56px → 230px on hover, 200ms cubic-bezier(.22,1,.36,1)
- [ ] Cell border-left: 3px solid var(--accent) when hovered
- [ ] All animations use `--hw-ease: cubic-bezier(.22,1,.36,1)`
- [ ] Publication mode: white plots, serif fonts per preset, mm ruler overlay
- [ ] Focus overlay: backdrop-filter blur 10px, fade-in 200ms
- [ ] Toast: bottom-right, 2.2s auto-dismiss

---

## 6. What the frontend already does (no backend needed)

`core_v3.html` v3.5 block implements these for real — port them 1:1:

1. **Claude calls** via `window.claude.complete` (replace with `/api/claude/complete`)
2. **SVG export** via `XMLSerializer` + `Blob`
3. **PNG export** via `canvas.drawImage(svgImg)` @ 2x/3x scale
4. **Clipboard copy** via `navigator.clipboard.writeText`
5. **File upload** via `<input type=file>` + `FileReader`
6. **Brush-zoom** in focus overlay via mousedown/move/up
7. **localStorage persistence** every 10s (move to backend `/api/workspace/save`)
8. **Help overlay** (`?` key)

---

## 7. Known gaps (ask before deciding)

- **Auth** — mockup is single-user. Do we need login?
- **Multi-page workspaces** — mockup is one page. File-tree nav?
- **Collaboration** — comments, mentions, cursor presence?
- **Mobile** — current layout is desktop-only (1280+).
- **Offline** — IndexedDB fallback when backend is down?

Ask the user for each before implementing.

---

*Generated from `phase2/core_v3.html` — if the mockup changes, regenerate this doc.*
