// Schema-only metadata for compute metrics. Used for:
//   - LlmDock dispatch validation (`metric in COMPUTE_METRICS`)
//   - the dropdown in ComputeCell (label + key)
// NO mock rows / summary values — those used to ship as fake placeholder
// numbers (e.g. cadence=111.8 spm) which leaked onto the canvas before
// a real CSV was bound. Real numbers come exclusively from /api/compute.
export interface ComputeMetric {
  label: string;
  cols: string[];
}

export const COMPUTE_METRICS: Record<string, ComputeMetric> = {
  per_stride:       { label: 'Per-stride metrics',
                      cols: ['stride_#', 'peak_L (N)', 'peak_R (N)', 'stride_T (s)', 'asym_idx (%)'] },
  impulse:          { label: 'Impulse (N·s)',
                      cols: ['stride_#', 'L impulse', 'R impulse', 'Δ (%)'] },
  loading_rate:     { label: 'Loading rate (BW/s, 0–50ms)',
                      cols: ['stride_#', 'L rate', 'R rate', 'Δ'] },
  rom:              { label: 'ROM per stride',
                      cols: ['stride', 'shank ROM (°)', 'thigh ROM (°)'] },
  cadence:          { label: 'Cadence (steps/min · whole-trial avg)',
                      cols: ['from L HS (spm)', 'from R HS (spm)', 'Combined (spm)'] },
  target_dev:       { label: 'Target deviation',
                      cols: ['trial', 'RMSE', 'peak Δ (%)'] },
  stride_length:    { label: 'Stride length (m, ZUPT · whole-trial avg)',
                      cols: ['L (m)', 'R (m)', 'asym (%)'] },
  stance_time:      { label: 'Stance time (s)',
                      cols: ['stride_#', 'L stance (s)', 'R stance (s)'] },
  swing_time:       { label: 'Swing time (s)',
                      cols: ['stride_#', 'L swing (s)', 'R swing (s)'] },
  fatigue_index:    { label: 'Fatigue index (stride time: first 10% vs last 10%)',
                      cols: ['side', 'Δ%', 'interpretation'] },
  symmetry_summary: { label: 'Symmetry summary (% asymmetry · 0 = perfect)',
                      cols: ['metric', 'Δ (%)'] },
};
