import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { usePage } from '../store/page';
import { GRAPH_TPLS } from '../data/graphTemplates';

export default function FocusOverlay() {
  const id = usePage((s) => s.focusCellId);
  const cells = usePage((s) => s.cells);
  const close = () => usePage.getState().focusCell(null);

  if (!id) return null;
  const graphCells = cells.filter((c) => c.type === 'graph');
  const idx = graphCells.findIndex((c) => c.id === id);
  const cell = graphCells[idx];
  if (!cell) return null;
  const tpl = GRAPH_TPLS[cell.graph || 'force'];

  return (
    <div className="focus-wrap open" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="focus">
        <header className="focus-head">
          <div>
            <div className="focus-ey">Focus</div>
            <div className="focus-title">{tpl.title}</div>
            <div className="focus-sub">{tpl.ey}</div>
          </div>
          <div className="focus-nav">
            <button disabled={idx <= 0} onClick={() => usePage.getState().focusCell(graphCells[idx - 1]?.id || null)}>
              <ChevronLeft size={14} />
            </button>
            <span className="count">{idx + 1} / {graphCells.length}</span>
            <button disabled={idx >= graphCells.length - 1} onClick={() => usePage.getState().focusCell(graphCells[idx + 1]?.id || null)}>
              <ChevronRight size={14} />
            </button>
            <button onClick={close}><X size={14} /></button>
          </div>
        </header>
        <div className="focus-body">
          <div className="focus-plot-wrap">
            <svg viewBox="0 0 456 210" preserveAspectRatio="none">
              {tpl.yTicks.map((_, i) => (
                <line key={'gy' + i} className="grid-line" x1={44} x2={448} y1={23 + i * 40} y2={23 + i * 40} />
              ))}
              <line className="axis-line" x1={44} x2={448} y1={182} y2={182} />
              <line className="axis-line" x1={44} x2={44} y1={20} y2={182} />
              <text x={228} y={108} textAnchor="middle"
                    style={{ fill: '#6B7280', fontSize: 11 }}>
                · open the cell to view the rendered figure ·
              </text>
            </svg>
          </div>
          <aside className="focus-side">
            <div className="fs-block">
              <h5>Axes</h5>
              <div className="fs-stat"><span>x</span><b>{tpl.xUnit || '—'}</b></div>
              <div className="fs-stat"><span>y</span><b>{tpl.yUnit || '—'}</b></div>
            </div>
          </aside>
        </div>
        <footer className="focus-foot">
          <span style={{ color: '#6B7280', fontSize: 11 }}>
            Per-sync zoom inspector arrives next.
          </span>
        </footer>
      </div>
    </div>
  );
}
