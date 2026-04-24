import { useEffect, useMemo, useRef, useState } from 'react';
import type { Cell } from '../../store/page';
import { usePage } from '../../store/page';
import { GRAPH_TPLS, type GraphTemplate } from '../../data/graphTemplates';
import { JOURNAL_PRESETS } from '../../data/journalPresets';
import { renderGraph, codegenGraph, feedbackPositive, feedbackCorrection } from '../../api';

const GRAPH_GROUPS = [
  { label: 'Force / Kinetic', keys: ['force_lr_subplot', 'force_avg', 'asymmetry', 'peak_box', 'force_tracking'] },
  { label: 'Kinematics',      keys: ['kinematics_ensemble'] },
  { label: 'Spatiotemporal',  keys: ['spatiotemporal_bar', 'stride_time_trend', 'stance_swing_bar'] },
  { label: 'Stability',       keys: ['mos_trajectory'] },
];

interface Props { cell: Cell; }

export default function GraphCell({ cell }: Props) {
  const globalPreset = usePage((s) => s.globalPreset);
  const updateCell = usePage((s) => s.updateCell);
  const showToast = usePage((s) => s.showToast);
  const runPreview = usePage((s) => s.runPreview);
  const allDatasets = usePage((s) => s.datasets);
  const [menuOpen, setMenuOpen] = useState(false);
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [svgInline, setSvgInline] = useState<string | null>(null);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiOpen, setAiOpen] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackReason, setFeedbackReason] = useState('');
  const aiInputRef = useRef<HTMLInputElement>(null);

  const activeKey =
    cell.strideAvg && cell.graph === 'force_lr_subplot' && GRAPH_TPLS.force_avg ? 'force_avg' : cell.graph;
  const tpl = GRAPH_TPLS[activeKey || 'force_lr_subplot'];
  const preset = globalPreset;
  const P = JOURNAL_PRESETS[preset];
  const canToggleAvg = cell.graph === 'force_lr_subplot' || cell.graph === 'force_avg';
  const palette = P?.paletteColor?.length ? P.paletteColor : P?.palette || [];
  const hasDataset = !!cell.dsIds[0];
  const side = cell.side || 'both';
  // Templates where L/R toggle doesn't apply
  const NO_LR_TEMPLATES = new Set(['asymmetry', 'spatiotemporal_bar', 'stride_time_trend', 'stance_swing_bar', 'force_tracking', 'mos_trajectory']);
  const canToggleSide = !NO_LR_TEMPLATES.has(cell.graph || '');

  // Auto-trigger backend preview when dataset is bound and no preview exists yet.
  useEffect(() => {
    if (hasDataset && !cell.previewBlobUrl && !cell.loading && !cell.error) {
      runPreview(cell.id);
    }
  }, [hasDataset, cell.previewBlobUrl, cell.loading, cell.error, cell.id, runPreview]);

  // Re-run when the graph template, global preset, strideAvg, title,
  // side filter, or the multi-dataset overlay series list changes.
  useEffect(() => {
    if (!hasDataset) return;
    const h = setTimeout(() => { runPreview(cell.id); }, 180);
    return () => clearTimeout(h);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cell.graph, cell.strideAvg, cell.title, globalPreset, cell.side,
      JSON.stringify(cell.series)]);

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
      const hasSeries = cell.series && cell.series.length >= 2;
      const blob = await renderGraph({
        template: activeKey || 'force_lr_subplot',
        preset,
        variant,
        format: fmt,
        stride_avg: !!cell.strideAvg,
        ...(hasSeries
          ? { datasets: cell.series.map((s) => ({ id: s.dsId, label: s.label, color: s.color })) }
          : { dataset_id: cell.dsIds[0] }),
        title: cell.title || '',
        side,
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

  async function runCodegen() {
    if (!cell.dsIds[0] || !aiPrompt.trim() || aiBusy) return;
    setAiBusy(true);
    try {
      const blob = await codegenGraph({
        dataset_id: cell.dsIds[0],
        prompt: aiPrompt.trim(),
        preset,
        variant: 'col2',
        format: 'svg',
      });
      const url = URL.createObjectURL(blob);
      updateCell(cell.id, { previewBlobUrl: url, error: undefined });
      setAiOpen(false);
      setAiPrompt('');
      showToast('AI 그래프 생성 완료');
    } catch (e) {
      showToast(`AI 그래프 실패: ${(e as Error).message}`);
    } finally {
      setAiBusy(false);
    }
  }

  function sendFeedbackGood() {
    feedbackPositive(
      `graph:${activeKey} dataset:${cell.dsIds[0]}`,
      { graph: activeKey, preset, title: cell.title },
    );
    showToast('👍 피드백 저장됨');
  }

  async function sendFeedbackBad() {
    if (!feedbackReason.trim()) { setFeedbackOpen(true); return; }
    await feedbackCorrection(
      `graph:${activeKey} dataset:${cell.dsIds[0]}`,
      { graph: activeKey, preset, title: cell.title },
      feedbackReason.trim(),
    );
    setFeedbackOpen(false);
    setFeedbackReason('');
    showToast('👎 피드백 저장됨');
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
            {GRAPH_GROUPS.map((g) => (
              <optgroup key={g.label} label={g.label}>
                {g.keys.filter((k) => k in GRAPH_TPLS).map((k) => (
                  <option key={k} value={k}>{GRAPH_TPLS[k].ey}</option>
                ))}
              </optgroup>
            ))}
          </select>
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
        {canToggleSide && (
          <div className="gt-side-toggle">
            {(['L', 'both', 'R'] as const).map((s) => (
              <button
                key={s}
                className={`gt-side-btn${side === s ? ' active' : ''}`}
                onClick={() => updateCell(cell.id, { side: s })}
                title={s === 'both' ? 'Both limbs' : `${s === 'L' ? 'Left' : 'Right'} only`}
              >
                {s === 'both' ? 'L+R' : s}
              </button>
            ))}
          </div>
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
        {hasDataset && allDatasets.length > 1 && (
          <div style={{ position: 'relative' }}>
            <button
              className="gt-btn"
              title="Add another dataset as an overlay"
              onClick={() => setOverlayOpen((v) => !v)}
            >
              + Overlay ({(cell.series?.length || cell.dsIds.length) || 1})
            </button>
            {overlayOpen && (
              <div className="gt-menu" onMouseLeave={() => setOverlayOpen(false)}
                   style={{ minWidth: 240, padding: '6px' }}>
                <div style={{ padding: '4px 8px', font: '600 9px/1 JetBrains Mono, monospace',
                              color: '#6B7280', letterSpacing: '.18em', textTransform: 'uppercase' }}>
                  Datasets in this plot
                </div>
                {allDatasets.map((d) => {
                  const active = (cell.series || cell.dsIds.map((id) => ({ dsId: id })))
                    .some((s) => ('dsId' in s ? s.dsId : s) === d.id);
                  return (
                    <label key={d.id} className="gt-mitem"
                           style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => {
                          const cur: Array<{ dsId: string; label?: string; color?: string }> =
                            cell.series && cell.series.length
                              ? [...cell.series]
                              : cell.dsIds.map((id) => ({ dsId: id }));
                          const idx = cur.findIndex((s) => s.dsId === d.id);
                          if (idx >= 0) cur.splice(idx, 1);
                          else cur.push({ dsId: d.id, label: d.name });
                          updateCell(cell.id, {
                            series: cur,
                            dsIds: cur.map((s) => s.dsId),
                          });
                        }}
                      />
                      <span className={`tag ${d.tag}`} style={{ padding: '1px 5px', fontSize: 9 }}>{d.tag}</span>
                      <span style={{ fontSize: 11, color: '#E2E8F0', flex: 1 }}>{d.name}</span>
                    </label>
                  );
                })}
                <div style={{ padding: '6px 8px 2px', font: '500 9.5px/1.3 Pretendard,sans-serif',
                              color: '#6B7280', borderTop: '1px solid rgba(255,255,255,.06)', marginTop: 4 }}>
                  {(cell.series?.length || cell.dsIds.length) >= 2
                    ? 'Overlay mode · one colored line per dataset'
                    : 'Add ≥ 2 datasets to overlay them on the same figure'}
                </div>
              </div>
            )}
          </div>
        )}
        <span className="gt-meta">
          {P?.name} · {P?.col2.w}mm · {P?.dpi}dpi · {P?.sizes.body}pt {P?.font}
        </span>
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

      {/* Figure caption — prominent, journal-style, above the plot.
          Empty value means no in-plot title in the exported file either. */}
      <div className="fig-caption">
        <span className="fig-cap-prefix">Figure</span>
        <input
          className="fig-cap-input"
          value={cell.title || ''}
          placeholder="논문 캡션 — 이 그림이 뭘 보여주는지 한 줄로 (비워두면 figure 내부 제목 없음)"
          onChange={(e) => updateCell(cell.id, { title: e.target.value })}
        />
      </div>

      <div
        className={`plot preset-pub${cell.loading ? ' plot-loading' : ''}`}
        style={{
          ['--pub-font' as never]: `'${P?.font}', ${P?.fontFallback}`,
          ['--pub-stroke' as never]: `${P?.stroke}`,
          ['--pub-grid' as never]: `${P?.gridColor}`,
          ['--pub-axis-pt' as never]: `${P?.sizes.axis}`,
          ['--pub-body-pt' as never]: `${P?.sizes.body}`,
        } as React.CSSProperties}
      >
        {cell.error ? (
          <div className="plot-error">
            <b>Render failed</b>
            <div>{cell.error}</div>
            <button onClick={() => runPreview(cell.id)}>Retry</button>
          </div>
        ) : hasDataset && svgInline ? (
          <div className="plot-real" dangerouslySetInnerHTML={{ __html: svgInline }} />
        ) : hasDataset && cell.loading ? (
          <div className="plot-skeleton">
            <div className="ps-bar" /><div className="ps-bar" /><div className="ps-bar" />
            <div className="ps-label">Rendering…</div>
          </div>
        ) : (
          <PlotSvg id={`plot-${cell.id}`} tpl={tpl} palette={palette} />
        )}
        <div className="pub-rule-ruler">
          {P?.name} · {P?.col2.w}mm · {P?.font} {P?.sizes.body}pt · {P?.dpi}dpi
        </div>
      </div>

      <div className="cell-legend">
        {tpl.paths?.map((p, i) => {
          const c = palette.length ? palette[i % palette.length] : p.c;
          return (
            <span key={i} className="lg-item">
              <span className={`lg-sw${p.dash ? ' dash' : ''}`} style={{ background: c, color: c }} />
              {p.label}
            </span>
          );
        })}
      </div>

      <div className="cell-meta">
        {hasDataset && cell.previewBlobUrl && (
          <span style={{ color: '#00FFB2' }}>● live</span>
        )}
        {tpl.summary.map(([k, v], i) => (
          <span key={i}>{k} <b>{v}</b></span>
        ))}
      </div>

      {/* AI codegen + feedback row */}
      <div className="cell-ai-row">
        {hasDataset && (
          <button
            className="gt-btn ai-ask-btn"
            title="AI에게 이 데이터로 그래프 그려달라고 요청"
            onClick={() => { setAiOpen((v) => !v); setTimeout(() => aiInputRef.current?.focus(), 50); }}
          >
            ✦ Ask AI
          </button>
        )}
        <div style={{ flex: 1 }} />
        {hasDataset && cell.previewBlobUrl && (
          <>
            <button className="gt-btn fb-btn" title="이 그래프 유용함" onClick={sendFeedbackGood}>👍</button>
            <button
              className="gt-btn fb-btn"
              title="이 그래프 문제 있음"
              onClick={() => setFeedbackOpen((v) => !v)}
            >👎</button>
          </>
        )}
      </div>

      {/* AI prompt input */}
      {aiOpen && hasDataset && (
        <div className="cell-ai-input">
          <input
            ref={aiInputRef}
            className="ai-prompt-input"
            placeholder="예: L 힘 추종 오차를 stride별로 그려줘 / Plot R_Pitch over gait cycle"
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') runCodegen(); if (e.key === 'Escape') setAiOpen(false); }}
            disabled={aiBusy}
          />
          <button className="gt-btn" onClick={runCodegen} disabled={aiBusy || !aiPrompt.trim()}>
            {aiBusy ? '…' : 'Run'}
          </button>
        </div>
      )}

      {/* 👎 reason input */}
      {feedbackOpen && (
        <div className="cell-ai-input">
          <input
            className="ai-prompt-input"
            placeholder="무엇이 문제였나요? (예: L/R 반전됨, 스케일 이상, 원하는 컬럼 아님)"
            value={feedbackReason}
            onChange={(e) => setFeedbackReason(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendFeedbackBad(); if (e.key === 'Escape') setFeedbackOpen(false); }}
          />
          <button className="gt-btn" onClick={sendFeedbackBad} disabled={!feedbackReason.trim()}>
            Send
          </button>
        </div>
      )}
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
