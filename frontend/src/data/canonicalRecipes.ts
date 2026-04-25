// Canonical recipes — the standard set of figures + tables a gait
// biomechanics paper / meeting deck would typically include.
//
// Philosophy: nothing is auto-generated on upload. Users pick what
// they need from the Library panel one click at a time. Recipes
// here exist purely as named bundles a user can batch-apply via
// "Apply selected" on the dataset card.
//
// Scalar-first rule: whole-trial parameters (cadence, stride length,
// ROM, fatigue) ship as compute-cell summaries (1-row scalar ± SD).
// Per-stride / per-window time-series of those values are advanced
// and must be explicitly requested.
//
// Naming: "Force" in this file means **loadcell / cable-driven assist
// force** measured by the H-Walker robot, NOT ground reaction force.
// GRF would come from a treadmill force-plate channel and is not
// what these recipes plot.
//
// Removed:
//   - peak_box  : L-vs-R peak boxplot adds little beyond the asymmetry
//                 series + per-stride table.
//   - debug_ts  : the cluttered all-channel raw time-series with no zoom.
//                 Replaced by the per-sync inspector workflow.
export interface CanonicalRecipe {
  id: string;
  label: string;
  default: boolean;
  type: 'graph' | 'compute';
  graph?: string;
  compute?: string;
  hint?: string;
}

const FORCE_RECIPES: CanonicalRecipe[] = [
  { id: 'load_lr',      label: 'Loadcell · L / R subplots (GCP-based)', default: false, type: 'graph',   graph: 'force_lr_subplot',
    hint: 'Side-by-side panels per leg, GCP-normalized, desired vs actual cable force.' },
  { id: 'load_avg',     label: 'Loadcell waveform · mean ± SD',        default: false, type: 'graph',   graph: 'force_avg',
    hint: 'Cable assist force averaged across strides, normalized to 0–100 % gait cycle.' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',         default: false, type: 'graph',   graph: 'asymmetry',
    hint: 'Peak L vs R cable force asymmetry per stride. 0 % = perfectly symmetric.' },
  { id: 'per_stride',   label: 'Stride-by-stride table',               default: false, type: 'compute', compute: 'per_stride',
    hint: 'One row per stride: peak_L, peak_R, stride time, asymmetry.' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)',      default: false, type: 'graph',   graph: 'symmetry_radar',
    hint: 'Radar of % asymmetry across stride time / length / force / stance / peak.' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',             default: false, type: 'graph',   graph: 'stance_swing_bar',
    hint: '% of gait cycle in stance vs swing, L and R. Stance is detected from GCP active segment.' },
  { id: 'load_raw',     label: 'Loadcell raw · L vs R overlay',        default: false, type: 'graph',   graph: 'force',
    hint: 'Instantaneous cable force overlay over the full trial. Use the Inspector for zoom-in debugging.' },
  { id: 'loading_rate', label: 'Loading rate (0–50 ms after HS)',      default: false, type: 'compute', compute: 'loading_rate',
    hint: 'Slope of cable force rise immediately after heel strike (N/s, body-mass normalised if mass is set).' },
  { id: 'impulse',      label: 'Impulse (∫F·dt) per stride',           default: false, type: 'compute', compute: 'impulse',
    hint: 'Time integral of cable force per stride. Useful for mechanical-work / energy estimates.' },
  { id: 'cop',          label: 'Center-of-pressure trajectory',        default: false, type: 'graph',   graph: 'cop',
    hint: 'AP vs ML path of CoP during stance. Requires a force-plate grid (separate from the cable loadcell).' },
];

const IMU_RECIPES: CanonicalRecipe[] = [
  // ── Core (publication-ready summaries)
  { id: 'joint_avg',  label: 'Joint angle · mean ± SD per cycle (per channel)',
                                                                       default: false, type: 'graph',   graph: 'imu_avg',
    hint: 'Stride-averaged joint angle per channel across the 0–100% gait cycle. The canonical kinematic figure.' },
  { id: 'rom_bar',    label: 'ROM bar (joint × plane × side)',        default: false, type: 'graph',   graph: 'rom_bar',
    hint: 'Peak-to-peak angle for each joint in each plane, L vs R.' },
  { id: 'cadence',    label: 'Cadence (avg spm)',                      default: false, type: 'compute', compute: 'cadence',
    hint: 'Whole-trial average steps/min — a single number, not a time-series.' },
  { id: 'stride_len', label: 'Stride length (avg, ZUPT)',              default: false, type: 'compute', compute: 'stride_length',
    hint: 'L / R mean ± SD and the asymmetry index — a single summary row.' },
  // ── Advanced (bookshelf — ask the LLM or tick to add)
  { id: 'cyclogram',     label: 'Cyclogram (proximal vs distal joint)', default: false, type: 'graph',   graph: 'cyclogram',
    hint: 'Phase portrait of two joints. Loops = cyclic gait.' },
  { id: 'stride_trend',  label: 'Stride-time trend (fatigue)',         default: false, type: 'graph',   graph: 'stride_time_trend',
    hint: 'Stride time vs stride #. Slope = fatigue.' },
  { id: 'rom',           label: 'ROM per stride table (per channel)',  default: false, type: 'compute', compute: 'rom',
    hint: 'Full per-stride ROM table per IMU channel — use the bar graph for a summary.' },
  { id: 'fatigue',       label: 'Fatigue index',                       default: false, type: 'compute', compute: 'fatigue_index',
    hint: 'Stride time first 10 % vs last 10 % — early fatigue detection.' },
];

