// Ported verbatim from core_v3.html :1054-1058
export const COLORS = {
  lActual: '#3B82C4', lDesired: '#7FB5E4',
  rActual: '#D35454', rDesired: '#E89B9B',
  accent: '#F09708', mint: '#00FFB2', violet: '#A78BFA',
} as const;

export type ColorKey = keyof typeof COLORS;
