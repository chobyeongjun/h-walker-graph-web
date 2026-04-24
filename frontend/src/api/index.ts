// Typed fetch wrappers for the H-Walker backend.
// Contract mirrors backend/routers/{datasets,analyze,compute,stats,graphs,claude}.py.

import type { Dataset } from '../store/page';

const BASE = '';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ============================================================
// Datasets
// ============================================================

export async function uploadDataset(file: File): Promise<Dataset> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(BASE + '/api/datasets/upload', { method: 'POST', body: fd });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const listDatasets = () => json<Dataset[]>('/api/datasets');
export const getDataset = (id: string) => json<Dataset & { sample: unknown[] }>(`/api/datasets/${id}`);
export const deleteDataset = (id: string) => fetch(BASE + `/api/datasets/${id}`, { method: 'DELETE' });

export const saveMapping = (id: string, columns: Record<string, string>) =>
  json<{ updated: number }>(`/api/datasets/${id}/mapping`, {
    method: 'POST',
    body: JSON.stringify({ columns }),
  });

// Phase 2 · study-level tags; Phase 4 · treadmill meta
export const updateDatasetMeta = (
  id: string,
  meta: Partial<Pick<Dataset,
    'subject_id' | 'condition' | 'group' | 'date' | 'is_treadmill' | 'belt_speed_ms'>>,
) => json<Dataset>(`/api/datasets/${id}/meta`, {
  method: 'PATCH',
  body: JSON.stringify(meta),
});

// ============================================================
// Analyze (GET /api/analyze/{ds_id})
// ============================================================

export interface SideStride {
  n_strides: number;
  stride_time_mean: number;
  stride_time_std: number;
  stride_time_cv: number;
  stride_length_mean: number;
  stride_length_std: number;
  cadence: number;
  stance_pct_mean: number;
  stance_pct_std: number;
  swing_pct_mean: number;
  swing_pct_std: number;
  force_tracking: { rmse: number; mae: number; peak_error: number };
  stride_times_list: number[];
  stride_lengths_list: number[];
}

export interface AnalysisPayload {
  mode: 'hwalker';
  filename: string;
  n_samples: number;
  duration_s: number;
  sample_rate: number;
  symmetry: { stride_time: number; stride_length: number; force: number; stance: number };
  fatigue: { left_pct_change: number; right_pct_change: number };
  left: SideStride;
  right: SideStride;
  profiles: {
    left:  { available: boolean; n_points?: number; mean?: number[]; std?: number[]; des_mean?: number[]; des_std?: number[] };
    right: { available: boolean; n_points?: number; mean?: number[]; std?: number[]; des_mean?: number[]; des_std?: number[] };
  };
}

export interface GenericAnalysisPayload {
  fallback_mode: 'generic';
  filename: string;
  n_samples: number;
  n_columns: number;
  columns: string[];
  descriptive: Record<string, { n: number; mean: number; std: number; min: number; max: number; median: number }>;
  note: string;
}

export type AnalyzeResponse = AnalysisPayload | GenericAnalysisPayload;

export const analyzeDataset = (dsId: string) =>
  json<AnalyzeResponse>(`/api/analyze/${dsId}`);

// ============================================================
// Compute (POST /api/compute)
// ============================================================

export type ComputeMetricKey =
  | 'per_stride' | 'impulse' | 'loading_rate' | 'rom' | 'cadence' | 'target_dev';

export interface ComputeRequest {
  dataset_id: string;
  metric: ComputeMetricKey;
  options?: Record<string, unknown>;
}

export interface ComputeResponse {
  label: string;
  cols: string[];
  rows: string[][];
  summary: { mean: string[] };
  meta?: {
    n_strides?: number;
    mode?: 'zupt' | 'treadmill' | string;
    belt_speed_ms?: number | null;
    warnings?: string[];
    [k: string]: unknown;
  };
}

export const computeMetric = (req: ComputeRequest) =>
  json<ComputeResponse>('/api/compute', { method: 'POST', body: JSON.stringify(req) });

