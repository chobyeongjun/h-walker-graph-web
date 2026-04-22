// Ported from core_v3.html :991-1041
export interface ComputeMetric {
  label: string;
  cols: string[];
  rows: string[][];
  summary: { mean: string[] };
}

export const COMPUTE_METRICS: Record<string, ComputeMetric> = {
  per_stride: {
    label: 'Per-stride metrics',
    cols: ['stride_#', 'peak_L (N)', 'peak_R (N)', 'stride_T (s)', 'asym_idx (%)'],
    rows: [
      ['1', '47.8', '45.1', '1.08', '2.9'],
      ['2', '48.5', '46.3', '1.07', '2.3'],
      ['3', '49.1', '46.8', '1.09', '2.4'],
      ['4', '48.2', '47.0', '1.08', '1.3'],
      ['5', '47.9', '46.5', '1.08', '1.5'],
      ['…', '…', '…', '…', '…'],
      ['14', '48.6', '46.9', '1.08', '1.8'],
    ],
    summary: { mean: ['48.2 ± 0.6', '46.7 ± 0.7', '1.08 ± 0.01', '2.1 ± 0.8'] },
  },
  impulse: {
    label: 'Impulse (N·s)',
    cols: ['stride_#', 'L impulse', 'R impulse', 'Δ (%)'],
    rows: [
      ['1', '42.8', '40.9', '4.6'],
      ['2', '43.1', '41.2', '4.6'],
      ['…', '…', '…', '…'],
      ['14', '43.0', '41.1', '4.6'],
    ],
    summary: { mean: ['43.0 ± 0.3', '41.1 ± 0.4', '4.6 ± 0.3'] },
  },
  loading_rate: {
    label: 'Loading rate (BW/s, 0–50ms)',
    cols: ['stride_#', 'L rate', 'R rate', 'Δ'],
    rows: [['1', '68.2', '62.1', '6.1'], ['2', '67.8', '62.5', '5.3'], ['…', '…', '…', '…']],
    summary: { mean: ['68.0 ± 1.2', '62.3 ± 1.4', '5.7 ± 0.9'] },
  },
  rom: {
    label: 'ROM per stride',
    cols: ['stride', 'shank ROM (°)', 'thigh ROM (°)'],
    rows: [['1', '42.1', '38.5'], ['2', '41.8', '38.2'], ['3', '42.4', '38.8']],
    summary: { mean: ['42.1 ± 0.3', '38.5 ± 0.3'] },
  },
  cadence: {
    label: 'Cadence',
    cols: ['window', 'spm'],
    rows: [['0-4s', '110'], ['4-8s', '114']],
    summary: { mean: ['112 ± 2'] },
  },
  target_dev: {
    label: 'Target deviation',
    cols: ['trial', 'RMSE', 'peak Δ (%)'],
    rows: [['T1', '6.8', '-4.2'], ['T2', '5.1', '-2.8'], ['T3', '4.2', '-1.9'], ['T4', '3.0', '+0.4'], ['T5', '2.3', '+2.3']],
    summary: { mean: ['4.3 ± 1.8', 'improving'] },
  },
};
