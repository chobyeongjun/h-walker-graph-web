// Canonical recipes — the standard set of figures + tables a gait
// biomechanics paper / meeting deck would typically include.
//
// Philosophy (post Phase 2H):
//   default:true  → core figures every gait study wants. Auto-run on
//                   upload. Keep this list SHORT and high-value.
//   default:false → advanced / specialized. User ticks the box then
//                   clicks "Apply selected" to add them on demand.
//
// Removed from default-on (moved to advanced): cyclogram,
// stride_time_trend, impulse, imu_avg (per user feedback — too
// specialized, confusing labels).
export interface CanonicalRecipe {
  id: string;
  label: string;
  default: boolean;
  type: 'graph' | 'compute';
  graph?: string;
  compute?: string;
  hint?: string;   // short tooltip explaining what this figure/table shows
}

const FORCE_RECIPES: CanonicalRecipe[] = [
  // ── Core (always on)
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP-based)',    default: true,  type: 'graph',   graph: 'force_lr_subplot',
    hint: 'Side-by-side panels, one per leg, both GCP-normalized with desired overlay. The standard paper Figure 1.' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD (overlay)',  default: true,  type: 'graph',   graph: 'force_avg',
    hint: 'Vertical ground reaction force averaged across strides, normalized to 0-100% gait cycle.' },
  { id: 'grf_raw',      label: 'GRF raw · L vs R',                    default: true,  type: 'graph',   graph: 'force',
    hint: 'Instantaneous force (not averaged) showing both legs overlaid.' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',        default: true,  type: 'graph',   graph: 'asymmetry',
    hint: 'Peak L vs R force asymmetry for each stride. 0% = perfectly symmetric.' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',         default: true,  type: 'graph',   graph: 'peak_box',
    hint: 'Distribution of peak force per stride, side-by-side L vs R.' },
  { id: 'per_stride',   label: 'Stride-by-stride table',              default: true,  type: 'compute', compute: 'per_stride',
    hint: 'One row per stride: peak_L, peak_R, stride time, asymmetry.' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)',     default: true,  type: 'graph',   graph: 'symmetry_radar',
    hint: 'Radar plot of % asymmetry across stride time / length / force / stance / peak.' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',            default: true,  type: 'graph',   graph: 'stance_swing_bar',
    hint: '% of gait cycle spent in stance vs swing, L and R.' },
  // ── Advanced (off by default)
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',               default: false, type: 'compute', compute: 'loading_rate',
    hint: 'Slope of force rise immediately after heel-strike (BW/s).' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                     default: false, type: 'compute', compute: 'impulse',
    hint: 'Time integral of vertical force per stride. Usually only needed for mechanical work analyses.' },
  { id: 'cop',          label: 'Center-of-pressure trajectory',       default: false, type: 'graph',   graph: 'cop',
    hint: 'AP vs ML path of CoP during stance. Requires force-plate grid.' },
];

const IMU_RECIPES: CanonicalRecipe[] = [
  // ── Core
  { id: 'pitch_ts',   label: 'Joint angle · time series',              default: true, type: 'graph',   graph: 'imu',
    hint: 'Raw pitch/roll angle over time for the first ~8 s.' },
  { id: 'rom_bar',    label: 'Range of motion (ROM) bar',              default: true, type: 'graph',   graph: 'rom_bar',
    hint: 'Peak-to-peak angle by joint / plane, L vs R.' },
  { id: 'cadence',    label: 'Cadence (steps/min)',                    default: true, type: 'compute', compute: 'cadence',
    hint: 'Average steps per minute computed from heel-strike intervals.' },
  { id: 'stride_len', label: 'Stride length (ZUPT integration)',       default: true, type: 'compute', compute: 'stride_length',
    hint: 'Foot displacement per stride, drift-corrected via zero-velocity update.' },
  // ── Advanced
  { id: 'joint_avg',     label: 'Joint angle · mean ± SD per cycle',   default: false, type: 'graph',   graph: 'imu_avg',
    hint: 'Angle (from pitch column) averaged across strides, normalized to gait cycle.' },
  { id: 'cyclogram',     label: 'Cyclogram (L vs R pitch phase plot)', default: false, type: 'graph',   graph: 'cyclogram',
    hint: 'Phase portrait: X = L pitch, Y = R pitch. Loops = cyclic gait.' },
  { id: 'stride_trend',  label: 'Stride-time trend (fatigue)',         default: false, type: 'graph',   graph: 'stride_time_trend',
    hint: 'Stride time vs stride #. Slope = fatigue or pacing change.' },
  { id: 'rom',           label: 'ROM per stride table',                default: false, type: 'compute', compute: 'rom',
    hint: 'Full per-stride ROM table — use the bar graph if you just need a summary.' },
  { id: 'fatigue',       label: 'Fatigue index',                       default: false, type: 'compute', compute: 'fatigue_index',
    hint: 'Stride time first 10 % vs last 10 % — early fatigue detection.' },
];