// ============================================================
// Stats (POST /api/stats)
// ============================================================

export type StatOpKey =
  | 'ttest_paired' | 'ttest_welch' | 'anova1' | 'pearson' | 'cohens_d' | 'shapiro';

export interface StatsRequest {
  op: StatOpKey;
  // Raw series
  a?: number[];
  b?: number[];
  groups?: number[][];
  paired?: boolean;
  // Dataset-backed convenience (single dataset + columns)
  dataset_id?: string;
  a_col?: string;
  b_col?: string;
  groups_cols?: string[];
  // Phase 3 cross-dataset
  datasets_a?: Array<{ id: string; metric: string }>;
  datasets_b?: Array<{ id: string; metric: string }>;
  datasets_groups?: Array<Array<{ id: string; metric: string }>>;
}

export interface MetricDescriptor {
  key: string;
  label: string;
  unit: string;
  side: string;
  kind: string;
}

export const listStatMetrics = () =>
  json<MetricDescriptor[]>('/api/stats/metrics');

export interface StatsResponse {
  op: string;
  name: string;
  stat: number;
  stat_name: string;
  p: number | null;
  df: number | number[] | null;
  effect_size: { name: string; value: number; label?: string } | null;
  ci95: [number, number] | null;
  n: number | number[];
  assumption: { name: string; p: number; passed: boolean } | null;
  fallback_used: boolean;
  summary: string;
}

export const runStats = (req: StatsRequest) =>
  json<StatsResponse>('/api/stats', { method: 'POST', body: JSON.stringify(req) });

// ============================================================
// Graph render (POST /api/graphs/render) — returns Blob
// ============================================================

export interface RenderGraphRequest {
  template: string;
  preset?: string;
  variant?: 'col1' | 'col2' | 'onehalf';
  format?: 'svg' | 'pdf' | 'eps' | 'png' | 'tiff';
  dpi?: number;
  stride_avg?: boolean;
  colorblind_safe?: boolean;
  keep_palette?: boolean;
  dataset_id?: string;   // single-dataset path (legacy)
  datasets?: Array<{ id: string; label?: string; color?: string }>;  // Phase 1 overlay
  title?: string;
  side?: 'L' | 'R' | 'both';  // limb filter — 'both' = default (show L and R)
}

