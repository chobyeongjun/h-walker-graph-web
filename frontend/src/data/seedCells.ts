// Clean slate — no seed cells. Cells appear only after a real CSV upload
// (auto-applied via canonical recipes) or via the LLM tool_use flow.
import type { Cell } from '../store/page';

export const SEED_CELLS: Cell[] = [];