const TRIAL_RECIPES: CanonicalRecipe[] = [
  { id: 'overlay',    label: 'Trial overlay (all trials)',       default: false,  type: 'graph',   graph: 'trials' },
  { id: 'target_dev', label: 'Target deviation per trial',       default: false,  type: 'compute', compute: 'target_dev' },
  { id: 'cv_bar',     label: 'Coefficient of variation',         default: false, type: 'graph',   graph: 'cv_bar' },
];

// H-Walker firmware CSV (force + IMU + motor + FF combined)
const MIXED_RECIPES: CanonicalRecipe[] = [
  // ── Core kinetic (cable assist force)
  { id: 'load_lr',      label: 'Loadcell · L / R subplots (GCP-based)', default: false, type: 'graph',   graph: 'force_lr_subplot' },
  { id: 'load_avg',     label: 'Loadcell waveform · mean ± SD',         default: false, type: 'graph',   graph: 'force_avg' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',          default: false, type: 'graph',   graph: 'asymmetry' },
  { id: 'per_stride',   label: 'Stride-by-stride table',                default: false, type: 'compute', compute: 'per_stride' },
  // ── Core motion (stride-averaged kinematics)
  { id: 'joint_avg',    label: 'Joint angle · mean ± SD per cycle',     default: false, type: 'graph',   graph: 'imu_avg' },
  { id: 'rom_bar',      label: 'ROM bar (joint × plane × side)',        default: false, type: 'graph',   graph: 'rom_bar' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',              default: false, type: 'graph',   graph: 'stance_swing_bar' },
  // ── Core scalars (whole-trial averages — one row each)
  { id: 'stride_len',   label: 'Stride length (avg, ZUPT)',             default: false, type: 'compute', compute: 'stride_length' },
  { id: 'cadence',      label: 'Cadence (avg spm)',                     default: false, type: 'compute', compute: 'cadence' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)',       default: false, type: 'graph',   graph: 'symmetry_radar' },
  // ── Motor / control tracking (whole-trial RMSE / MAE / peak / R²)
  { id: 'vel_track',    label: 'Motor velocity tracking (Des vs Act)',  default: false, type: 'compute', compute: 'velocity_tracking' },
  { id: 'pos_track',    label: 'Motor position tracking (Des vs Act)',  default: false, type: 'compute', compute: 'position_tracking' },
  { id: 'cur_track',    label: 'Motor current tracking (Des vs Act)',   default: false, type: 'compute', compute: 'current_tracking' },
  { id: 'feedforward',  label: 'Feedforward channels (motion / treadmill / gain)', default: false, type: 'compute', compute: 'feedforward' },
  // ── Bookshelf (off by default — tick to add)
  { id: 'load_raw',     label: 'Loadcell raw · L vs R overlay',         default: false, type: 'graph',   graph: 'force' },
  { id: 'loading_rate', label: 'Loading rate (0–50 ms after HS)',       default: false, type: 'compute', compute: 'loading_rate' },
  { id: 'impulse',      label: 'Impulse (∫F·dt) per stride',            default: false, type: 'compute', compute: 'impulse' },
  { id: 'cyclogram',    label: 'Cyclogram (proximal vs distal joint)',  default: false, type: 'graph',   graph: 'cyclogram' },
  { id: 'stride_trend', label: 'Stride-time trend (fatigue)',           default: false, type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom',          label: 'ROM per stride table (per channel)',    default: false, type: 'compute', compute: 'rom' },
  { id: 'fatigue',      label: 'Fatigue index',                         default: false, type: 'compute', compute: 'fatigue_index' },
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
