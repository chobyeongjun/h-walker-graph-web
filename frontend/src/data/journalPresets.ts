// Ported verbatim from core_v3.html :836-964 (JOURNAL_PRESETS)
export interface JournalPreset {
  name: string;
  full: string;
  col1: { w: number; h: number };
  col2: { w: number; h: number };
  onehalf?: { w: number; h: number };
  maxH: number;
  font: string;
  fontFallback: string;
  sizes: { body: number; axis: number; legend: number; title: number; panel: number };
  stroke: number;
  grid: number;
  palette: string[];
  paletteColor: string[];
  colorblindSafe: boolean;
  bg: string;
  axisColor: string;
  gridColor: string;
  formats: string[];
  dpi: number;
  notes: string;
}

export const JOURNAL_PRESETS: Record<string, JournalPreset> = {
  ieee: {
    name: 'IEEE',
    full: 'IEEE Transactions / Journals',
    col1: { w: 88.9, h: 70 },
    col2: { w: 181, h: 90 },
    maxH: 216,
    font: 'Times New Roman',
    fontFallback: '"Times New Roman", Times, serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 1.0,
    grid: 0.4,
    palette: ['#000000', '#555555', '#888888', '#BBBBBB'],
    paletteColor: ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#CCCCCC',
    formats: ['PDF', 'EPS', 'TIFF', 'SVG', 'PNG'],
    dpi: 600,
    notes: 'One col 88.9mm / two col 181mm · 8–10pt Times · grayscale preferred · fonts embedded',
  },
  nature: {
    name: 'Nature',
    full: 'Nature · Nature journals',
    col1: { w: 89, h: 60 },
    col2: { w: 183, h: 90 },
    maxH: 247,
    font: 'Helvetica',
    fontFallback: 'Helvetica, Arial, sans-serif',
    sizes: { body: 7, axis: 7, legend: 6, title: 8, panel: 8 },
    stroke: 0.5,
    grid: 0.25,
    palette: ['#000000', '#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7'],
    paletteColor: ['#000000', '#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7'],
    colorblindSafe: true,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E5E5E5',
    formats: ['PDF', 'EPS', 'AI', 'TIFF'],
    dpi: 300,
    notes: 'Single 89mm / double 183mm · Helvetica 5–7pt · Wong colorblind-safe palette · vector editable',
  },
  apa: {
    name: 'APA',
    full: 'APA 7th edition',
    col1: { w: 85, h: 65 },
    col2: { w: 174, h: 100 },
    maxH: 235,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 10, axis: 10, legend: 9, title: 11, panel: 10 },
    stroke: 0.75,
    grid: 0.3,
    palette: ['#000000', '#555555', '#888888', '#BBBBBB'],
    paletteColor: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#DDDDDD',
    formats: ['PDF', 'SVG', 'PNG', 'TIFF'],
    dpi: 300,
    notes: 'Sans-serif (Arial/Calibri) · 8–14pt · grayscale preferred · figure note below',
  },
  elsevier: {
    name: 'Elsevier',
    full: 'Elsevier journals',
    col1: { w: 90, h: 60 },
    col2: { w: 190, h: 90 },
    onehalf: { w: 140, h: 80 },
    maxH: 240,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 9, panel: 8 },
    stroke: 0.5,
    grid: 0.25,
    palette: ['#000000', '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00'],
    paletteColor: ['#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33', '#A65628'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#DDDDDD',
    formats: ['EPS', 'PDF', 'TIFF', 'JPEG'],
    dpi: 300,
    notes: 'Single 90mm / 1.5 col 140mm / double 190mm · Arial/Courier/Times/Symbol · EPS preferred',
  },
  mdpi: {
    name: 'MDPI',
    full: 'MDPI (Applied Sciences, Sensors, etc.)',
    col1: { w: 85, h: 65 },
    col2: { w: 170, h: 90 },
    maxH: 225,
    font: 'Palatino',
    fontFallback: 'Palatino, "Palatino Linotype", "Book Antiqua", serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 0.75,
    grid: 0.3,
    palette: ['#000000', '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
    paletteColor: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'],
    colorblindSafe: false,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E0E0E0',
    formats: ['PDF', 'TIFF', 'PNG', 'EPS'],
    dpi: 1000,
    notes: 'Single 85mm / double 170mm · Palatino/Arial 8pt · 1000 dpi line art',
  },
  jner: {
    name: 'JNER',
    full: 'J. NeuroEngineering & Rehabilitation (BMC)',
    col1: { w: 85, h: 65 },
    col2: { w: 170, h: 90 },
    maxH: 225,
    font: 'Arial',
    fontFallback: 'Arial, Helvetica, sans-serif',
    sizes: { body: 8, axis: 8, legend: 7, title: 10, panel: 8 },
    stroke: 0.75,
    grid: 0.3,
    palette: ['#000000', '#0072B2', '#D55E00', '#009E73', '#CC79A7', '#F0E442'],
    paletteColor: ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#F0E442', '#56B4E9'],
    colorblindSafe: true,
    bg: '#ffffff',
    axisColor: '#000000',
    gridColor: '#E0E0E0',
    formats: ['PDF', 'EPS', 'PNG', 'TIFF'],
    dpi: 300,
    notes: 'Springer/BMC style · Arial 8pt · colorblind-safe recommended · 300 dpi raster',
  },
};

export type JournalKey = keyof typeof JOURNAL_PRESETS;
