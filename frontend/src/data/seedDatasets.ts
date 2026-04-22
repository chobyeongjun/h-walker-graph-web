// Ported from core_v3.html :1063-1097 (DATASETS seed)
import type { Dataset } from '../store/workspace';

export const SEED_DATASETS: Dataset[] = [
  {
    id: 'ds1', name: 'trial_1_force.csv', tag: 'force', kind: 'force',
    rows: 2400, dur: '24.0s', hz: '100Hz',
    cols: [
      { name: 'time_s',  unit: 's',  mapped: 'time' },
      { name: 'L_force', unit: 'N',  mapped: 'L force' },
      { name: 'R_force', unit: 'N',  mapped: 'R force' },
      { name: 'L_cop',   unit: 'mm', mapped: '—' },
      { name: 'R_cop',   unit: 'mm', mapped: '—' },
    ],
    active: true,
    recipeState: {},
  },
  {
    id: 'ds2', name: 'trial_2_imu.csv', tag: 'imu', kind: 'imu',
    rows: 800, dur: '8.0s', hz: '100Hz',
    cols: [
      { name: 't',           unit: 's', mapped: 'time' },
      { name: 'shank_pitch', unit: '°', mapped: 'shank' },
      { name: 'thigh_pitch', unit: '°', mapped: 'thigh' },
      { name: 'shank_roll',  unit: '°', mapped: '—' },
    ],
    active: false,
    recipeState: {},
  },
  {
    id: 'ds3', name: 'pilot_run.csv', tag: 'mix', kind: 'trials',
    rows: 5000, dur: '50.0s · 5 trials', hz: '100Hz',
    cols: [
      { name: 'time',     unit: 's',   mapped: 'time' },
      { name: 'trial_id', unit: '—',   mapped: 'group' },
      { name: 'force',    unit: 'N·n', mapped: 'force' },
    ],
    active: false,
    recipeState: {},
  },
];
