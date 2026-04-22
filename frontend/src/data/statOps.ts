// Ported from core_v3.html :1205-1236 (STAT_OPS)
// The run() functions return deterministic mock results; real impl will be server-side.

export interface StatResult {
  test: string;
  n?: number;
  n1?: number;
  n2?: number;
  k?: number;
  t?: string;
  F?: string;
  r?: string;
  df?: number | string;
  df1?: number;
  df2?: number;
  p: string;
  psig: boolean;
  mean_diff?: string;
  ci95?: string;
  cohen_d?: string;
  eta2?: string;
  effect?: string;
  posthoc?: string;
}

export interface StatOp {
  label: string;
  needs: number;
  run: (inputs: { a: string; b: string }) => StatResult;
}

export const STAT_OPS: Record<string, StatOp> = {
  ttest_paired: {
    label: 'Paired t-test', needs: 2,
    run: ({ a, b }) => {
      const seed = (a + b).length;
      return {
        test: 'Paired t-test (two-tailed)',
        n: 14,
        t: (3.27 + (seed % 4) * 0.08).toFixed(2),
        df: 13,
        p: '0.006',
        psig: true,
        mean_diff: '+4.82 N',
        ci95: '[1.62, 8.02]',
        cohen_d: '0.87',
        effect: 'large',
      };
    },
  },
  ttest_welch: {
    label: 'Welch t-test', needs: 2,
    run: () => ({
      test: 'Welch t-test (two-tailed)', n1: 14, n2: 14, t: '2.94', df: '25.8',
      p: '0.007', psig: true, mean_diff: '+4.6 N', ci95: '[1.3, 7.9]',
      cohen_d: '0.79', effect: 'medium-large',
    }),
  },
  anova: {
    label: 'One-way ANOVA', needs: 3,
    run: () => ({
      test: 'One-way ANOVA', k: 3, n: 42, F: '5.14', df1: 2, df2: 39,
      p: '0.011', psig: true, eta2: '0.208', effect: 'large',
      posthoc: 'Tukey HSD: T1<T5 (p=.008), T2<T5 (p=.024)',
    }),
  },
  corr: {
    label: 'Pearson correlation', needs: 2,
    run: () => ({
      test: 'Pearson correlation', n: 140, r: '0.72', p: '<0.001',
      psig: true, ci95: '[0.62, 0.80]', effect: 'strong positive',
    }),
  },
  cohen: {
    label: "Cohen's d", needs: 2,
    run: () => ({
      test: "Cohen's d (independent)", n1: 14, n2: 14, cohen_d: '0.87',
      ci95: '[0.09, 1.64]', effect: 'large', mean_diff: '+4.82 N', p: '-', psig: false,
    }),
  },
};
