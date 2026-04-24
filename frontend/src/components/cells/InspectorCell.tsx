import { useEffect, useMemo, useRef, useState } from 'react';
import type { Cell } from '../../store/page';
import { usePage } from '../../store/page';
import {
  listSyncs, fetchWindow,
  type SyncBoundary, type WindowResponse,
} from '../../api';
import { Search, ChevronLeft, ChevronRight, Maximize2 } from 'lucide-react';

interface Props { cell: Cell; }

/**
 * Per-sync zoom/pan inspector — MATLAB-style raw signal viewer.
 *
 * "sync = 1 cycle of the digital sync signal" (CLAUDE.md). The cell
 * fetches the dataset's sync cycle boundaries, lets the user step
 * through each cycle, and re-fetches a downsampled window on every
 * pan/zoom gesture. There is no client-side mock data — when no
 * dataset is bound, the cell shows an empty state.
 */
export default function InspectorCell({ cell }: Props) {
  const update = usePage((s) => s.updateCell);
  const datasets = usePage((s) => s.datasets);
  const showToast = usePage((s) => s.showToast);
  const dsId = cell.dsIds[0];
  const ds = datasets.find((d) => d.id === dsId);
  const colNames = useMemo(
    () => (ds?.cols || []).map((c) => c.name).filter((n) => n !== 'Sync'),
    [ds?.cols],
  );

  // Default channels: prefer raw force traces, then key IMU axes.
  const defaultChannels = useMemo(() => {
    const preferred = [
      'L_ActForce_N', 'R_ActForce_N',
      'L_Pitch', 'R_Pitch',
    ].filter((c) => colNames.includes(c));
    return preferred.length ? preferred : colNames.slice(0, 3);
  }, [colNames]);

  const channels = cell.inspectorChannels ?? defaultChannels;
  const syncIdx  = cell.inspectorSyncIdx ?? null;

  // ── Sync cycle list (fetched once per dataset) ───────────────────
  const [syncs, setSyncs] = useState<SyncBoundary[] | null>(null);
  const [tFull, setTFull] = useState<{ start: number; end: number } | null>(null);
  const [syncCol, setSyncCol] = useState<string | null>(null);
  useEffect(() => {
    if (!dsId) { setSyncs(null); setTFull(null); return; }
    let alive = true;
    listSyncs(dsId)
      .then((r) => {
        if (!alive) return;
        setSyncs(r.cycles);
        setSyncCol(r.column);
        const end = r.sample_rate_hz
          ? r.n_samples / r.sample_rate_hz
          : r.cycles.length ? r.cycles[r.cycles.length - 1].t_end : 0;
        setTFull({ start: 0, end });
      })
      .catch((e: Error) => {
        if (!alive) return;
        showToast(`Inspector: ${e.message}`);
      });
    return () => { alive = false; };
  }, [dsId, showToast]);

  // ── Viewport (the time window currently displayed) ──────────────
  const [viewport, setViewport] = useState<{ t0: number; t1: number } | null>(null);
  // When the user picks a sync index, snap viewport to that cycle's
  // bounds. -1 / null = full trial.
  useEffect(() => {
    if (!syncs || !tFull) return;
    if (syncIdx == null || syncIdx < 0) {
      setViewport({ t0: tFull.start, t1: tFull.end });
    } else {
      const c = syncs[Math.min(syncIdx, syncs.length - 1)];
      if (c) setViewport({ t0: c.t_start, t1: c.t_end });
    }
  }, [syncs, tFull, syncIdx]);

  // ── Window fetch (re-fires on viewport / channel change) ────────
  const [data, setData] = useState<WindowResponse | null>(null);
  const [fetching, setFetching] = useState(false);
  useEffect(() => {
    if (!dsId || !viewport || channels.length === 0) { setData(null); return; }
    let alive = true;
    setFetching(true);
    fetchWindow(dsId, {
      columns: channels,
      t_start: viewport.t0,
      t_end: viewport.t1,
      max_points: 4000,
    })
      .then((r) => { if (alive) { setData(r); setFetching(false); } })
      .catch((e: Error) => {
        if (!alive) return;
        setFetching(false);
        showToast(`Inspector window: ${e.message}`);
      });
    return () => { alive = false; };
  }, [dsId, viewport?.t0, viewport?.t1, channels.join(','), showToast]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Mouse zoom / pan ────────────────────────────────────────────
  const plotRef = useRef<SVGSVGElement | null>(null);
  function applyZoom(factor: number, anchorFraction: number) {
    if (!viewport) return;
    const span = viewport.t1 - viewport.t0;
    const anchor = viewport.t0 + span * anchorFraction;
    const newSpan = Math.max(span * factor, 0.005);
    const t0 = anchor - (anchor - viewport.t0) * (newSpan / span);
    const t1 = t0 + newSpan;
    if (tFull) {
      const clamped = clampViewport(t0, t1, tFull.start, tFull.end);
      setViewport(clamped);
    } else {
      setViewport({ t0, t1 });
    }
  }
  function onWheel(e: React.WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    if (!plotRef.current || !viewport) return;
    const rect = plotRef.current.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    const factor = e.deltaY > 0 ? 1.25 : 0.8;
    applyZoom(factor, Math.max(0, Math.min(1, fraction)));
  }
  const dragStateRef = useRef<{ x: number; t0: number; t1: number } | null>(null);
  function onMouseDown(e: React.MouseEvent<SVGSVGElement>) {
    if (!viewport) return;
    dragStateRef.current = { x: e.clientX, t0: viewport.t0, t1: viewport.t1 };
  }
  function onMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const drag = dragStateRef.current;
    if (!drag || !plotRef.current) return;
    const rect = plotRef.current.getBoundingClientRect();
    const dxFrac = (e.clientX - drag.x) / rect.width;
    const span = drag.t1 - drag.t0;
    const dt = -span * dxFrac;
    const t0 = drag.t0 + dt;
    const t1 = drag.t1 + dt;
    if (tFull) {
      setViewport(clampViewport(t0, t1, tFull.start, tFull.end));
    }
  }
  function onMouseUp() { dragStateRef.current = null; }

  // ── Channel toggle ──────────────────────────────────────────────
  function toggleChannel(name: string) {
    const next = channels.includes(name)
      ? channels.filter((c) => c !== name)
      : [...channels, name];
    update(cell.id, { inspectorChannels: next });
  }

  // ── Sync navigation ─────────────────────────────────────────────
  const totalSyncs = syncs?.length ?? 0;
  function goSync(i: number | null) {
    update(cell.id, { inspectorSyncIdx: i });
  }

  if (!dsId) {
    return (
      <div className="inspector-empty" style={{ padding: 24, textAlign: 'center', color: '#9CA3AF' }}>
        <Search size={20} style={{ opacity: 0.5, marginBottom: 6 }} />
        <div style={{ fontSize: 12 }}>Bind a CSV to inspect raw signals.</div>
        <div style={{ fontSize: 10, color: '#6B7280', marginTop: 4 }}>
          Drop a file or pick an existing dataset.
        </div>
      </div>
    );
  }

  return (
    <div className="inspector" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {/* Toolbar */}
      <div className="ins-bar" style={{
        display: 'flex', alignItems: 'center', gap: 6,
        fontSize: 11, color: '#E2E8F0',
      }}>
        <button
          onClick={() => goSync(syncIdx == null || syncIdx < 0 ? null : Math.max(0, syncIdx - 1))}
          disabled={syncIdx == null || syncIdx <= 0}
          title="Previous sync"
        >
          <ChevronLeft size={12} />
        </button>
        <span style={{ minWidth: 80, textAlign: 'center' }}>
          {syncIdx == null || syncIdx < 0
            ? 'Full trial'
            : `Sync ${syncIdx + 1} / ${totalSyncs || '?'}`}
        </span>
        <button
          onClick={() => goSync(syncIdx == null || syncIdx < 0 ? 0 : Math.min(totalSyncs - 1, syncIdx + 1))}
          disabled={!totalSyncs || (syncIdx != null && syncIdx >= totalSyncs - 1)}
          title="Next sync"
        >
          <ChevronRight size={12} />
        </button>
        <button onClick={() => goSync(null)} title="Reset to full trial">
          <Maximize2 size={11} />
        </button>
        <span style={{ flex: 1, color: '#6B7280', textAlign: 'right', fontSize: 10 }}>
          {syncCol
            ? `Sync col: ${syncCol} · ${totalSyncs} cycle${totalSyncs === 1 ? '' : 's'}`
            : 'No `Sync` column — viewing full trial'}
          {' · '}
          {viewport ? `[${viewport.t0.toFixed(2)}, ${viewport.t1.toFixed(2)}] s` : '—'}
          {fetching && ' · loading…'}
          {data && ` · ${data.n_returned}/${data.n_total} pts`}
        </span>
      </div>

      {/* Channel picker */}
      <div className="ins-channels" style={{
        display: 'flex', flexWrap: 'wrap', gap: 4, fontSize: 10,
      }}>
        {colNames.slice(0, 24).map((name) => {
          const on = channels.includes(name);
          return (
            <button
              key={name}
              onClick={() => toggleChannel(name)}
              style={{
                padding: '2px 6px',
                borderRadius: 3,
                border: on ? '1px solid #F09708' : '1px solid #2D3748',
                background: on ? 'rgba(240,151,8,.15)' : 'transparent',
                color: on ? '#F09708' : '#6B7280',
                cursor: 'pointer',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            >
              {name}
            </button>
          );
        })}
      </div>

      {/* Plot */}
      <svg
        ref={plotRef}
        viewBox="0 0 800 320"
        preserveAspectRatio="none"
        style={{
          width: '100%', height: 320,
          background: 'rgba(15,23,42,.4)',
          borderRadius: 4,
          cursor: dragStateRef.current ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        {data && data.t.length > 1 ? renderTraces(data, viewport) : (
          <text x={400} y={160} textAnchor="middle"
                style={{ fill: '#6B7280', fontSize: 12 }}>
            {fetching ? 'loading window…' : 'no data in window'}
          </text>
        )}
      </svg>

      {/* Footer: gestures hint */}
      <div style={{ color: '#6B7280', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}>
        wheel = zoom · drag = pan · ◀ ▶ = step sync · ⛶ = full trial
      </div>
    </div>
  );
}

function clampViewport(t0: number, t1: number, lo: number, hi: number)
                     : { t0: number; t1: number } {
  const span = t1 - t0;
  if (t0 < lo) { t0 = lo; t1 = lo + span; }
  if (t1 > hi) { t1 = hi; t0 = hi - span; }
  if (t0 < lo) t0 = lo;
  return { t0, t1 };
}

const TRACE_COLORS = [
  '#F09708', '#00FFB2', '#A78BFA', '#7FB5E4',
  '#1E5F9E', '#9E3838', '#FFB347', '#56B4E9',
];

function renderTraces(data: WindowResponse, viewport: { t0: number; t1: number } | null) {
  if (!viewport || data.t.length < 2) return null;
  const { t } = data;
  const W = 800, H = 320;
  const padL = 50, padR = 8, padT = 8, padB = 22;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;
  const tMin = viewport.t0;
  const tMax = viewport.t1;
  const tx = (v: number) => padL + ((v - tMin) / (tMax - tMin)) * plotW;

  // Stack each series in its own horizontal lane so they don't overlap.
  // Each lane gets equal vertical space; y is auto-scaled to its own min/max.
  const laneCount = Math.max(1, data.series.length);
  const laneH = plotH / laneCount;

  return (
    <>
      {/* Time axis grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((f, i) => {
        const x = padL + f * plotW;
        return (
          <g key={'gx' + i}>
            <line x1={x} x2={x} y1={padT} y2={padT + plotH}
                  stroke="#2D3748" strokeWidth={0.5} />
            <text x={x} y={H - 6} textAnchor="middle"
                  style={{ fill: '#6B7280', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}>
              {(tMin + f * (tMax - tMin)).toFixed(2)}
            </text>
          </g>
        );
      })}

      {data.series.map((s, idx) => {
        const yLane0 = padT + idx * laneH;
        const yLaneH = laneH - 4;
        let yMin = Infinity, yMax = -Infinity;
        for (const v of s.y) {
          if (v < yMin) yMin = v;
          if (v > yMax) yMax = v;
        }
        if (!isFinite(yMin) || !isFinite(yMax) || yMax === yMin) {
          yMin = (yMin || 0) - 1; yMax = (yMax || 0) + 1;
        }
        const yScale = (v: number) =>
          yLane0 + yLaneH - ((v - yMin) / (yMax - yMin)) * yLaneH;

        const path = s.y.map((v, i) =>
          `${i === 0 ? 'M' : 'L'}${tx(t[i]).toFixed(1)},${yScale(v).toFixed(1)}`,
        ).join('');
        const color = TRACE_COLORS[idx % TRACE_COLORS.length];

        return (
          <g key={s.name}>
            {/* Lane separator */}
            <line x1={padL} x2={W - padR} y1={yLane0} y2={yLane0}
                  stroke="#1E293B" strokeWidth={0.5} />
            {/* Channel name + range */}
            <text x={padL - 4} y={yLane0 + 11} textAnchor="end"
                  style={{ fill: color, fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}>
              {s.name}
            </text>
            <text x={padL - 4} y={yLane0 + yLaneH - 2} textAnchor="end"
                  style={{ fill: '#4B5563', fontSize: 8, fontFamily: 'JetBrains Mono, monospace' }}>
              {yMin.toFixed(2)}…{yMax.toFixed(2)}
            </text>
            <path d={path} stroke={color} strokeWidth={1.1} fill="none" />
          </g>
        );
      })}
    </>
  );
}
