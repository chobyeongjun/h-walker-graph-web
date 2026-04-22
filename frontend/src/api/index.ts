// Typed fetch wrappers for the H-Walker backend.
// Endpoints match HANDOFF §2 (§3.3/§3.4 to be implemented server-side).

import type { Dataset } from '../store/workspace';

const BASE = '';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

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

export interface ComputeRequest {
  dataset_id: string;
  metric: 'per_stride' | 'per_trial' | 'per_window';
  params: {
    detect?: 'heel-strike' | 'toe-off' | 'threshold';
    window?: [number, number] | null;
    smoothing?: { method: 'lowpass'; cutoff: number } | null;
  };
}
export interface ComputeResponse {
  rows: unknown[][];
  columns: string[];
  summary: { mean: number[]; sd: number[]; n: number };
  csv_url: string;
}
export const compute = (req: ComputeRequest) =>
  json<ComputeResponse>('/api/compute', { method: 'POST', body: JSON.stringify(req) });

export interface StatsRequest {
  op: string;
  inputs: { a: string; b: string };
  fmt: 'apa' | 'ieee' | 'csv';
  dataset_id: string;
}
export const runStats = (req: StatsRequest) =>
  json<{
    stat: number; p: number; df: number;
    effect_size: { name: string; value: number };
    ci95: [number, number] | null;
    text_apa: string; text_ieee: string;
    passed_assumptions: { normality: boolean; equal_var: boolean };
  }>('/api/stats', { method: 'POST', body: JSON.stringify(req) });

export interface RenderGraphRequest {
  template: string;
  dataset_id: string;
  preset: string;
  width_mm: number;
  dpi: number;
  format: 'svg' | 'pdf' | 'eps' | 'tiff' | 'png';
  options: { stride_avg: boolean; colorblind_safe: boolean };
}
export const renderGraph = async (req: RenderGraphRequest): Promise<Blob> => {
  const res = await fetch(BASE + '/api/graphs/render', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.blob();
};

export interface ExportBundleRequest {
  preset: string;
  include: { graphs: boolean; stats: boolean; notebook: boolean; html: boolean };
  cell_ids: string[];
}
export const exportBundle = async (req: ExportBundleRequest): Promise<Blob> => {
  const res = await fetch(BASE + '/api/export/bundle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.blob();
};

export interface ClaudeCompleteRequest {
  prompt: string;
  context: { cells: unknown[]; active_dataset_id: string | null };
}
export const claudeComplete = (req: ClaudeCompleteRequest) =>
  json<{ reply: string; suggested_cells?: unknown[] }>(
    '/api/claude/complete',
    { method: 'POST', body: JSON.stringify(req) },
  );
