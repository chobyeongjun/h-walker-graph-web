import { X, Trash2 } from 'lucide-react';
import { useWorkspace } from '../store/workspace';
import { STATS_LIB, EXPORT_FORMATS } from '../data/catalogs';

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(ts).toLocaleString();
}

const FMT_MAP: Record<string, { fmt: string; variant: string }> = {
  svg: { fmt: 'svg', variant: 'col2' },
  'pdf-grid': { fmt: 'pdf', variant: 'col2' },
  'pdf-each': { fmt: 'pdf', variant: 'col2' },
  png2x: { fmt: 'png', variant: 'col2' },
  eps: { fmt: 'eps', variant: 'col2' },
  tiff: { fmt: 'tiff', variant: 'col2' },
};

async function runBundle(preset: string, fmt: string, variant: string, cells: unknown[], showToast: (m: string) => void) {
  try {
    const res = await fetch('/api/graphs/bundle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset, format: fmt, variant, cells }),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `hwalker_bundle_${preset}_${fmt}.zip`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    showToast(`Bundle: ${preset.toUpperCase()} · ${fmt.toUpperCase()}`);
  } catch (e) {
    showToast(`Bundle failed: ${(e as Error).message}`);
  }
}

export default function Drawer() {
  const kind = useWorkspace((s) => s.drawer);
  const close = useWorkspace((s) => s.closeDrawer);
  const addCell = useWorkspace((s) => s.addCell);
  const showToast = useWorkspace((s) => s.showToast);
  const cells = useWorkspace((s) => s.cells);
  const preset = useWorkspace((s) => s.globalPreset);
  const history = useWorkspace((s) => s.history);
  const clearHistory = useWorkspace((s) => s.clearHistory);

  if (!kind) return null;

  const graphCellsForBundle = cells
    .filter((c) => c.type === 'graph' && c.graph)
    .map((c) => ({
      id: c.id,
      template: c.graph,
      preset: c.preset,
      stride_avg: c.strideAvg,
    }));

  return (
    <div className="drawer-wrap open" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <aside className="drawer">
        <header className="drawer-head">
          <div>
            <div className="ey">
              {kind === 'history' ? 'Activity timeline'
                : kind === 'exports' ? 'Export to publication'
                : kind === 'stats' ? 'Statistical tests'
                : 'Preferences'}
            </div>
            <h2>
              {kind === 'history' ? 'History'
                : kind === 'exports' ? 'Exports'
                : kind === 'stats' ? 'Stats library'
                : 'Settings'}
            </h2>
          </div>
          <button className="close" onClick={close}><X size={16} /></button>
        </header>

        <div className="drawer-body">
          {kind === 'history' && (
            <>
              {history.length === 0 ? (
                <div style={{ padding: 20, color: '#6B7280', fontSize: 12, fontStyle: 'italic' }}>
                  No activity yet. Upload a CSV to begin — every action
                  (uploads, recipes applied, chat messages, preset changes,
                  RUN ALL) will appear here.
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '0 0 10px' }}>
                    <button
                      onClick={() => { if (confirm('Clear all history?')) clearHistory(); }}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        background: 'rgba(248,113,113,.08)', border: '1px solid rgba(248,113,113,.3)',
                        color: '#f87171', padding: '4px 10px', borderRadius: 6,
                        font: '600 10.5px/1 Pretendard,sans-serif', cursor: 'pointer',
                      }}
                    >
                      <Trash2 size={11} /> Clear
                    </button>
                  </div>
                  {history.map((h) => (
                    <div key={h.id} className="hst-item">
                      <div className={`hst-dot hst-${h.kind}`} />
                      <div>
                        <div className="hst-title">{h.label}</div>
                        <div className="hst-sub">
                          {h.actor} · {relativeTime(h.ts)} · <span style={{ color: '#A78BFA' }}>{h.kind}</span>
                        </div>
                      </div>
                      <div className="hst-line" />
                    </div>
                  ))}
                </>
              )}
            </>
          )}

          {kind === 'stats' && STATS_LIB.map((s, i) => (
            <div key={i} className="slib-item" onClick={() => {
              addCell({
                id: 'c' + Date.now(),
                type: 'stat',
                op: s.op,
                dsIds: [],
                fmt: 'apa',
                inputs: { a: '', b: '' },
              });
              close();
              showToast(`Added ${s.name}`);
            }}>
              <div className="slib-row1">
                <span className="name">{s.name}</span>
                <span className="tag">{s.tag}</span>
              </div>
              <div className="slib-desc">{s.desc}</div>
              <div className="slib-when">When: <b>{s.when}</b></div>
            </div>
          ))}

          {kind === 'exports' && (
            <>
              <div className="exp-group">
                <h4>Graphs · {preset.toUpperCase()}</h4>
                <div className="exp-grid">
                  {EXPORT_FORMATS.graphs.map((f, i) => {
                    const m = FMT_MAP[f.fmt];
                    if (!m) return null;
                    return (
                      <button key={i} className="exp-card" onClick={() => runBundle(preset, m.fmt, m.variant, graphCellsForBundle, showToast)}>
                        <span className="name">{f.name}</span>
                        <span className="sub">{f.sub} · {graphCellsForBundle.length} graphs</span>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="exp-group">
                <h4>Stats</h4>
                <div className="exp-grid">
                  {EXPORT_FORMATS.stats.map((f, i) => (
                    <button key={i} className="exp-card" onClick={() => showToast(`Stats ${f.fmt}: Phase B`)}>
                      <span className="name">{f.name}</span>
                      <span className="sub">{f.sub}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="exp-bundle">
                <div className="lbl">
                  One-click bundle for <b>all {graphCellsForBundle.length} graphs</b> at <b>{preset.toUpperCase()}</b> preset.
                </div>
                <button onClick={() => runBundle(preset, 'svg', 'col2', graphCellsForBundle, showToast)}>SVG</button>
                <button onClick={() => runBundle(preset, 'pdf', 'col2', graphCellsForBundle, showToast)}>PDF</button>
              </div>
            </>
          )}

          {kind === 'settings' && (
            <>
              <div className="set-group">
                <h4>General</h4>
                <div className="set-row">
                  <label>Auto-save</label>
                  <div className="val">
                    <span className="set-chip on">Every 10s</span>
                    <span className="set-chip">Manual</span>
                  </div>
                </div>
                <div className="set-row">
                  <label>LLM</label>
                  <div className="val">
                    <span className="set-chip on">claude-haiku-4-5</span>
                  </div>
                </div>
              </div>
              <div className="set-group">
                <h4>Appearance</h4>
                <div className="set-row">
                  <label>Accent</label>
                  <div className="val set-swatch">
                    <span className="sw on" style={{ background: '#F09708' }} />
                    <span className="sw" style={{ background: '#00FFB2' }} />
                    <span className="sw" style={{ background: '#A78BFA' }} />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        <footer className="drawer-foot">
          <span>ESC to close</span>
        </footer>
      </aside>
    </div>
  );
}
