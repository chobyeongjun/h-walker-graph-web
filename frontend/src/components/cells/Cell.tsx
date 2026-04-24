import type { Cell as CellModel } from '../../store/page';
import GraphCell from './GraphCell';
import StatCell from './StatCell';
import ComputeCell from './ComputeCell';
import InspectorCell from './InspectorCell';
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
  const displayTitle = cell.title
    ?? (cell.type === 'graph' ? `Graph · ${cell.graph}`
      : cell.type === 'stat' ? `Stat · ${cell.op}`
      : cell.type === 'compute' ? `Compute · ${cell.metric}`
      : cell.type === 'inspector' ? 'Inspector · raw signal'
      : 'Cell');

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
            : cell.type === 'inspector' ? 'INSPECT'
            : 'CELL'}
        </span>
        <span
          className="cell-title"
          contentEditable
          suppressContentEditableWarning
          onBlur={(e) => update(cell.id, { title: e.currentTarget.textContent || '' })}
        >{displayTitle}</span>
        {cell.dsIds.slice(0, 2).map((dsId) => (
          <span key={dsId} className="ds-chip">{dsId}</span>
        ))}
        <div className="cell-tools">
          {cell.type === 'graph' && (
            <button className="cell-tool" title="Focus" onClick={() => focusCell(cell.id)}>
              <Expand size={14} />
            </button>
          )}
          <button className="cell-tool" title="Duplicate" onClick={() => dup(cell.id)}>
            <Copy size={14} />
          </button>
          <button className="cell-tool danger" title="Delete" onClick={() => remove(cell.id)}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {cell.type === 'graph' && <GraphCell cell={cell} />}
      {cell.type === 'stat' && <StatCell cell={cell} />}
      {cell.type === 'compute' && <ComputeCell cell={cell} />}
      {cell.type === 'inspector' && <InspectorCell cell={cell} />}
      {/* `llm` cell type is deprecated — Haiku integration was removed
          per user directive ("haiku 없애고 클릭으로"). Old persisted
          cells of this type are silently ignored and removable via
          the trash icon. */}
    </div>
  );
}
