import type { Cell as CellModel } from '../../store/page';
import GraphCell from './GraphCell';
import StatCell from './StatCell';
import ComputeCell from './ComputeCell';
import LlmCell from './LlmCell';
import { usePage } from '../../store/page';
import { Copy, Trash2, GripVertical, Expand } from 'lucide-react';

const GRAPH_LABEL: Record<string, string> = {
  force:              '지면반력 (GRF)',
  force_avg:          '평균 GRF (mean±SD)',
  force_lr_subplot:   'L/R 지면반력 서브플롯',
  asymmetry:          '좌우 비대칭',
  peak_box:           '피크 박스플롯',
  cop:                '압력 중심 (COP)',
  trials:             'Trial 비교',
  cv_bar:             '변동 계수 (CV)',
  imu:                '관절 각도 시계열',
  imu_avg:            '관절 각도 평균±SD',
  cyclogram:          '사이클로그램',
  stride_time_trend:  '보폭 시간 추이',
  stance_swing_bar:   'Stance/Swing 비율',
  rom_bar:            '관절 가동 범위 (ROM)',
  symmetry_radar:     '대칭성 레이더',
  debug_ts:           '원시 시계열 (전체)',
  mocap_window:       'MoCap 구간 뷰',
};

const COMPUTE_LABEL_PREFIXES: Array<[string, string]> = [
  ['events:',   '이벤트 감지 · '],
  ['colstats:', '컬럼 통계 · '],
  ['mocap:',    'MoCap 구간 · '],
];

function resolveTitle(cell: CellModel): string {
  if (cell.title) return cell.title;
  if (cell.type === 'graph') {
    return GRAPH_LABEL[cell.graph || ''] ?? `그래프 · ${cell.graph}`;
  }
  if (cell.type === 'compute') {
    const m = cell.metric || '';
    for (const [prefix, label] of COMPUTE_LABEL_PREFIXES) {
      if (m.startsWith(prefix)) return label + m.slice(prefix.length);
    }
    return `Compute · ${m}`;
  }
  if (cell.type === 'stat') return `통계 · ${cell.op}`;
  return '어시스턴트';
}

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
  const displayTitle = resolveTitle(cell);

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
      {cell.type === 'llm' && <LlmCell cell={cell} />}
    </div>
  );
}
