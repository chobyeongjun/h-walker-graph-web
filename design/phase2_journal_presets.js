/* ============================================================
   H-Walker CORE — Journal Publication Presets
   Spec sourced from official submission guidelines (2025–2026):
     IEEE     · ieee.org author kit, Proceedings of the IEEE
     Nature   · nature.com/for-authors, research figure guide
     APA      · APA 7th (figure style)
     Elsevier · Artwork & media instructions
     MDPI     · applsci instructions (typical)
     JNER     · BioMed Central / Springer Nature (Arial)
   ============================================================ */

const JOURNAL_PRESETS = {
  ieee: {
    name: 'IEEE',
    full: 'IEEE Transactions / Journals',
    col1: { w: 88.9, h: 70 },   // mm — 3.5"
    col2: { w: 181,  h: 90 },   // mm — 7.16"
    maxH: 216,
    font: 'Times New Roman',
    fontFallback: '"Times New Roman", Times, serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 1.0,         // pt
    grid:   0.4,         // pt, light gray
    palette: ['#000000','#555555','#888888','#BBBBBB'],  // grayscale first
    paletteColor: ['#1f77b4','#d62728','#2ca02c','#ff7f0e','#9467bd'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#CCCCCC',
    formats: ['PDF','EPS','TIFF','SVG','PNG'],
    dpi: 600,            // line art
    notes: 'One col 88.9mm / two col 181mm · 8–10pt Times · grayscale preferred · fonts embedded',
  },
  nature: {
    name: 'Nature',
    full: 'Nature · Nature journals',
    col1: { w: 89,  h: 60 },
    col2: { w: 183, h: 90 },
    maxH: 247,
    font: 'Helvetica',
    fontFallback: 'Helvetica, Arial, sans-serif',
    sizes: { body: 7, axis: 7, legend: 6, title: 8, panel: 8 },
    stroke: 0.5,         // 0.25–1 pt range
    grid:   0.25,
    palette: ['#000000','#E69F00','#56B4E9','#009E73','#F0E442','#0072B2','#D55E00','#CC79A7'],
    paletteColor: ['#000000','#E69F00','#56B4E9','#009E73','#F0E442','#0072B2','#D55E00','#CC79A7'],
    colorblindSafe: true,  // Wong palette
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E5E5E5',
    formats: ['PDF','EPS','AI','TIFF'],
    dpi: 300,
    notes: 'Single 89mm / double 183mm · Helvetica 5–7pt · Wong colorblind-safe palette · vector editable',
  },
  apa: {
    name: 'APA',
    full: 'APA 7th edition',
    col1: { w: 85,  h: 65 },
    col2: { w: 174, h: 100 },
    maxH: 235,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 10, axis: 10, legend: 9, title: 11, panel: 10 },
    stroke: 0.75,
    grid:   0.3,
    palette: ['#000000','#555555','#888888','#BBBBBB'],
    paletteColor: ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#DDDDDD',
    formats: ['PDF','SVG','PNG','TIFF'],
    dpi: 300,
    notes: 'Sans-serif (Arial/Calibri) · 8–14pt · grayscale preferred · figure note below',
  },
  elsevier: {
    name: 'Elsevier',
    full: 'Elsevier journals',
    col1: { w: 90,  h: 60 },
    col2: { w: 190, h: 90 },
    onehalf: { w: 140, h: 80 },
    maxH: 240,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 9, panel: 8 },
    stroke: 0.5,
    grid:   0.25,
    palette: ['#000000','#E41A1C','#377EB8','#4DAF4A','#984EA3','#FF7F00'],
    paletteColor: ['#E41A1C','#377EB8','#4DAF4A','#984EA3','#FF7F00','#FFFF33','#A65628'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#DDDDDD',
    formats: ['EPS','PDF','TIFF','JPEG'],
    dpi: 300,
    notes: 'Single 90mm / 1.5 col 140mm / double 190mm · Arial/Courier/Times/Symbol · EPS preferred',
  },
  mdpi: {
    name: 'MDPI',
    full: 'MDPI (Applied Sciences, Sensors, etc.)',
    col1: { w: 85,  h: 65 },
    col2: { w: 170, h: 90 },
    maxH: 225,
    font: 'Palatino',
    fontFallback: 'Palatino, "Palatino Linotype", "Book Antiqua", serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 0.75,
    grid:   0.3,
    palette: ['#000000','#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd'],
    paletteColor: ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E0E0E0',
    formats: ['PDF','TIFF','PNG','EPS'],
    dpi: 1000,     // MDPI prefers 1000 dpi for line art
    notes: 'Single 85mm / double 170mm · Palatino/Arial 8pt · 1000 dpi line art',
  },
  jner: {
    name: 'JNER',
    full: 'J. NeuroEngineering & Rehabilitation (BMC)',
    col1: { w: 85,  h: 65 },
    col2: { w: 170, h: 90 },
    maxH: 225,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 0.75,
    grid:   0.3,
    palette: ['#000000','#0072B2','#D55E00','#009E73','#CC79A7','#F0E442'],
    paletteColor: ['#0072B2','#D55E00','#009E73','#CC79A7','#F0E442','#56B4E9'],
    colorblindSafe: true,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E0E0E0',
    formats: ['PDF','EPS','PNG','TIFF'],
    dpi: 300,
    notes: 'Springer/BMC style · Arial 8pt · colorblind-safe recommended · 300 dpi raster',
  },
};

