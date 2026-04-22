// Ported from core_v3.html :1102-1199 (GRAPH_TPLS)
import { COLORS } from './colors';

export interface GraphPath { c: string; w: number; label: string; d: string; dash?: string; }
export interface GraphBand { c: string; opacity: number; upper: string; lower: string; }
export interface GraphHline { y: number; c: string; dash: string; label: string; }
export interface GraphBox { x: number; label: string; c: string; min: number; q1: number; med: number; q3: number; max: number; }
export interface GraphBar { x: number; w: number; h: number; c: string; label: string; }

export interface GraphTemplate {
  ey: string;
  title: string;
  ds: string;
  yUnit: string;
  xUnit: string;
  paths?: GraphPath[];
  bands?: GraphBand[];
  hlines?: GraphHline[];
  boxes?: GraphBox[];
  bars?: GraphBar[];
  yTicks: string[];
  xTicks: string[];
  summary: Array<[string, string]>;
}

export const GRAPH_TPLS: Record<string, GraphTemplate> = {
  force: {
    ey: 'Force · L vs R', title: 'Ground reaction force', ds: 'ds1',
    yUnit: 'Force (N)', xUnit: 'Gait cycle (%)',
    paths: [
      { c: COLORS.lActual, w: 2, label: 'L Actual', d: 'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138' },
      { c: COLORS.lDesired, w: 1.3, label: 'L Desired', dash: '4 3', d: 'M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140' },
      { c: COLORS.rActual, w: 2, label: 'R Actual', d: 'M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136' },
      { c: COLORS.rDesired, w: 1.3, label: 'R Desired', dash: '4 3', d: 'M48,167 C70,162 92,154 114,114 C138,68 160,54 180,70 C202,88 224,104 246,132 C270,150 292,156 312,154 C332,150 354,138 376,126 C394,114 402,124 408,138' },
    ],
    yTicks: ['60', '45', '30', '15', '0'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['n strides', '14'], ['peak ΔL', '48.2 N'], ['peak ΔR', '46.7 N'], ['asym', '3.2%']],
  },
  imu: {
    ey: 'IMU · Pitch', title: 'Shank vs thigh pitch', ds: 'ds2',
    yUnit: 'Pitch (°)', xUnit: 'Time (s)',
    paths: [
      { c: COLORS.lActual, w: 1.8, label: 'Shank', d: 'M48,100 C70,70 92,40 114,50 C136,60 158,130 180,140 C202,150 224,90 246,60 C268,50 290,110 312,140 C332,150 354,100 376,70 C394,55 402,80 408,100' },
      { c: COLORS.rActual, w: 1.8, label: 'Thigh', d: 'M48,110 C70,90 92,70 114,78 C138,88 158,120 180,126 C204,132 224,100 246,82 C268,75 290,108 312,128 C332,136 354,108 376,88 C394,78 402,90 408,102' },
    ],
    yTicks: ['+20', '+10', '0', '−10', '−20'], xTicks: ['0', '2', '4', '6', '8'],
    summary: [['strides', '3'], ['cadence', '112 spm'], ['stride T', '1.08 s']],
  },
  force_avg: {
    ey: 'Force · mean ± SD', title: 'GRF stride-averaged (n=14)', ds: 'ds1',
    yUnit: 'Vertical GRF (N)', xUnit: 'Gait cycle (%)',
    bands: [
      { c: '#3B82C4', opacity: 0.18,
        upper: 'M48,148 C70,144 92,108 114,58 C138,24 158,14 180,28 C202,44 224,66 246,96 C270,126 290,138 312,136 C332,134 354,120 376,108 C394,100 402,108 408,124',
        lower: 'M48,172 C70,167 92,132 114,86 C138,52 158,42 180,56 C202,72 224,94 246,124 C270,154 290,166 312,164 C332,162 354,148 376,136 C394,128 402,136 408,152' },
      { c: '#D35454', opacity: 0.18,
        upper: 'M48,153 C70,148 92,138 114,94 C138,48 160,34 180,50 C202,68 224,86 246,116 C270,136 292,142 312,138 C332,136 354,124 376,110 C394,100 402,108 408,122',
        lower: 'M48,177 C70,172 92,162 114,122 C138,76 160,62 180,78 C202,96 224,114 246,144 C270,164 292,170 312,166 C332,164 354,152 376,138 C394,128 402,136 408,150' },
    ],
    paths: [
      { c: '#1E5F9E', w: 2, label: 'L mean', d: 'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138' },
      { c: '#9E3838', w: 2, label: 'R mean', d: 'M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136' },
    ],
    yTicks: ['60', '45', '30', '15', '0'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['n strides', '14'], ['mean peak L', '48.2 ± 0.6 N'], ['mean peak R', '46.7 ± 0.7 N'], ['CV', '1.3%']],
  },
  asymmetry: {
    ey: 'Asymmetry · per stride', title: 'Asymmetry index across strides', ds: 'ds1',
    yUnit: 'Asymmetry (%)', xUnit: 'Stride #',
    paths: [
      { c: '#F09708', w: 1.8, label: 'asym_idx', d: 'M48,120 L76,98 L102,115 L128,105 L156,90 L184,110 L210,95 L238,118 L264,100 L292,85 L318,112 L348,102 L376,92 L408,106' },
    ],
    hlines: [{ y: 140, c: '#6B7280', dash: '3 3', label: '5% threshold' }],
    yTicks: ['10', '7.5', '5', '2.5', '0'], xTicks: ['1', '4', '7', '10', '14'],
    summary: [['mean', '2.1 ± 0.8%'], ['max', '3.6%'], ['≥5%', '0 strides']],
  },
  peak_box: {
    ey: 'Peak force · L vs R', title: 'Peak vertical GRF — boxplot', ds: 'ds1',
    yUnit: 'Peak GRF (N)', xUnit: '',
    boxes: [
      { x: 140, label: 'L', c: '#3B82C4', min: 170, q1: 162, med: 158, q3: 155, max: 148 },
      { x: 280, label: 'R', c: '#D35454', min: 175, q1: 167, med: 163, q3: 160, max: 152 },
    ],
    yTicks: ['50', '48', '46', '44', '42'], xTicks: [],
    summary: [['n=14', 'paired'], ['Δ mean', '+1.5 N'], ['p', '.006']],
  },
  cop: {
    ey: 'CoP · trajectory', title: 'Center of pressure path', ds: 'ds1',
    yUnit: 'AP (mm)', xUnit: 'ML (mm)',
    paths: [
      { c: '#3B82C4', w: 1.6, label: 'L CoP', d: 'M100,160 C110,140 115,120 120,100 C125,80 130,60 140,40 C145,35 150,35 155,40' },
      { c: '#D35454', w: 1.6, label: 'R CoP', d: 'M300,160 C295,140 290,120 285,100 C280,80 275,60 268,40 C263,35 258,35 255,40' },
    ],
    yTicks: ['+50', '+25', '0', '−25', '−50'], xTicks: ['−40', '−20', '0', '+20', '+40'],
    summary: [['L path', '142 mm'], ['R path', '138 mm'], ['Δ', '+2.9%']],
  },
  cv_bar: {
    ey: 'Variability · CV', title: 'Coefficient of variation per trial', ds: 'ds3',
    yUnit: 'CV (%)', xUnit: 'Trial',
    bars: [
      { x: 80, w: 40, h: 60, c: '#7FB5E4', label: 'T1' },
      { x: 150, w: 40, h: 48, c: '#3B82C4', label: 'T2' },
      { x: 220, w: 40, h: 36, c: '#E89B9B', label: 'T3' },
      { x: 290, w: 40, h: 22, c: '#D35454', label: 'T4' },
      { x: 360, w: 40, h: 14, c: '#F09708', label: 'T5' },
    ],
    yTicks: ['8', '6', '4', '2', '0'], xTicks: ['T1', 'T2', 'T3', 'T4', 'T5'],
    summary: [['trials', '5'], ['improving', 'T1→T5'], ['final CV', '0.7%']],
  },
  trials: {
    ey: 'Trials · N=5', title: 'Trial overlay', ds: 'ds3',
    yUnit: 'Normalized force', xUnit: 'Gait cycle (%)',
    paths: [
      { c: '#7FB5E4', w: 1.4, label: 'Trial 1', d: 'M48,170 C82,150 112,100 150,60 C188,40 222,32 258,52 C292,78 326,130 360,160 C384,172 398,168 408,164' },
      { c: '#3B82C4', w: 1.4, label: 'Trial 2', d: 'M48,172 C82,154 112,104 150,66 C188,46 222,38 258,58 C292,82 326,132 360,160 C384,170 398,168 408,166' },
      { c: '#E89B9B', w: 1.4, label: 'Trial 3', d: 'M48,168 C82,148 112,98 150,58 C188,38 222,30 258,50 C292,76 326,128 360,158 C384,170 398,166 408,162' },
      { c: '#D35454', w: 1.4, label: 'Trial 4', d: 'M48,174 C82,156 112,108 150,70 C188,50 222,42 258,60 C292,84 326,134 360,162 C384,172 398,170 408,168' },
      { c: COLORS.accent, w: 2.2, label: 'Trial 5 · target', d: 'M48,166 C82,146 112,94 150,54 C188,34 222,26 258,46 C292,72 326,124 360,154 C384,168 398,164 408,160' },
    ],
    yTicks: ['1.0', '0.75', '0.5', '0.25', '0'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['trials', '5'], ['CV', '4.1%'], ['target Δ', '+2.3%']],
  },

  // =====================================================
  // Phase 2I · Debug raw time-series (full duration + HS markers)
  // =====================================================
  'debug_ts': {
    ey: 'Debug · raw time-series', title: 'Raw signals with heel-strike markers', ds: 'ds1',
    yUnit: '', xUnit: 'Time (s)',
    paths: [
      { c: '#1E5F9E', w: 1.2, label: 'L_ActForce_N', d: 'M48,100 C80,60 120,150 160,80 C200,40 240,140 280,90 C320,50 360,150 408,100' },
      { c: '#9E3838', w: 1.2, label: 'R_ActForce_N', d: 'M48,110 C80,70 120,160 160,90 C200,50 240,150 280,100 C320,60 360,160 408,110' },
    ],
    yTicks: ['', '', '', '', ''], xTicks: ['0', '5', '10', '15', '20'],
    summary: [['hint', 'dotted = heel-strikes'], ['purpose', 'find anomalies']],
  },

  // =====================================================
  // Phase 2H · L/R GCP subplot — top-requested kinetic figure
  // (fallback mock; real backend renders true 1×2 matplotlib subplot)
  // =====================================================
  'force_lr_subplot': {
    ey: 'Force · L / R subplots', title: 'GCP-normalized force per leg', ds: 'ds1',
    yUnit: 'Force (N)', xUnit: 'Gait cycle (%)',
    paths: [
      { c: '#1E5F9E', w: 2.0, label: 'L actual',  d: 'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138' },
      { c: '#7FB5E4', w: 1.3, label: 'L desired', d: 'M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140', dash: '4 3' },
    ],
    yTicks: ['60', '45', '30', '15', '0'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['L peak', '48.2 N'], ['R peak', '46.7 N'], ['asym', '3.2%']],
  },

  // =====================================================
  // Phase 0 · Motion / kinematic templates (fallback mockups;
  // real data replaces these when cell has a dataset bound).
  // =====================================================
  'imu_avg': {
    ey: 'Kinematics · mean ± SD', title: 'Joint angle over gait cycle', ds: 'ds2',
    yUnit: 'Pitch (°)', xUnit: 'Gait cycle (%)',
    paths: [
      { c: '#1E5F9E', w: 2.0, label: 'L shank', d: 'M48,100 C70,70 92,40 114,60 C138,80 158,130 180,140 C202,140 224,90 246,60 C268,50 290,110 312,140 C332,140 354,100 376,70 C394,55 402,80 408,100' },
      { c: '#9E3838', w: 2.0, label: 'R shank', d: 'M48,110 C70,90 92,70 114,78 C138,88 158,120 180,126 C204,132 224,100 246,82 C268,75 290,108 312,128 C332,136 354,108 376,88 C394,78 402,90 408,102' },
    ],
    yTicks: ['+20', '+10', '0', '−10', '−20'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['ROM L', '38.4°'], ['ROM R', '37.1°'], ['asym', '3.4%']],
  },
  'cyclogram': {
    ey: 'Phase portrait', title: 'Shank vs thigh cyclogram', ds: 'ds2',
    yUnit: 'Thigh pitch (°)', xUnit: 'Shank pitch (°)',
    paths: [
      { c: COLORS.accent, w: 1.8, label: 'Cycle avg', d: 'M150,100 C120,60 140,30 200,40 C260,50 300,80 340,110 C340,140 280,160 220,150 C160,140 180,120 150,100' },
    ],
    yTicks: ['+30', '+15', '0', '−15', '−30'], xTicks: ['−20', '−10', '0', '+10', '+20'],
    summary: [['cycle', 'closed'], ['phase lag', '12°']],
  },
  'stride_time_trend': {
    ey: 'Temporal · fatigue', title: 'Stride time over strides', ds: 'ds1',
    yUnit: 'Stride T (s)', xUnit: 'Stride #',
    paths: [
      { c: '#3B82C4', w: 1.6, label: 'L', d: 'M48,100 L80,96 L120,104 L160,100 L200,108 L240,104 L280,112 L320,108 L360,116 L408,112' },
      { c: '#D35454', w: 1.6, label: 'R', d: 'M48,104 L80,100 L120,108 L160,104 L200,112 L240,108 L280,116 L320,112 L360,120 L408,116' },
    ],
    yTicks: ['1.20', '1.10', '1.00', '0.90', '0.80'], xTicks: ['1', '5', '10', '15', '20'],
    summary: [['slope L', '+0.3 ms/str'], ['slope R', '+0.4 ms/str']],
  },
  'stance_swing_bar': {
    ey: 'Temporal phases', title: 'Stance / swing percentages', ds: 'ds1',
    yUnit: '% gait cycle', xUnit: '',
    bars: [
      { x: 80,  w: 40, h: 120, c: '#3B82C4', label: 'L stance' },
      { x: 170, w: 40, h: 52,  c: '#7FB5E4', label: 'L swing' },
      { x: 260, w: 40, h: 116, c: '#D35454', label: 'R stance' },
      { x: 350, w: 40, h: 56,  c: '#E89B9B', label: 'R swing' },
    ],
    yTicks: ['100', '75', '50', '25', '0'], xTicks: ['L stance', 'L swing', 'R stance', 'R swing'],
    summary: [['L stance', '62%'], ['R stance', '60%'], ['asym', '3.3%']],
  },
  'rom_bar': {
    ey: 'Kinematics · ROM', title: 'Range of motion by joint/plane', ds: 'ds2',
    yUnit: 'ROM (°)', xUnit: '',
    bars: [
      { x: 80,  w: 40, h: 130, c: '#3B82C4', label: 'L sag' },
      { x: 170, w: 40, h: 40,  c: '#7FB5E4', label: 'L fro' },
      { x: 260, w: 40, h: 126, c: '#D35454', label: 'R sag' },
      { x: 350, w: 40, h: 36,  c: '#E89B9B', label: 'R fro' },
    ],
    yTicks: ['60', '45', '30', '15', '0'], xTicks: ['L sag', 'L fro', 'R sag', 'R fro'],
    summary: [['L sagittal', '38.4°'], ['R sagittal', '36.8°']],
  },
  'symmetry_radar': {
    ey: 'Symmetry', title: 'Symmetry summary (0 = perfect)', ds: 'ds1',
    yUnit: 'Asymmetry (%)', xUnit: '',
    bars: [
      { x: 70,  w: 44, h: 36, c: COLORS.accent, label: 'stride T' },
      { x: 150, w: 44, h: 60, c: COLORS.accent, label: 'stride L' },
      { x: 230, w: 44, h: 32, c: COLORS.accent, label: 'stance' },
      { x: 310, w: 44, h: 50, c: COLORS.accent, label: 'force' },
      { x: 385, w: 44, h: 42, c: COLORS.accent, label: 'peak' },
    ],
    yTicks: ['10', '7.5', '5', '2.5', '0'], xTicks: ['T', 'L', 'St', 'F', 'Pk'],
    summary: [['avg', '3.9%'], ['max', 'stride L · 5.6%']],
  },
};
