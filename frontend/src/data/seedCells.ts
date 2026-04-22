// Ported from core_v3.html :1241-1264 (initial cells seed)
import type { Cell } from '../store/workspace';

export const SEED_CELLS: Cell[] = [
  { id: 'c1', type: 'graph', graph: 'force', dsIds: ['ds1'] },
  { id: 'c2', type: 'stat',
    op: 'ttest_paired',
    inputs: { a: 'L Actual', b: 'R Actual' },
    dsIds: ['ds1'],
    fmt: 'apa',
  },
  { id: 'c3', type: 'graph', graph: 'imu', dsIds: ['ds2'] },
  { id: 'c4', type: 'llm',
    dsIds: ['ds1'],
    prompt: 'Compare L/R peak force asymmetry across c1 and explain the mid-stance deficit.',
    refs: ['c1', 'c2'],
    answer: {
      text: [
        'Across <b>14 strides</b> in <code>trial_1_force.csv</code>, the left limb peaks at <b class="num">48.2 N</b> vs. right at <b class="num">46.7 N</b> — an asymmetry index of <b class="num">3.2%</b>.',
        'The paired-t in c2 confirms the gap is real: <b>t(13) = 3.27, p = .006, d = 0.87</b> (large effect). Most of the Δ sits in <b>mid-stance (30–55% GC)</b> where the R-side loses ≈8N of drive.',
        'Interpretation: <b>late stance-phase propulsion deficit on the right</b>, consistent with a weakened gastrocnemius or delayed heel-off. Recommend overlaying the desired trajectory from the prescription file.',
      ],
      spawns: [
        { label: '+ Graph: isolate 30–55% GC', action: 'graph:force:zoom' },
        { label: '+ Stat: ANOVA across 5 trials', action: 'stat:anova' },
      ],
    },
  },
];