/* Canonical recipes — auto-generate cells based on dataset type */
const CANONICAL_RECIPES = {
  force: [
    { id:'grf_avg',     label:'GRF waveform · mean ± SD',       default:true,  type:'graph', graph:'force_avg' },
    { id:'grf_raw',     label:'GRF raw waveform · L vs R',      default:true,  type:'graph', graph:'force' },
    { id:'per_stride',  label:'Per-stride metrics table',       default:true,  type:'compute', compute:'per_stride' },
    { id:'asymmetry',   label:'Asymmetry index · stride series',default:true,  type:'graph', graph:'asymmetry' },
    { id:'peak_box',    label:'Peak force · L vs R boxplot',    default:false, type:'graph', graph:'peak_box' },
    { id:'impulse',     label:'Impulse (force · time integral)',default:false, type:'compute', compute:'impulse' },
    { id:'cop',         label:'CoP trajectory',                 default:false, type:'graph', graph:'cop' },
    { id:'loading_rate',label:'Loading rate (0–50ms)',          default:false, type:'compute', compute:'loading_rate' },
  ],
  imu: [
    { id:'pitch_ts',    label:'Shank/thigh pitch · time series',default:true,  type:'graph', graph:'imu' },
    { id:'rom',         label:'ROM per stride',                 default:false, type:'compute', compute:'rom' },
    { id:'cadence',     label:'Cadence from heel-strike',       default:false, type:'compute', compute:'cadence' },
  ],
  trials: [
    { id:'overlay',     label:'Trial overlay (N=5)',            default:true,  type:'graph', graph:'trials' },
    { id:'target_dev',  label:'Target deviation per trial',     default:true,  type:'compute', compute:'target_dev' },
    { id:'cv_bar',      label:'Coefficient of variation · bar', default:false, type:'graph', graph:'cv_bar' },
  ],
};

/* Compute cell metric catalog — all available within-file metrics */
const COMPUTE_METRICS = {
  per_stride: {
    label: 'Per-stride metrics',
    cols: ['stride_#','peak_L (N)','peak_R (N)','stride_T (s)','asym_idx (%)'],
    rows: [
      ['1', '47.8', '45.1', '1.08', '2.9'],
      ['2', '48.5', '46.3', '1.07', '2.3'],
      ['3', '49.1', '46.8', '1.09', '2.4'],
      ['4', '48.2', '47.0', '1.08', '1.3'],
      ['5', '47.9', '46.5', '1.08', '1.5'],
      ['…', '…',    '…',    '…',    '…'  ],
      ['14','48.6', '46.9', '1.08', '1.8'],
    ],
    summary: { mean: ['48.2 ± 0.6', '46.7 ± 0.7', '1.08 ± 0.01', '2.1 ± 0.8'] },
  },
  impulse: {
    label: 'Impulse (N·s)',
    cols: ['stride_#','L impulse','R impulse','Δ (%)'],
    rows: [
      ['1','42.8','40.9','4.6'],
      ['2','43.1','41.2','4.6'],
      ['…','…','…','…'],
      ['14','43.0','41.1','4.6'],
    ],
    summary: { mean: ['43.0 ± 0.3', '41.1 ± 0.4', '4.6 ± 0.3'] },
  },
  loading_rate: {
    label: 'Loading rate (BW/s, 0–50ms)',
    cols: ['stride_#','L rate','R rate','Δ'],
    rows: [['1','68.2','62.1','6.1'],['2','67.8','62.5','5.3'],['…','…','…','…']],
    summary: { mean: ['68.0 ± 1.2', '62.3 ± 1.4', '5.7 ± 0.9'] },
  },
  rom: {
    label: 'ROM per stride',
    cols: ['stride','shank ROM (°)','thigh ROM (°)'],
    rows: [['1','42.1','38.5'],['2','41.8','38.2'],['3','42.4','38.8']],
    summary: { mean: ['42.1 ± 0.3', '38.5 ± 0.3'] },
  },
  cadence: {
    label: 'Cadence',
    cols: ['window','spm'],
    rows: [['0-4s','110'],['4-8s','114']],
    summary: { mean: ['112 ± 2'] },
  },
  target_dev: {
    label: 'Target deviation',
    cols: ['trial','RMSE','peak Δ (%)'],
    rows: [['T1','6.8','-4.2'],['T2','5.1','-2.8'],['T3','4.2','-1.9'],['T4','3.0','+0.4'],['T5','2.3','+2.3']],
    summary: { mean: ['4.3 ± 1.8', 'improving'] },
  },
};

if (typeof window !== 'undefined') {
  window.JOURNAL_PRESETS = JOURNAL_PRESETS;
  window.CANONICAL_RECIPES = CANONICAL_RECIPES;
  window.COMPUTE_METRICS = COMPUTE_METRICS;
}

