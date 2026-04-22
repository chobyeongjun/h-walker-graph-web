// Clean slate — no seed datasets. The user starts with an empty workspace
// and an always-visible drop zone. Datasets appear only after real upload.
import type { Dataset } from '../store/workspace';

export const SEED_DATASETS: Dataset[] = [];
