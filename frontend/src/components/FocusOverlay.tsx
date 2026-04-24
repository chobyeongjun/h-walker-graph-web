import { useEffect, useState } from 'react';
import { X, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { usePage } from '../store/page';
import { GRAPH_TPLS } from '../data/graphTemplates';

export default function FocusOverlay() {
  const id = usePage((s) => s.focusCellId);
  const cells = usePage((s) => s.cells);
  const datasets = usePage((s) => s.datasets);
  const runPreview = usePage((s) => s.runPreview);
  const close = () => usePage.getState().focusCell(null);
  const [svgInline, setSvgInline] = useState<string | null>(null);

  const graphCells = cells.filter((c) => c.type === 'graph');
  const idx = graphCells.findIndex((c) => c.id === id);
  const cell = graphCells[idx];

  // Inline the rendered SVG blob so the focus view shows exactly what the
  // card shows — same real data, same preset, same palette.
  useEffect(() => {
    if (!cell?.previewBlobUrl) { setSvgInline(null); return; }
    let cancelled = false;
    fetch(cell.previewBlobUrl)
      .then((r) => r.text())
      .then((txt) => { if (!cancelled) setSvgInline(txt); })
      .catch(() => { if (!cancelled) setSvgInline(null); });
    return () => { cancelled = true; };
  }, [cell?.previewBlobUrl]);

  // Auto-render on open if we have a dataset bound but no preview yet.
  useEffect(() => {
    if (!cell) return;
    const hasDs = !!cell.dsIds[0];
    if (hasDs && !cell.previewBlobUrl && !cell.loading && !cell.error) {
      runPreview(cell.id);
    }
  }, [cell?.id, cell?.previewBlobUrl, cell?.loading, cell?.error, runPreview]);

  if (!id || !cell) return null;
  const tpl = GRAPH_TPLS[cell.graph || 'force'];
  const hasDs = !!cell.dsIds[0];
  const ds = hasDs ? datasets.find((d) => d.id === cell.dsIds[0]) : null;

  return (
    <div className="focus-wrap open" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="focus">
        <header className="focus-head">
          <div>
            <div className="focus-ey">Focus</div>
            <div className="focus-title">{cell.title || tpl.title}</div>
            <div className="focus-sub">
              {tpl.ey}
              {ds ? ` · ${ds.name}` : ' · no dataset bound'}
            </div>
          </div>
          <div className="focus-nav">
            <button
              title="Re-render"
              disabled={!hasDs || !!cell.loading}
              onClick={() => runPreview(cell.id)}
            >
              <RefreshCw size={18} />
            </button>
            <button disabled={idx <= 0} onClick={() => usePage.getState().focusCell(graphCells[idx - 1]?.id || null)}>
              <ChevronLeft size={18} />
            </button>
            <span className="count">{idx + 1} / {graphCells.length}</span>
            <button disabled={idx >= graphCells.length - 1} onClick={() => usePage.getState().focusCell(graphCells[idx + 1]?.id || null)}>
              <ChevronRight size={18} />
            </button>
            <button onClick={close}><X size={18} /></button>
          </div>
        </header>
        <div className="focus-body">
          <div className="focus-plot-wrap">
            {cell.error ? (
              <div className="plot-error" style={{ padding: 40, textAlign: 'center' }}>
                <b>Render failed</b>
                <div style={{ marginTop: 8, color: '#f87171' }}>{cell.error}</div>
                <button
                  style={{ marginTop: 12 }}
                  onClick={() => runPreview(cell.id)}
                >Retry</button>
              </div>
            ) : !hasDs ? (
              <div className="plot-error" style={{ padding: 40, textAlign: 'center', color: '#9CA3AF' }}>
                <b>No dataset bound</b>
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  Drag a CSV onto the workspace or bind this cell to an uploaded dataset
                  to see the real figure here. Showing template preview only.
                </div>
                <svg viewBox="0 0 456 210" preserveAspectRatio="none" style={{ marginTop: 16, opacity: 0.6 }}>
                  {tpl.yTicks.map((_, i) => (
                    <line key={'gy' + i} className="grid-line" x1={44} x2={448} y1={23 + i * 40} y2={23 + i * 40} />
                  ))}
                  <line className="axis-line" x1={44} x2={448} y1={182} y2={182} />
                  <line className="axis-line" x1={44} x2={44} y1={20} y2={182} />
                  {tpl.paths?.map((p, i) => (
                    <path key={i} d={p.d} stroke={p.c} strokeWidth={p.w} strokeDasharray={p.dash} fill="none" strokeLinecap="round" />
                  ))}
                </svg>
              </div>
            ) : cell.loading || !svgInline ? (
              <div className="plot-skeleton" style={{ height: '60vh' }}>
                <div className="ps-bar" /><div className="ps-bar" /><div className="ps-bar" />
                <div className="ps-label">Rendering real data…</div>
              </div>
            ) : (
              <div
                className="focus-svg plot preset-pub"
                dangerouslySetInnerHTML={{ __html: svgInline }}
              />
            )}
          </div>
          <aside className="focus-side">
            <div className="fs-block">
              <h5>Dataset</h5>
              {ds ? (
                <>
                  <div className="fs-stat"><span>name</span><b>{ds.name}</b></div>
                  <div className="fs-stat"><span>kind</span><b>{ds.kind}</b></div>
                  <div className="fs-stat"><span>rows</span><b>{ds.rows.toLocaleString()}</b></div>
                  {ds.subject_id && <div className="fs-stat"><span>subject</span><b>{ds.subject_id}</b></div>}
                  {ds.condition && <div className="fs-stat"><span>condition</span><b>{ds.condition}</b></div>}
                </>
              ) : (
                <div className="fs-stat"><span>—</span><b>no binding</b></div>
              )}
            </div>
            <div className="fs-block">
              <h5>Summary (template)</h5>
              {tpl.summary.map(([k, v], i) => (
                <div key={i} className="fs-stat"><span>{k}</span><b>{v}</b></div>
              ))}
            </div>
            <div className="fs-block">
              <h5>Series</h5>
              {tpl.paths?.map((p, i) => (
                <div key={i} className="fs-series">
                  <span className="tog" style={{ background: p.c }} />
                  <span>{p.label}</span>
                  <span className="val">{p.dash ? 'dashed' : 'solid'}</span>
                </div>
              ))}
            </div>
          </aside>
        </div>
        <footer className="focus-foot">
          <span style={{ color: '#6B7280', fontSize: 11 }}>
            {hasDs
              ? 'Focus shows the live render — same data/preset as the card'
              : 'Bind a dataset to see the real rendered figure'}
          </span>
        </footer>
      </div>
    </div>
  );
}