const TRIAL_RECIPES: CanonicalRecipe[] = [
  { id: 'overlay',    label: 'Trial overlay (all trials)',       default: true,  type: 'graph',   graph: 'trials' },
  { id: 'target_dev', label: 'Target deviation per trial',       default: true,  type: 'compute', compute: 'target_dev' },
  { id: 'cv_bar',     label: 'Coefficient of variation',         default: false, type: 'graph',   graph: 'cv_bar' },
];

// H-Walker 67-col firmware CSV (force + IMU combined)
const MIXED_RECIPES: CanonicalRecipe[] = [
  // ── Core force
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP-based)', default: true,  type: 'graph',   graph: 'force_lr_subplot' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD',         default: true,  type: 'graph',   graph: 'force_avg' },
  { id: 'grf_raw',      label: 'GRF raw · L vs R',                 default: true,  type: 'graph',   graph: 'force' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',    default: true,  type: 'graph',   graph: 'asymmetry' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',     default: true,  type: 'graph',   graph: 'peak_box' },
  { id: 'per_stride',   label: 'Stride-by-stride table',          default: true,  type: 'compute', compute: 'per_stride' },
  // ── Core motion
  { id: 'pitch_ts',     label: 'Joint angle · time series',       default: true,  type: 'graph',   graph: 'imu' },
  { id: 'rom_bar',      label: 'Range of motion (ROM) bar',       default: true,  type: 'graph',   graph: 'rom_bar' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',        default: true,  type: 'graph',   graph: 'stance_swing_bar' },
  { id: 'stride_len',   label: 'Stride length (ZUPT)',            default: true,  type: 'compute', compute: 'stride_length' },
  { id: 'cadence',      label: 'Cadence (steps/min)',             default: true,  type: 'compute', compute: 'cadence' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)', default: true,  type: 'graph',   graph: 'symmetry_radar' },
  // ── Advanced
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',           default: false, type: 'compute', compute: 'loading_rate' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                 default: false, type: 'compute', compute: 'impulse' },
  { id: 'joint_avg',    label: 'Joint angle · mean ± SD per cycle', default: false, type: 'graph', graph: 'imu_avg' },
  { id: 'cyclogram',    label: 'Cyclogram (L vs R pitch)',        default: false, type: 'graph',   graph: 'cyclogram' },
  { id: 'stride_trend', label: 'Stride-time trend (fatigue)',     default: false, type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom',          label: 'ROM per stride table',            default: false, type: 'compute', compute: 'rom' },
  { id: 'fatigue',      label: 'Fatigue index',                   default: false, type: 'compute', compute: 'fatigue_index' },
];

export const CANONICAL_RECIPES: Record<string, CanonicalRecipe[]> = {
  force:  FORCE_RECIPES,
  imu:    IMU_RECIPES,
  trials: TRIAL_RECIPES,
  mixed:  MIXED_RECIPES,
  // Fallback for legacy kinds
  cop:    FORCE_RECIPES,
  emg:    FORCE_RECIPES,
};
