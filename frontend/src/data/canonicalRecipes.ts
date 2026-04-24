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
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP)',          default: true,  type: 'graph',   graph: 'force_lr_subplot',
    hint: 'Side-by-side panels, one per leg, GCP-normalized with desired overlay.' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD',            default: true,  type: 'graph',   graph: 'force_avg',
    hint: 'GRF averaged across strides, 0–100% gait cycle.' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',        default: true,  type: 'graph',   graph: 'asymmetry',
    hint: 'Peak L vs R force asymmetry per stride. 0 % = symmetric.' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',         default: true,  type: 'graph',   graph: 'peak_box',
    hint: 'Distribution of peak force per stride, L vs R.' },
  { id: 'force_track',  label: 'Force tracking RMSE (ILC)',           default: true,  type: 'graph',   graph: 'force_tracking',
    hint: 'Per-stride cable force RMSE — convergence over the session.' },
  { id: 'spatiotemporal', label: 'Spatiotemporal summary',            default: true,  type: 'graph',   graph: 'spatiotemporal_bar',
    hint: 'Cadence, stride length, and symmetry indices side by side.' },
  { id: 'per_stride',   label: 'Stride-by-stride table',              default: true,  type: 'compute', compute: 'per_stride',
    hint: 'One row per stride: peak_L, peak_R, stride time, asymmetry.' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',            default: true,  type: 'graph',   graph: 'stance_swing_bar',
    hint: '% gait cycle in stance vs swing, L and R.' },
  // ── Advanced
  { id: 'loading_rate', label: 'Loading rate (0–50 ms)',              default: false, type: 'compute', compute: 'loading_rate' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                     default: false, type: 'compute', compute: 'impulse' },
];

const IMU_RECIPES: CanonicalRecipe[] = [
  // ── Core
  { id: 'kinematics',  label: 'Kinematics ensemble (GCP avg ± SD)',  default: true,  type: 'graph',   graph: 'kinematics_ensemble',
    hint: 'Joint angle vs gait cycle — detects Hip/Knee/Ankle or shank IMU automatically.' },
  { id: 'spatiotemporal', label: 'Spatiotemporal summary',           default: true,  type: 'graph',   graph: 'spatiotemporal_bar',
    hint: 'Cadence, stride length, and symmetry side by side.' },
  { id: 'cadence',     label: 'Cadence (steps/min)',                 default: true,  type: 'compute', compute: 'cadence' },
  { id: 'stride_len',  label: 'Stride length',                       default: true,  type: 'compute', compute: 'stride_length' },
  // ── Advanced
  { id: 'stride_trend', label: 'Stride-time trend (fatigue)',        default: false, type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom',          label: 'ROM per stride table',               default: false, type: 'compute', compute: 'rom' },
  { id: 'fatigue',      label: 'Fatigue index',                      default: false, type: 'compute', compute: 'fatigue_index' },
];

const TRIAL_RECIPES: CanonicalRecipe[] = [
  { id: 'force_track',  label: 'Force tracking RMSE (ILC)',          default: true,  type: 'graph',   graph: 'force_tracking' },
  { id: 'target_dev',   label: 'Target deviation per trial',         default: true,  type: 'compute', compute: 'target_dev' },
];

// H-Walker 67-col firmware CSV (force + IMU combined)
const MIXED_RECIPES: CanonicalRecipe[] = [
  // ── Core force
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP)',        default: true,  type: 'graph',   graph: 'force_lr_subplot' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD',          default: true,  type: 'graph',   graph: 'force_avg' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',      default: true,  type: 'graph',   graph: 'asymmetry' },
  { id: 'peak_box',     label: 'Peak force · L vs R boxplot',       default: true,  type: 'graph',   graph: 'peak_box' },
  { id: 'force_track',  label: 'Force tracking RMSE (ILC)',         default: true,  type: 'graph',   graph: 'force_tracking' },
  { id: 'per_stride',   label: 'Stride-by-stride table',            default: true,  type: 'compute', compute: 'per_stride' },
  // ── Core motion
  { id: 'kinematics',   label: 'Kinematics ensemble (GCP avg ± SD)', default: true, type: 'graph',   graph: 'kinematics_ensemble' },
  { id: 'spatiotemporal', label: 'Spatiotemporal summary',          default: true,  type: 'graph',   graph: 'spatiotemporal_bar' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',          default: true,  type: 'graph',   graph: 'stance_swing_bar' },
  { id: 'stride_len',   label: 'Stride length',                     default: true,  type: 'compute', compute: 'stride_length' },
  { id: 'cadence',      label: 'Cadence (steps/min)',               default: true,  type: 'compute', compute: 'cadence' },
  // ── Advanced
  { id: 'loading_rate', label: 'Loading rate (0–50 ms)',            default: false, type: 'compute', compute: 'loading_rate' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                   default: false, type: 'compute', compute: 'impulse' },
  { id: 'stride_trend', label: 'Stride-time trend (fatigue)',       default: false, type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom',          label: 'ROM per stride table',              default: false, type: 'compute', compute: 'rom' },
  { id: 'fatigue',      label: 'Fatigue index',                     default: false, type: 'compute', compute: 'fatigue_index' },
  { id: 'mos',          label: 'MoS · XCoM trajectory',            default: false, type: 'graph',   graph: 'mos_trajectory',
    hint: 'Margin of Stability — requires XCoM columns in CSV.' },
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