export const renderGraph = async (req: RenderGraphRequest): Promise<Blob> => {
  const res = await fetch(BASE + '/api/graphs/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.blob();
};

// ============================================================
// Bundle export (POST /api/graphs/bundle) — returns Blob
// ============================================================

export interface BundleRequest {
  preset: string;
  variant?: 'col1' | 'col2' | 'onehalf';
  format?: 'svg' | 'pdf' | 'eps' | 'png' | 'tiff';
  dpi?: number;
  cells: Array<{
    id: string;
    template: string;
    stride_avg?: boolean;
    preset?: string;
    variant?: string;
    dataset_id?: string;
    datasets?: Array<{ id: string; label?: string; color?: string }>;
    title?: string;
  }>;
  include_readme?: boolean;
}

export const exportBundle = async (req: BundleRequest): Promise<Blob> => {
  const res = await fetch(BASE + '/api/graphs/bundle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.blob();
};

// ============================================================
// Paper bundle (POST /api/paper/bundle) — Phase 5 RUN PAPER
// ============================================================

export interface PaperBundleCell {
  id: string;
  type: 'graph' | 'stat' | 'compute';
  title?: string;
  graph?: string;
  stride_avg?: boolean;
  dataset_id?: string;
  datasets?: Array<{ id: string; label?: string; color?: string }>;
  op?: string;
  a_col?: string;
  b_col?: string;
  datasets_a?: Array<{ id: string; metric: string }>;
  datasets_b?: Array<{ id: string; metric: string }>;
  metric?: string;
}

export interface PaperBundleRequest {
  preset: string;
  variant?: 'col1' | 'col2' | 'onehalf';
  format?: 'pdf' | 'svg' | 'eps' | 'png' | 'tiff';
  dpi?: number;
  paper_title?: string;
  cells: PaperBundleCell[];
  colorblind_safe?: boolean;
}

export interface PaperBundleResult {
  blob: Blob;
  /** Number of cells that failed to render (surfaced via X-Bundle-Errors header). */
  errorCount: number;
  /** Short description of the first failed cell (X-Bundle-First-Error). */
  firstError: string | null;
}

/** Paper bundle returning Blob + error metadata from response headers,
 *  so the UI can show a warning toast if some cells were dropped. */
export const paperBundle = async (req: PaperBundleRequest): Promise<PaperBundleResult> => {
  const res = await fetch(BASE + '/api/paper/bundle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const errorCount = Number(res.headers.get('x-bundle-errors') || '0') || 0;
  const firstError = res.headers.get('x-bundle-first-error');
  return { blob, errorCount, firstError };
};

// ============================================================
// LLM Codegen (POST /api/graphs/codegen) — AI-generated custom plot
// ============================================================

export interface CodegenRequest {
  dataset_id: string;
  prompt: string;
  preset?: string;
  variant?: 'col1' | 'col2' | 'onehalf';
  format?: 'svg' | 'png' | 'pdf';
  dpi?: number;
}

export const codegenGraph = async (req: CodegenRequest): Promise<Blob> => {
  const res = await fetch(BASE + '/api/graphs/codegen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.blob();
};

// ============================================================
// Feedback (POST /api/feedback/positive | /correction)
// ============================================================

export const feedbackPositive = (query: string, response: object, note?: string) =>
  fetch(BASE + '/api/feedback/positive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, response, note }),
  });

export const feedbackCorrection = (query: string, wrongResponse: object, reason: string) =>
  fetch(BASE + '/api/feedback/correction', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, wrong_response: wrongResponse, reason }),
  });

// ============================================================
// Claude (POST /api/claude/complete)
// ============================================================

export interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface ClaudeCompleteRequest {
  prompt: string;
  context: {
    cells: unknown[];
    active_dataset_id: string | null;
    history?: Array<{ role: 'user' | 'assistant'; content: string }>;
    datasets?: unknown[];   // Phase 2I · analysis summary per dataset for LLM diagnosis
  };
}

export interface ClaudeCompleteResponse {
  reply: string;
  tool_uses?: ToolUseBlock[];
  suggested_cells?: unknown[];   // legacy
}

export const claudeComplete = (req: ClaudeCompleteRequest) =>
  json<ClaudeCompleteResponse>('/api/claude/complete', {
    method: 'POST',
    body: JSON.stringify(req),
  });

export const claudeHealth = () =>
  json<{ provider: string; model: string; key_present: boolean }>('/api/claude/health');


// ============================================================
// Study (POST /api/study/discover, GET /api/study/{id}/analyze)
// ============================================================

export interface StudyFile {
  id: string;
  name: string;
  path: string;
  subject_id?: string;
  condition?: string;
  group?: string;
}

export interface Study {
  id: string;
  name: string;
  files: StudyFile[];
}

export interface StudySummary {
  study_id: string;
  study_name: string;
  file_summaries: any[];
  comparison: any;
  report_md: string;
  report_latex?: string;
}

export const discoverStudy = (directory: string, name?: string) =>
  json<Study>(`/api/study/discover?directory=${encodeURIComponent(directory)}&name=${encodeURIComponent(name || '')}`, { method: 'POST' });

export const analyzeStudy = (id: string) =>
  json<StudySummary>(`/api/study/${id}/analyze`);

export const listStudies = () =>
  json<Study[]>('/api/study/list');

// ============================================================
// Sync (POST /api/sync/align) — cross-source Hz alignment
// ============================================================

export interface SyncPulse {
  fall_idx: number;
  rise_idx: number;
  fall_t: number;
  rise_t: number;
  width_s: number;
}

