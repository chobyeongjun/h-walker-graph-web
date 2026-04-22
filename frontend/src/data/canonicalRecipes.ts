// Ported from core_v3.html :967-988
export interface CanonicalRecipe {
  id: string;
  label: string;
  default: boolean;
  type: 'graph' | 'compute';
  graph?: string;
  compute?: string;
}

export const CANONICAL_RECIPES: Record<string, CanonicalRecipe[]> = {
  force: [
    { id: 'grf_avg',     label: 'GRF waveform · mean ± SD',        default: true,  type: 'graph',   graph: 'force_avg' },
    { id: 'grf_raw',     label: 'GRF raw waveform · L vs R',       default: true,  type: 'graph',   graph: 'force' },
    { id: 'per_stride',  label: 'Per-stride metrics table',        default: true,  type: 'compute', compute: 'per_stride' },
    { id: 'asymmetry',   label: 'Asymmetry index · stride series', default: true,  type: 'graph',   graph: 'asymmetry' },
    { id: 'peak_box',    label: 'Peak force · L vs R boxplot',     default: false, type: 'graph',   graph: 'peak_box' },
    { id: 'impulse',     label: 'Impulse (force · time integral)', default: false, type: 'compute', compute: 'impulse' },
    { id: 'cop',         label: 'CoP trajectory',                  default: false, type: 'graph',   graph: 'cop' },
    { id: 'loading_rate',label: 'Loading rate (0–50ms)',           default: false, type: 'compute', compute: 'loading_rate' },
  ],
  imu: [
    { id: 'pitch_ts',    label: 'Shank/thigh pitch · time series', default: true,  type: 'graph',   graph: 'imu' },
    { id: 'rom',         label: 'ROM per stride',                  default: false, type: 'compute', compute: 'rom' },
    { id: 'cadence',     label: 'Cadence from heel-strike',        default: false, type: 'compute', compute: 'cadence' },
  ],
  trials: [
    { id: 'overlay',     label: 'Trial overlay (N=5)',             default: true,  type: 'graph',   graph: 'trials' },
    { id: 'target_dev',  label: 'Target deviation per trial',      default: true,  type: 'compute', compute: 'target_dev' },
    { id: 'cv_bar',      label: 'Coefficient of variation · bar',  default: false, type: 'graph',   graph: 'cv_bar' },
  ],
};
