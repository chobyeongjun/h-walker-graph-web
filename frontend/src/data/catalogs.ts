// Ported from core_v3.html :2470-2519 (HISTORY, STATS_LIB, EXPORT_FORMATS)

export interface HistoryEntry {
  t: string;
  label: string;
  kind: 'edit' | 'llm' | 'saved' | 'preset' | 'upload' | 'map' | 'create';
  actor: string;
  cells: string;
  saved?: boolean;
}

export const HISTORY: HistoryEntry[] = [
  { t: '2m ago',  label: 'Added Asymmetry index graph',        kind: 'edit',   actor: 'you',    cells: '6 cells' },
  { t: '8m ago',  label: 'Claude · paired t-test (c2)',        kind: 'llm',    actor: 'Claude', cells: '5 cells' },
  { t: '14m ago', label: 'Checkpoint · v3-draft',              kind: 'saved',  actor: 'you',    cells: '5 cells', saved: true },
  { t: '22m ago', label: 'Applied IEEE preset (bulk)',         kind: 'preset', actor: 'you',    cells: '5 cells' },
  { t: '31m ago', label: 'Imported pilot_run.csv (5000 rows)', kind: 'upload', actor: 'you',    cells: '4 cells' },
  { t: '45m ago', label: 'Mapped columns · trial_1_force',     kind: 'map',    actor: 'you',    cells: '3 cells' },
  { t: '1h ago',  label: 'Created page · pilot_subject_03',    kind: 'create', actor: 'you',    cells: '0 cells', saved: true },
];

export interface StatLibEntry {
  name: string;
  tag: string;
  desc: string;
  when: string;
  op: string;
}

export const STATS_LIB: StatLibEntry[] = [
  { name: 'Paired t-test',        tag: 'parametric',     desc: 'L vs R within-subject. Assumes normal differences.',
    when: 'Same subject, two conditions · e.g. L/R limb peak force', op: 'ttest_paired' },
  { name: "Welch's t-test",       tag: 'parametric',     desc: 'Two independent samples, unequal variances. Safer default than Student t.',
    when: 'Two groups · e.g. pre vs post, healthy vs patient', op: 'ttest_welch' },
  { name: 'One-way ANOVA',        tag: 'parametric',     desc: 'Compare means across ≥3 groups. Tukey HSD for pairwise.',
    when: 'Trials 1–5 · progressive change across sessions', op: 'anova' },
  { name: 'Pearson correlation',  tag: 'association',    desc: 'Linear relationship strength, -1…+1.',
    when: 'L force vs R force sample-by-sample', op: 'corr' },
  { name: "Cohen's d",            tag: 'effect size',    desc: 'Standardized mean difference · interpret regardless of sample size.',
    when: 'Report alongside every t-test (APA requirement)', op: 'cohen' },
  { name: 'Mann-Whitney U',       tag: 'non-parametric', desc: 'Rank-based Welch · when normality fails.',
    when: 'Small n (<15) or skewed data', op: 'mwu' },
  { name: 'Wilcoxon signed-rank', tag: 'non-parametric', desc: 'Paired non-parametric t-test.',
    when: 'Paired L/R but small or skewed', op: 'wilcoxon' },
  { name: 'Shapiro-Wilk',         tag: 'assumption',     desc: 'Normality check before choosing parametric.',
    when: 'Run on residuals of each group · n < 50', op: 'shapiro' },
  { name: "Levene's test",        tag: 'assumption',     desc: 'Equal variance across groups.',
    when: 'Before ANOVA or Student t', op: 'levene' },
];

export interface ExportFormatEntry { name: string; sub: string; fmt: string; }

export const EXPORT_FORMATS: Record<string, ExportFormatEntry[]> = {
  graphs: [
    { name: 'SVG bundle',     sub: 'vector · per cell',         fmt: 'svg' },
    { name: 'PDF · A4 grid',  sub: 'all graphs one page',       fmt: 'pdf-grid' },
    { name: 'PDF · per cell', sub: 'one graph per page',        fmt: 'pdf-each' },
    { name: 'PNG @ 2x',       sub: 'display raster',            fmt: 'png2x' },
    { name: 'EPS',            sub: 'IEEE/Elsevier submission',  fmt: 'eps' },
    { name: 'TIFF @ DPI',     sub: 'Nature/MDPI submission',    fmt: 'tiff' },
  ],
  stats: [
    { name: 'APA report',  sub: 'docx · numbered',   fmt: 'apa-docx' },
    { name: 'IEEE inline', sub: 'md · plain text',   fmt: 'ieee-md' },
    { name: 'CSV',         sub: 't/F/p/d/CI95',      fmt: 'csv' },
  ],
  bundle: [
    { name: 'Full page', sub: 'HTML · self-contained', fmt: 'html-bundle' },
    { name: 'Notebook',  sub: '.ipynb replay',         fmt: 'ipynb' },
  ],
};