export interface SyncPreview {
  ds_id: string;
  sync_col: string | null;
  sample_rate: number;
  duration_s: number;
  pulses: SyncPulse[];
  window: [number, number] | null;
  window_t: [number, number] | null;
  signal_thumb: number[];
  signal_thumb_t: number[];
}

export const syncPreview = (dsId: string) =>
  json<SyncPreview>(`/api/sync/preview/${dsId}`);

export interface SyncAlignRequest {
  dataset_ids: string[];
  target_hz?: number;
  crop_to_a7?: boolean;
  suffix?: string;
}

export interface AlignedDataset {
  original_id: string;
  new_id: string;
  original_name: string;
  new_name: string;
  original_fs: number;
  target_fs: number;
  window: [number, number] | null;
  window_t: [number, number] | null;
  sync_col_used: string | null;
  n_in: number;
  n_out: number;
  duration_s: number;
}

export interface SyncAlignResponse {
  target_hz: number;
  common_duration_s: number;
  aligned: AlignedDataset[];
  notes: string[];
}

export const syncAlign = (req: SyncAlignRequest) =>
  json<SyncAlignResponse>('/api/sync/align', {
    method: 'POST',
    body: JSON.stringify(req),
  });

export const syncNeedsCheck = () =>
  json<{ mixed: boolean; rates: Record<string, string[]>; n_datasets: number }>('/api/sync/needs-sync');

// ============================================================
// Sync gate-split (POST /api/sync/split/gates/*)
// MoCap trial segmentation: HIGH gate = recording window
// ============================================================

export interface GateSplitRequest {
  ds_id: string;
  signal_col?: string;
  min_gate_width_s?: number;
  max_gate_width_s?: number;
  merge_gap_s?: number;
  threshold_rel?: number;
}

export interface GateInfo {
  trial_index: number;
  start_idx: number;
  end_idx: number;
  start_t: number;
  end_t: number;
  duration_s: number;
  new_ds_id?: string | null;
  new_name?: string | null;
}

export interface GatePreviewResponse {
  source_ds_id: string;
  signal_col: string;
  n_trials: number;
  sample_rate: number;
  gates: GateInfo[];
}

export interface GateSplitResponse {
  source_ds_id: string;
  signal_col: string;
  n_trials: number;
  gates: GateInfo[];
}

export const syncGatesPreview = (req: GateSplitRequest) =>
  json<GatePreviewResponse>('/api/sync/split/gates/preview', {
    method: 'POST',
    body: JSON.stringify(req),
  });

export const syncGatesExecute = (req: GateSplitRequest) =>
  json<GateSplitResponse>('/api/sync/split/gates/execute', {
    method: 'POST',
    body: JSON.stringify(req),
  });

// ============================================================
// Edge-trim (fallback when no analog sync column)
// POST /api/sync/split/trim/*
// ============================================================

export interface EdgeTrimRequest {
  ds_id: string;
  force_col?: string;
  n_edge?: number;         // default 3
  threshold_rel?: number;  // default 0.15
  min_stride_s?: number;   // default 0.3
}

export interface EdgeTrimInfo {
  force_col: string;
  total_footfalls: number;
  n_edge: number;
  start_idx: number;
  end_idx: number;
  start_t: number;
  end_t: number;
  duration_s: number;
  kept_footfalls: number;
}

export interface EdgeTrimResponse {
  source_ds_id: string;
  new_ds_id?: string | null;
  new_name?: string | null;
  info: EdgeTrimInfo;
}

export const syncTrimPreview = (req: EdgeTrimRequest) =>
  json<EdgeTrimInfo & { source_ds_id: string }>('/api/sync/split/trim/preview', {
    method: 'POST',
    body: JSON.stringify(req),
  });

export const syncTrimExecute = (req: EdgeTrimRequest) =>
  json<EdgeTrimResponse>('/api/sync/split/trim/execute', {
    method: 'POST',
    body: JSON.stringify(req),
  });
