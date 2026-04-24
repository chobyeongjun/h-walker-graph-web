// Canonical recipes — the standard set of figures + tables a gait
// biomechanics paper / meeting deck would typically include.
//
// Philosophy (post user directive "정말 필요한 그림들만 그리고, 그
// 다음은 미리 만들어놓은 책장에서 책을 꺼내쓰듯이"):
//
//   default:true  → only the 1-2 figures the user almost always wants
//                   immediately on upload. Auto-running 10 cells was
//                   "Too much"; users can click anything else from the
//                   Library bookshelf in one click.
//   default:false → bookshelf-only. Visible in the Library panel; not
//                   auto-created. Tick the recipe and "Apply selected"
//                   if you want it batched into the dataset's defaults.
//
// Scalar-first rule: whole-trial parameters (cadence, stride length,
// ROM, fatigue) ship as compute-cell summaries (1-row scalar ± SD).
// Per-stride or per-window time-series of those values are advanced and
// must be explicitly requested.
//
// Removed (per user directive):
//   - peak_box  : L-vs-R peak boxplot adds little beyond the asymmetry
//                 series + per-stride table.
//   - debug_ts  : the cluttered all-channel raw time-series with no zoom.
//                 Replaced by the per-stride crop / inspector workflow.
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
  // ── Core (publication-ready kinetics)
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP-based)',    default: false,  type: 'graph',   graph: 'force_lr_subplot',
    hint: 'Side-by-side panels, one per leg, both GCP-normalized with desired overlay. The standard paper Figure 1.' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD (overlay)',  default: false,  type: 'graph',   graph: 'force_avg',
    hint: 'Vertical ground reaction force averaged across strides, normalized to 0-100% gait cycle.' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',        default: false,  type: 'graph',   graph: 'asymmetry',
    hint: 'Peak L vs R force asymmetry for each stride. 0% = perfectly symmetric.' },
  { id: 'per_stride',   label: 'Stride-by-stride table',              default: false,  type: 'compute', compute: 'per_stride',
    hint: 'One row per stride: peak_L, peak_R, stride time, asymmetry.' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)',     default: false,  type: 'graph',   graph: 'symmetry_radar',
    hint: 'Radar plot of % asymmetry across stride time / length / force / stance / peak.' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',            default: false,  type: 'graph',   graph: 'stance_swing_bar',
    hint: '% of gait cycle spent in stance vs swing, L and R.' },
  // ── Bookshelf (off by default — tick to add, or ask the LLM)
  { id: 'grf_raw',      label: 'GRF raw · L vs R overlay',            default: false, type: 'graph',   graph: 'force',
    hint: 'Instantaneous force overlay over the full trial. Use the per-stride inspector for zoom-in debugging.' },
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',               default: false, type: 'compute', compute: 'loading_rate',
    hint: 'Slope of force rise immediately after heel-strike (BW/s).' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                     default: false, type: 'compute', compute: 'impulse',
    hint: 'Time integral of vertical force per stride. Usually only needed for mechanical work analyses.' },
  { id: 'cop',          label: 'Center-of-pressure trajectory',       default: false, type: 'graph',   graph: 'cop',
    hint: 'AP vs ML path of CoP during stance. Requires force-plate grid.' },
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

// H-Walker 67-col firmware CSV (force + IMU combined)
const MIXED_RECIPES: CanonicalRecipe[] = [
  // ── Core force (waveforms — shape matters, stay as graphs)
  { id: 'grf_lr',       label: 'GRF · L / R subplots (GCP-based)', default: false,  type: 'graph',   graph: 'force_lr_subplot' },
  { id: 'grf_avg',      label: 'GRF waveform · mean ± SD',         default: false,  type: 'graph',   graph: 'force_avg' },
  { id: 'asymmetry',    label: 'Asymmetry index · per stride',    default: false,  type: 'graph',   graph: 'asymmetry' },
  { id: 'per_stride',   label: 'Stride-by-stride table',          default: false,  type: 'compute', compute: 'per_stride' },
  // ── Core motion (stride-averaged kinematics)
  { id: 'joint_avg',    label: 'Joint angle · mean ± SD per cycle', default: false, type: 'graph',   graph: 'imu_avg' },
  { id: 'rom_bar',      label: 'ROM bar (joint × plane × side)',  default: false,  type: 'graph',   graph: 'rom_bar' },
  { id: 'stance_swing', label: 'Stance / swing phase bar',        default: false,  type: 'graph',   graph: 'stance_swing_bar' },
  // ── Core scalars (whole-trial averages — one row each)
  { id: 'stride_len',   label: 'Stride length (avg, ZUPT)',       default: false,  type: 'compute', compute: 'stride_length' },
  { id: 'cadence',      label: 'Cadence (avg spm)',               default: false,  type: 'compute', compute: 'cadence' },
  { id: 'symmetry',     label: 'Symmetry summary (multi-metric)', default: false,  type: 'graph',   graph: 'symmetry_radar' },
  // ── Bookshelf (off by default — tick to add, or ask the LLM)
  { id: 'grf_raw',      label: 'GRF raw · L vs R overlay',        default: false, type: 'graph',   graph: 'force' },
  { id: 'loading_rate', label: 'Loading rate (0–50ms)',           default: false, type: 'compute', compute: 'loading_rate' },
  { id: 'impulse',      label: 'Impulse (∫F·dt)',                 default: false, type: 'compute', compute: 'impulse' },
  { id: 'cyclogram',    label: 'Cyclogram (proximal vs distal joint)', default: false, type: 'graph',   graph: 'cyclogram' },
  { id: 'stride_trend', label: 'Stride-time trend (fatigue)',     default: false, type: 'graph',   graph: 'stride_time_trend' },
  { id: 'rom',          label: 'ROM per stride table (per channel)', default: false, type: 'compute', compute: 'rom' },
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
