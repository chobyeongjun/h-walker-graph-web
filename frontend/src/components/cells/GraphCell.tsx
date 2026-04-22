import { useEffect, useMemo, useState } from 'react';
import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';
import { GRAPH_TPLS, type GraphTemplate } from '../../data/graphTemplates';
import { JOURNAL_PRESETS } from '../../data/journalPresets';
import { renderGraph } from '../../api';

interface Props { cell: Cell; }

export default function GraphCell({ cell }: Props) {
  const globalPreset = useWorkspace((s) => s.globalPreset);
  const mode = useWorkspace((s) => s.mode);
  const updateCell = useWorkspace((s) => s.updateCell);
  const showToast = useWorkspace((s) => s.showToast);
  const runPreview = useWorkspace((s) => s.runPreview);
  const [menuOpen, setMenuOpen] = useState(false);
  const [svgInline, setSvgInline] = useState<string | null>(null);

  const activeKey =
    cell.strideAvg && cell.graph === 'force' && GRAPH_TPLS.force_avg ? 'force_avg' : cell.graph;
  const tpl = GRAPH_TPLS[activeKey || 'force'];
  const preset = cell.preset || globalPreset;
  const P = JOURNAL_PRESETS[preset];
  const isOverride = !!cell.preset;
  const canToggleAvg = cell.graph === 'force' || cell.graph === 'force_avg';
  const pubActive = mode === 'pub' || isOverride;
  const palette = P?.paletteColor?.length ? P.paletteColor : P?.palette || [];
  const hasDataset = !!cell.dsIds[0];

  // Auto-trigger backend preview when dataset is bound and no preview exists yet.
  useEffect(() => {
    if (hasDataset && !cell.previewBlobUrl && !cell.loading && !cell.error) {
      runPreview(cell.id);
    }
  }, [hasDataset, cell.previewBlobUrl, cell.loading, cell.error, cell.id, runPreview]);

  // Re-run when the graph template, preset, or strideAvg changes (debounced via effect).
  useEffect(() => {
    if (!hasDataset) return;
    const h = setTimeout(() => { runPreview(cell.id); }, 180);
    return () => clearTimeout(h);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cell.graph, cell.preset, cell.strideAvg]);

  // Fetch inline SVG text when blob URL changes — so we can adapt viewport to plot box.
  useEffect(() => {
    if (!cell.previewBlobUrl) { setSvgInline(null); return; }
    let cancelled = false;
    fetch(cell.previewBlobUrl)
      .then((r) => r.text())
      .then((txt) => { if (!cancelled) setSvgInline(txt); })
      .catch(() => { if (!cancelled) setSvgInline(null); });
    return () => { cancelled = true; };
  }, [cell.previewBlobUrl]);

  async function backendRender(fmt: 'svg' | 'pdf' | 'png' | 'eps' | 'tiff', variant: 'col1' | 'col2' | 'onehalf' = 'col2') {
    try {
      const blob = await renderGraph({
        template: activeKey || 'force',
        preset,
        variant,
        format: fmt,
        stride_avg: !!cell.strideAvg,
        dataset_id: cell.dsIds[0],
      });
      const w = variant === 'col1' ? P?.col1.w : (variant === 'onehalf' ? P?.onehalf?.w ?? P?.col2.w : P?.col2.w);
      downloadBlob(blob, `${cell.id}_${activeKey}_${preset}_${Math.round(w || 0)}mm.${fmt}`);
      showToast(`${fmt.toUpperCase()} · ${preset} · ${Math.round(w || 0)}mm`);
    } catch (e) {
      showToast(`Export failed: ${(e as Error).message}`);
    }
  }

  function exportSvgClient() {
    const svgEl = document.getElementById(`plot-${cell.id}`);
    if (!svgEl) return;
    const xml = new XMLSerializer().serializeToString(svgEl);
    downloadBlob(new Blob([xml], { type: 'image/svg+xml' }), `${cell.id}_preview.svg`);
  }

  return (
    <>
      <div className="graph-toolbar">
        <div className="gt-field">
          <span className="gt-lbl">Graph</span>
          <select
            className="gt-sel"
            value={cell.graph || ''}
            onChange={(e) => updateCell(cell.id, { graph: e.target.value })}
          >
            {Object.keys(GRAPH_TPLS).map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
        <div className="gt-field">
          <span className="gt-lbl">Journal</span>
          <select
            className="gt-sel"
            value={preset}
            data-overriden={isOverride}
            onChange={(e) => updateCell(cell.id, { preset: e.target.value })}
          >
            {Object.entries(JOURNAL_PRESETS).map(([k, v]) => (
              <option key={k} value={k}>{v.name}</option>
            ))}
          </select>
          {isOverride && <span className="gt-override">override</span>}
        </div>
        {canToggleAvg && (
          <label className="gt-toggle">
            <input
              type="checkbox"
              checked={!!cell.strideAvg}
              onChange={(e) => updateCell(cell.id, { strideAvg: e.target.checked })}
            />
            Stride avg (mean±SD)
          </label>
        )}
        <div className="gt-spacer" />
        {hasDataset && (
          <button
            className="gt-btn"
            title="Re-render from dataset"
            onClick={() => runPreview(cell.id)}
            disabled={!!cell.loading}
          >
            {cell.loading ? '…' : '⟳ Run'}
          </button>
        )}
        <span className="gt-meta">{P?.col2.w}mm · {P?.dpi} dpi · {P?.sizes.body}pt</span>
        <div className="gt-export">
          <button className="gt-btn" onClick={() => setMenuOpen((v) => !v)}>Export ▾</button>
          {menuOpen && (
            <div className="gt-menu" onMouseLeave={() => setMenuOpen(false)}>
              <div style={{ padding: '4px 10px', font: '600 8.5px/1 JetBrains Mono, monospace', color: '#6B7280', letterSpacing: '.14em' }}>
                {P?.name} · {Math.round(P?.col2.w || 0)}mm · {P?.dpi}dpi
              </div>
              <button className="gt-mitem" onClick={() => { backendRender('svg', 'col2'); setMenuOpen(false); }}>SVG · 2-col</button>
              <button className="gt-mitem" onClick={() => { backendRender('svg', 'col1'); setMenuOpen(false); }}>SVG · 1-col</button>
              <button className="gt-mitem" onClick={() => { backendRender('pdf', 'col2'); setMenuOpen(false); }}>PDF · 2-col</button>
              <button className="gt-mitem" onClick={() => { backendRender('png', 'col2'); setMenuOpen(false); }}>PNG · 2-col</button>
              <button className="gt-mitem" onClick={() => { backendRender('eps', 'col2'); setMenuOpen(false); }}>EPS · 2-col</button>
              <button className="gt-mitem" onClick={() => { backendRender('tiff', 'col2'); setMenuOpen(false); }}>TIFF · 2-col</button>
              <div style={{ padding: '4px 10px', borderTop: '1px solid rgba(255,255,255,.06)', marginTop: 2 }}>
                <button className="gt-mitem" onClick={() => { exportSvgClient(); setMenuOpen(false); }}>Preview SVG</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div
        className={`plot${pubActive ? ' preset-pub' : ''}${cell.loading ? ' plot-loading' : ''}`}
        style={pubActive ? ({
          ['--pub-font' as never]: `'${P?.font}', ${P?.fontFallback}`,
          ['--pub-stroke' as never]: `${P?.stroke}`,
          ['--pub-grid' as never]: `${P?.gridColor}`,
          ['--pub-axis-pt' as never]: `${P?.sizes.axis}`,
          ['--pub-body-pt' as never]: `${P?.sizes.body}`,
        } as React.CSSProperties) : undefined}
      >
        {cell.error ? (
          <div className="plot-error">
            <b>Render failed</b>
            <div>{cell.error}</div>
            <button onClick={() => runPreview(cell.id)}>Retry</button>
          </div>
        ) : hasDataset && svgInline ? (
          <div
            className="plot-real"
            dangerouslySetInnerHTML={{ __html: svgInline }}
          />
        ) : hasDataset && cell.loading ? (
          <div className="plot-skeleton">
            <div className="ps-bar" /><div className="ps-bar" /><div className="ps-bar" />
            <div className="ps-label">Rendering…</div>
          </div>
        ) : (
          <PlotSvg
            id={`plot-${cell.id}`}
            tpl={tpl}
            palette={pubActive ? palette : null}
          />
        )}
        {pubActive && (
          <div className="pub-rule-ruler">
            {P?.name} · {P?.col2.w}mm · {P?.font} {P?.sizes.body}pt · {P?.dpi}dpi
          </div>
        )}
      </div>

      <div className="cell-legend">
        {tpl.paths?.map((p, i) => {
          const c = pubActive && palette.length ? palette[i % palette.length] : p.c;
          return (
            <span key={i} className="lg-item" style={pubActive ? { color: '#111' } : undefined}>
              <span className={`lg-sw${p.dash ? ' dash' : ''}`} style={{ background: c, color: c }} />
              {p.label}
            </span>
          );
        })}
      </div>

      <div className="cell-meta">
        <span>{tpl.title}</span>
        {hasDataset && cell.previewBlobUrl && (
          <span style={{ color: '#00FFB2' }}>● live</span>
        )}
        {tpl.summary.map(([k, v], i) => (
          <span key={i}>{k} <b>{v}</b></span>
        ))}
      </div>
    </>
  );
}

function PlotSvg({ id, tpl, palette }: { id: string; tpl: GraphTemplate; palette: string[] | null }) {
  const vb = '0 0 456 210';
  const pick = (original: string, idx: number): string => {
    if (!palette || palette.length === 0) return original;
    return palette[idx % palette.length];
  };

  return useMemo(() => (
    <svg id={id} viewBox={vb} preserveAspectRatio="none">
      {tpl.yTicks.map((_, i) => (
        <line key={'gy' + i} className="grid-line" x1={44} x2={448} y1={23 + i * 40} y2={23 + i * 40} />
      ))}
      {tpl.xTicks.map((_, i) => (
        <line key={'gx' + i} className="grid-line" x1={48 + i * 90} x2={48 + i * 90} y1={20} y2={182} />
      ))}
      <line className="axis-line" x1={44} x2={448} y1={182} y2={182} />
      <line className="axis-line" x1={44} x2={44} y1={20} y2={182} />
      {tpl.bands?.map((b, i) => {
        const c = pick(b.c, i);
        return <path key={'b' + i} d={`${b.upper} L ${b.lower.replace(/M/g, 'L')} Z`} fill={c} opacity={b.opacity} />;
      })}
      {tpl.boxes?.map((b, i) => {
        const c = pick(b.c, i);
        return (
          <g key={'bx' + i}>
            <line x1={b.x} x2={b.x} y1={b.min} y2={b.max} stroke={c} strokeWidth={1.2} />
            <rect x={b.x - 18} y={b.q3} width={36} height={b.q1 - b.q3} fill={c} fillOpacity={0.25} stroke={c} strokeWidth={1} />
            <line x1={b.x - 18} x2={b.x + 18} y1={b.med} y2={b.med} stroke={c} strokeWidth={1.5} />
            <text className="tick-label" x={b.x} y={200} textAnchor="middle">{b.label}</text>
          </g>
        );
      })}
      {tpl.bars?.map((b, i) => (
        <rect key={'br' + i} x={b.x} y={180 - b.h} width={b.w} height={b.h} fill={pick(b.c, i)} />
      ))}
      {tpl.hlines?.map((h, i) => (
        <line key={'hl' + i} x1={44} x2={448} y1={h.y} y2={h.y} stroke={h.c} strokeDasharray={h.dash} strokeWidth={1} />
      ))}
      {tpl.paths?.map((p, i) => (
        <path
          key={'p' + i}
          d={p.d}
          stroke={pick(p.c, i)}
          strokeWidth={p.w}
          strokeDasharray={p.dash}
          fill="none"
          strokeLinecap="round"
        />
      ))}
      {tpl.yTicks.map((v, i) => (
        <text key={'ty' + i} className="tick-label" x={40} y={25 + i * 40} textAnchor="end">{v}</text>
      ))}
      {tpl.xTicks.map((v, i) => (
        <text key={'tx' + i} className="tick-label" x={48 + i * 90} y={196} textAnchor="middle">{v}</text>
      ))}
      <text className="axis-title" x={246} y={208} textAnchor="middle">{tpl.xUnit}</text>
      <text className="axis-title" x={14} y={100} textAnchor="middle" transform="rotate(-90 14,100)">{tpl.yUnit}</text>
    </svg>
  ), [id, tpl, palette]);
}

function downloadBlob(blob: Blob, name: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
