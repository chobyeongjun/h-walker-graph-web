// Canonical recipes — the standard set of figures + tables a gait
// biomechanics paper would typically include. Items with default:true
// run automatically on CSV upload; the user can toggle the optional
// ones in the Dataset panel.
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
    // GCP-normalized force comparison — the single most common figure
    { id: 'grf_avg',     label: 'GCP-based GRF waveform · mean ± SD', default: true,  type: 'graph',   graph: 'force_avg' },
    // Raw L vs R overlay — before averaging
    { id: 'grf_raw',     label: 'GRF raw waveform · L vs R',          default: true,  type: 'graph',   graph: 'force' },
    // Per-stride numeric table (peak, stride T, asymmetry)
    { id: 'per_stride',  label: 'Per-stride metrics table',           default: true,  type: 'compute', compute: 'per_stride' },
    // Asymmetry index per stride
    { id: 'asymmetry',   label: 'Asymmetry index · stride series',    default: true,  type: 'graph',   graph: 'asymmetry' },
    // Peak force L vs R — boxplot
    { id: 'peak_box',    label: 'Peak force · L vs R boxplot',        default: true,  type: 'graph',   graph: 'peak_box' },
    // Impulse per stride
    { id: 'impulse',     label: 'Impulse (force · time integral)',    default: true,  type: 'compute', compute: 'impulse' },
    // Loading rate per stride (0-50ms slope)
    { id: 'loading_rate',label: 'Loading rate (0–50ms)',              default: true,  type: 'compute', compute: 'loading_rate' },
    // Optional — not every paper includes CoP
    { id: 'cop',         label: 'CoP trajectory',                     default: false, type: 'graph',   graph: 'cop' },
  ],
  imu: [
    { id: 'pitch_ts',    label: 'Shank/thigh pitch · time series',    default: true,  type: 'graph',   graph: 'imu' },
    { id: 'rom',         label: 'ROM per stride',                     default: true,  type: 'compute', compute: 'rom' },
    { id: 'cadence',     label: 'Cadence from heel-strike',           default: true,  type: 'compute', compute: 'cadence' },
  ],
  trials: [
    { id: 'overlay',     label: 'Trial overlay (N=5)',                default: true,  type: 'graph',   graph: 'trials' },
    { id: 'target_dev',  label: 'Target deviation per trial',         default: true,  type: 'compute', compute: 'target_dev' },
    { id: 'cv_bar',      label: 'Coefficient of variation · bar',     default: true,  type: 'graph',   graph: 'cv_bar' },
  ],
};
