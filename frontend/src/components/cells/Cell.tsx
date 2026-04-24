import type { Cell as CellModel } from '../../store/page';
import GraphCell from './GraphCell';
import StatCell from './StatCell';
import ComputeCell from './ComputeCell';
import LlmCell from './LlmCell';
import { usePage } from '../../store/page';
import { Copy, Trash2, GripVertical, Expand } from 'lucide-react';

interface Props {
  cell: CellModel;
  index: number;
  /** Phase 4 · drag-and-drop listener bag from @dnd-kit; spread onto
   *  the grip icon so only the handle initiates reorder, not the whole
   *  cell body. */
  dragHandle?: Record<string, unknown>;
}

export default function Cell({ cell, index, dragHandle }: Props) {
  const remove = usePage((s) => s.removeCell);
  const dup = usePage((s) => s.duplicateCell);
  const update = usePage((s) => s.updateCell);
  const focusCell = usePage((s) => s.focusCell);

  const typeClass = `cell ${cell.type}`;
  // For graph cells, the card header is a derived label — editing the
  // figure caption lives inside GraphCell so we don't accidentally inject
  // "Shank IMU" etc. into the exported figure title. Non-graph cells keep
  // the editable title behavior.
  const autoLabel =
    cell.type === 'graph' ? `Graph · ${cell.graph}`
      : cell.type === 'stat' ? `Stat · ${cell.op}`
      : cell.type === 'compute' ? `Compute · ${cell.metric}`
      : 'Assistant';
  const headerEditable = cell.type !== 'graph';
  const displayTitle = (headerEditable && cell.title) ? cell.title : autoLabel;

  return (
    <div className={typeClass} id={`cell-${cell.id}`}>
      <div className="cell-head">
        <span className="cell-idx">#{index + 1}</span>
        <span
          className="cell-handle"
          style={{ cursor: dragHandle ? 'grab' : undefined }}
          {...(dragHandle || {})}
          title="Drag to reorder"
        ><GripVertical size={14} /></span>
        <span className="cell-ey">
          {cell.type === 'graph' ? 'GRAPH'
            : cell.type === 'stat' ? 'STATS'
            : cell.type === 'compute' ? 'COMPUTE'
            : 'ASSISTANT'}
        </span>
        <span
          className="cell-title"
          contentEditable={headerEditable}
          suppressContentEditableWarning
          onBlur={headerEditable
            ? (e) => update(cell.id, { title: e.currentTarget.textContent || '' })
            : undefined}
          title={headerEditable ? undefined : 'Edit the figure caption below the plot'}
        >{displayTitle}</span>
        {cell.dsIds.slice(0, 2).map((dsId) => (
          <span key={dsId} className="ds-chip">{dsId}</span>
        ))}
        <div className="cell-tools">
          {cell.type === 'graph' && (
            <button
              className="cell-tool primary"
              title="Open focus view (single-plot mode)"
              onClick={() => focusCell(cell.id)}
            >
              <Expand size={18} />
            </button>
          )}
          <button className="cell-tool" title="Duplicate" onClick={() => dup(cell.id)}>
            <Copy size={16} />
          </button>
          <button className="cell-tool danger" title="Delete" onClick={() => remove(cell.id)}>
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {cell.type === 'graph' && <GraphCell cell={cell} />}
      {cell.type === 'stat' && <StatCell cell={cell} />}
      {cell.type === 'compute' && <ComputeCell cell={cell} />}
      {cell.type === 'llm' && <LlmCell cell={cell} />}
    </div>
  );
}
