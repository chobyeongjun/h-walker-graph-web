// Canonical recipes — the standard set of figures + tables a gait
// biomechanics paper / meeting deck would typically include. Items with
// default:true run automatically on CSV upload; the user can toggle the
// optional ones in the Dataset panel.
//
// Phase 0 expansion: kinematic (IMU) + motion-data metrics are now
// first-class citizens alongside force templates. A dataset flagged
// `mixed` (has BOTH force and IMU columns) gets the combined recipe set.
export interface CanonicalRecipe {
  id: string;
  label: string;
  default: boolean;
  type: 'graph' | 'compute';
  graph?: string;
  compute?: string;
}

const FORCE_RECIPES: CanonicalRecipe[] = [
  { id: 'grf_avg',      label: 'GCP-based GRF waveform · mean ± SD',  default: true,  type: 'graph',   graph: 'force_avg' },
  { id: 'grf_raw',      label: 'GRF raw waveform · L vs R',           default: true,  type: 'graph',   graph: 'force' },
  { id: 'per_stride',   label: 'Per-stride metrics table',            default: true,  type: 'compute', compute: 'per_stride' },
  { id: 'asymmetry',    label: 'Asymmetry index · stride series',     default: true,  type: 'graph',   graph: 'asymmetry' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',         default: true,  type: 'graph',   graph: 'peak_box' },
  { id: 'impulse',      label: 'Impulse (force · time integral)',     default: true,  type: 'compute', compute: 'impulse' },
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',               default: true,  type: 'compute', compute: 'loading_rate' },
  { id: 'stance_swing', label: 'Stance / swing bar',                  default: true,  type: 'graph',   graph: 'stance_swing_bar' },
  { id: 'symmetry',     label: 'Symmetry radar (6-axis)',             default: true,  type: 'graph',   graph: 'symmetry_radar' },
  { id: 'cop',          label: 'CoP trajectory',                      default: false, type: 'graph',   graph: 'cop' },
];

const IMU_RECIPES: CanonicalRecipe[] = [
  { id: 'pitch_ts',     label: 'Shank/thigh pitch · time series',      default: true,  type: 'graph',   graph: 'imu' },
  { id: 'imu_avg',      label: 'Joint angle · mean ± SD per cycle',    default: true,  type: 'graph',   graph: 'imu_avg' },
  { id: 'cyclogram',    label: 'Cyclogram (shank vs thigh pitch)',     default: true,  type: 'graph',   graph: 'cyclogram' },
  { id: 'stride_trend', label: 'Stride time trend (fatigue)',          default: true,  type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom_bar',      label: 'ROM by joint/plane bar',               default: true,  type: 'graph',   graph: 'rom_bar' },
  { id: 'rom',          label: 'ROM per stride table',                 default: true,  type: 'compute', compute: 'rom' },
  { id: 'cadence',      label: 'Cadence from heel-strike',             default: true,  type: 'compute', compute: 'cadence' },
  { id: 'stride_len',   label: 'Stride length (ZUPT)',                 default: true,  type: 'compute', compute: 'stride_length' },
  { id: 'fatigue',      label: 'Fatigue index (first 10% vs last 10%)', default: true, type: 'compute', compute: 'fatigue_index' },
];

const TRIAL_RECIPES: CanonicalRecipe[] = [
  { id: 'overlay',    label: 'Trial overlay (N=5)',              default: true,  type: 'graph',   graph: 'trials' },
  { id: 'target_dev', label: 'Target deviation per trial',       default: true,  type: 'compute', compute: 'target_dev' },
  { id: 'cv_bar',     label: 'Coefficient of variation · bar',   default: true,  type: 'graph',   graph: 'cv_bar' },
];

// Mixed dataset (force + IMU columns in one CSV — the H-Walker 67-col
// firmware format). Union of force and imu defaults + a symmetry
// summary. This is the typical "full paper figure" set.
const MIXED_RECIPES: CanonicalRecipe[] = [
  // Force side
  { id: 'grf_avg',      label: 'GCP-based GRF waveform · mean ± SD',   default: true,  type: 'graph',   graph: 'force_avg' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',          default: true,  type: 'graph',   graph: 'peak_box' },
  { id: 'asymmetry',    label: 'Asymmetry index · stride series',      default: true,  type: 'graph',   graph: 'asymmetry' },
  { id: 'per_stride',   label: 'Per-stride metrics table',             default: true,  type: 'compute', compute: 'per_stride' },
  { id: 'impulse',      label: 'Impulse (force · time integral)',      default: true,  type: 'compute', compute: 'impulse' },
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',                default: false, type: 'compute', compute: 'loading_rate' },
  // Motion side
  { id: 'imu_avg',      label: 'Joint angle · mean ± SD per cycle',    default: true,  type: 'graph',   graph: 'imu_avg' },
  { id: 'cyclogram',    label: 'Cyclogram (shank vs thigh pitch)',     default: true,  type: 'graph',   graph: 'cyclogram' },
  { id: 'stride_trend', label: 'Stride time trend (fatigue)',          default: true,  type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom_bar',      label: 'ROM by joint/plane bar',               default: true,  type: 'graph',   graph: 'rom_bar' },
  { id: 'stance_swing', label: 'Stance / swing bar',                   default: true,  type: 'graph',   graph: 'stance_swing_bar' },
  // Summary
  { id: 'symmetry',     label: 'Symmetry radar (6-axis)',              default: true,  type: 'graph',   graph: 'symmetry_radar' },
  { id: 'rom',          label: 'ROM per stride table',                 default: false, type: 'compute', compute: 'rom' },
  { id: 'fatigue',      label: 'Fatigue index',                        default: false, type: 'compute', compute: 'fatigue_index' },
  { id: 'cadence',      label: 'Cadence',                              default: false, type: 'compute', compute: 'cadence' },
  { id: 'stride_len',   label: 'Stride length (ZUPT)',                 default: false, type: 'compute', compute: 'stride_length' },
];

export const CANONICAL_RECIPES: Record<string, CanonicalRecipe[]> = {
  force:  FORCE_RECIPES,
  imu:    IMU_RECIPES,
  trials: TRIAL_RECIPES,
  mixed:  MIXED_RECIPES,
  // Fallback for legacy kinds (cop, emg) — use force recipes
  cop:    FORCE_RECIPES,
  emg:    FORCE_RECIPES,
};
