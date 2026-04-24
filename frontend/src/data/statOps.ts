// Schema-only metadata for stat operations. Used for:
//   - LlmDock dispatch validation (`op in STAT_OPS`)
//   - the op picker in StatCell
// All numeric results come from /api/stats — no client-side mock results.
export interface StatOp {
  label: string;
  /** Number of input columns the op needs (1, 2, or ≥3). */
  needs: number;
}

export const STAT_OPS: Record<string, StatOp> = {
  ttest_paired: { label: 'Paired t-test',          needs: 2 },
  ttest_welch:  { label: "Welch t-test",           needs: 2 },
  anova1:       { label: 'One-way ANOVA',          needs: 3 },
  pearson:      { label: 'Pearson correlation',    needs: 2 },
  cohens_d:     { label: "Cohen's d",              needs: 2 },
  shapiro:      { label: 'Shapiro–Wilk normality', needs: 1 },
};
