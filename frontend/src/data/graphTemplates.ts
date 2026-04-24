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
  // ── Force / Kinetic ──────────────────────────────────────────
  force_lr_subplot: {
    ey: 'Force · L / R subplots', title: 'GCP-normalized force per leg', ds: 'ds1',
    yUnit: 'Force (N)', xUnit: 'Gait cycle (%)',
    bands: [
      { c: '#3B82C4', opacity: 0.15,
        upper: 'M48,148 C70,144 92,108 114,58 C138,24 158,14 180,28 C202,44 224,66 246,96 C270,126 290,138 312,136 C332,134 354,120 376,108 C394,100 402,108 408,124',
        lower: 'M48,172 C70,167 92,132 114,86 C138,52 158,42 180,56 C202,72 224,94 246,124 C270,154 290,166 312,164 C332,162 354,148 376,136 C394,128 402,136 408,152' },
    ],
    paths: [
      { c: '#1E5F9E', w: 2.0, label: 'L actual',  d: 'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138' },
      { c: '#7FB5E4', w: 1.3, label: 'L desired', d: 'M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140', dash: '4 3' },
    ],
    yTicks: ['60', '45', '30', '15', '0'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['L peak', '48.2 N'], ['R peak', '46.7 N'], ['asym', '3.2%']],
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
      { c: COLORS.accent, w: 1.8, label: 'asym_idx', d: 'M48,120 L76,98 L102,115 L128,105 L156,90 L184,110 L210,95 L238,118 L264,100 L292,85 L318,112 L348,102 L376,92 L408,106' },
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

  force_tracking: {
    ey: 'ILC · RMSE per stride', title: 'Cable force tracking convergence', ds: 'ds1',
    yUnit: 'RMSE (N)', xUnit: 'Stride #',
    paths: [
      { c: '#3B82C4', w: 1.8, label: 'L RMSE',  d: 'M48,60 L90,54 L130,72 L170,68 L210,76 L250,74 L290,80 L330,78 L370,84 L408,82' },
      { c: '#D35454', w: 1.8, label: 'R RMSE',  d: 'M48,68 L90,62 L130,78 L170,74 L210,82 L250,80 L290,88 L330,84 L370,90 L408,88' },
      { c: '#7FB5E4', w: 1.0, label: 'L mean',  d: 'M48,80 L408,80', dash: '4 3' },
      { c: '#E89B9B', w: 1.0, label: 'R mean',  d: 'M48,87 L408,87', dash: '4 3' },
    ],
    yTicks: ['8', '6', '4', '2', '0'], xTicks: ['1', '5', '10', '15', '20'],
    summary: [['L RMSE', '3.8 N'], ['R RMSE', '4.1 N'], ['bias', '+0.2 N']],
  },

  // ── Kinematics ───────────────────────────────────────────────
  kinematics_ensemble: {
    ey: 'Kinematics · ensemble', title: 'Joint angle over gait cycle (avg ± SD)', ds: 'ds2',
    yUnit: 'Angle (°)', xUnit: 'Gait cycle (%)',
    bands: [
      { c: '#3B82C4', opacity: 0.18,
        upper: 'M48,100 C70,70 92,40 114,60 C138,80 158,130 180,140 C202,140 224,90 246,60 C268,50 290,110 312,140 C332,140 354,100 376,70 C394,55 402,80 408,100',
        lower: 'M48,120 C70,90 92,60 114,80 C138,100 158,150 180,160 C202,160 224,110 246,80 C268,70 290,130 312,160 C332,160 354,120 376,90 C394,75 402,100 408,120' },
    ],
    paths: [
      { c: '#1E5F9E', w: 2.0, label: 'L mean', d: 'M48,110 C70,80 92,50 114,70 C138,90 158,140 180,150 C202,150 224,100 246,70 C268,60 290,120 312,150 C332,150 354,110 376,80 C394,65 402,90 408,110' },
      { c: '#9E3838', w: 2.0, label: 'R mean', d: 'M48,115 C70,85 92,65 114,80 C138,95 158,135 180,142 C202,148 224,105 246,78 C268,68 290,122 312,145 C332,148 354,115 376,85 C394,72 402,92 408,112' },
    ],
    yTicks: ['+30', '+15', '0', '−15', '−30'], xTicks: ['0', '25', '50', '75', '100'],
    summary: [['ROM L', '38°'], ['ROM R', '37°'], ['asym', '2.7%'], ['note', 'Hip/Knee/Ankle or IMU']],
  },

  // ── Spatiotemporal ───────────────────────────────────────────
  spatiotemporal_bar: {
    ey: 'Spatiotemporal', title: 'Cadence · stride length · symmetry', ds: 'ds1',
    yUnit: '', xUnit: '',
    bars: [
      { x: 65,  w: 30, h: 108, c: '#1E5F9E', label: 'cad L' },
      { x: 105, w: 30, h: 112, c: '#9E3838', label: 'cad R' },
      { x: 185, w: 30, h: 90,  c: '#1E5F9E', label: 'len L' },
      { x: 225, w: 30, h: 88,  c: '#9E3838', label: 'len R' },
      { x: 310, w: 30, h: 36,  c: COLORS.accent, label: 'T asym' },
      { x: 350, w: 30, h: 56,  c: COLORS.accent, label: 'L asym' },
      { x: 390, w: 30, h: 28,  c: COLORS.accent, label: 'St' },
    ],
    yTicks: ['120', '90', '60', '30', '0'], xTicks: ['Cadence', 'Stride L', 'Symmetry'],
    summary: [['cadence', '112/110 spm'], ['stride L', '1.24/1.21 m'], ['max asym', '3.8%']],
  },

  stride_time_trend: {
    ey: 'Temporal · fatigue', title: 'Stride time over strides', ds: 'ds1',
    yUnit: 'Stride T (s)', xUnit: 'Stride #',
    paths: [
      { c: '#3B82C4', w: 1.6, label: 'L', d: 'M48,100 L80,96 L120,104 L160,100 L200,108 L240,104 L280,112 L320,108 L360,116 L408,112' },
      { c: '#D35454', w: 1.6, label: 'R', d: 'M48,104 L80,100 L120,108 L160,104 L200,112 L240,108 L280,116 L320,112 L360,120 L408,116' },
    ],
    yTicks: ['1.20', '1.10', '1.00', '0.90', '0.80'], xTicks: ['1', '5', '10', '15', '20'],
    summary: [['slope L', '+0.3 ms/str'], ['slope R', '+0.4 ms/str']],
  },

  stance_swing_bar: {
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

  // ── Stability ─────────────────────────────────────────────────
  mos_trajectory: {
    ey: 'MoS · XCoM', title: 'Margin of Stability — XCoM trajectory', ds: 'ds1',
    yUnit: 'Distance (m)', xUnit: 'Time (s)',
    paths: [
      { c: '#00FFB2', w: 1.8, label: 'XCoM AP', d: 'M48,100 C70,80 90,120 110,90 C130,70 150,110 170,95 C190,80 210,115 230,98 C250,82 270,118 290,102 C310,85 330,115 350,100 C370,88 390,112 408,100' },
      { c: '#A78BFA', w: 1.4, label: 'MoS AP',  d: 'M48,140 C70,125 90,155 110,135 C130,118 150,148 170,130 C190,115 210,145 230,128 C250,112 270,142 290,126 C310,110 330,140 350,125 C370,112 390,138 408,128' },
    ],
    yTicks: ['0.3', '0.2', '0.1', '0.0', '−0.1'], xTicks: ['0', '5', '10', '15', '20'],
    summary: [['XCoM AP', '0.12 m'], ['MoS min', '0.04 m'], ['requires', 'XCoM columns']],
  },
};
