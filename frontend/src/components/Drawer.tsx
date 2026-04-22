import { useEffect, useState } from 'react';
import { X, Trash2, Download, Upload, RefreshCw, RotateCcw, Save, FolderOpen } from 'lucide-react';
import { usePage } from '../store/page';
import { STATS_LIB, EXPORT_FORMATS } from '../data/catalogs';
import { claudeHealth } from '../api';
import StudyPanel from './StudyPanel';

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
  const kind = usePage((s) => s.drawer);
  const close = usePage((s) => s.closeDrawer);
  const addCell = usePage((s) => s.addCell);
  const showToast = usePage((s) => s.showToast);
  const cells = usePage((s) => s.cells);
  const preset = usePage((s) => s.globalPreset);
  const history = usePage((s) => s.history);
  const clearHistory = usePage((s) => s.clearHistory);

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
                : kind === 'study' ? 'Research automation'
                : 'Preferences'}
            </div>
            <h2>
              {kind === 'history' ? 'History'
                : kind === 'exports' ? 'Exports'
                : kind === 'stats' ? 'Stats library'
                : kind === 'study' ? 'Study'
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

              <PageBackup close={close} />
            </>
          )}

          {kind === 'settings' && <SettingsPanel />}
          {kind === 'study' && <StudyPanel />}
        </div>

        <footer className="drawer-foot">
          <span>ESC to close</span>
        </footer>
      </aside>
    </div>
  );
}

const PAGES_KEY = 'hw_pages_v1';

interface SavedPage {
  name: string;
  saved_at: string;
  state: {
    cells: unknown[];
    datasets: unknown[];
    history: unknown[];
    globalPreset: string;
    pageTitle: string;
  };
}

function listSavedPages(): SavedPage[] {
  try {
    const raw = localStorage.getItem(PAGES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeSavedPages(pages: SavedPage[]) {
  localStorage.setItem(PAGES_KEY, JSON.stringify(pages));
}

function SettingsPanel() {
  const showToast = usePage((s) => s.showToast);
  const clearHistory = usePage((s) => s.clearHistory);
  const cells = usePage((s) => s.cells);
  const datasets = usePage((s) => s.datasets);
  const history = usePage((s) => s.history);
  const globalPreset = usePage((s) => s.globalPreset);
  const pageTitle = usePage((s) => s.pageTitle);

  const [health, setHealth] = useState<{ provider: string; model: string; key_present: boolean } | null>(null);
  const [cacheInfo, setCacheInfo] = useState<{ memory_entries: number; disk_entries: number; disk_mb: number; cache_dir: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [pages, setPages] = useState<SavedPage[]>(() => listSavedPages());
  const [newPageName, setNewPageName] = useState('');

  function saveAsPage() {
    const name = newPageName.trim() || pageTitle.trim() || 'Untitled page';
    const state: SavedPage['state'] = {
      cells: cells.map((c) => {
        const { loading: _l, error: _e, computeData: _cd, statData: _sd,
                previewBlobUrl: _p, ...rest } = c as typeof c & { [k: string]: unknown };
        void _l; void _e; void _cd; void _sd; void _p;
        return rest;
      }),
      datasets: datasets.map((d) => {
        const { analyzing: _a, analyzeError: _ae, analysis: _an, ...rest } = d as typeof d & { [k: string]: unknown };
        void _a; void _ae; void _an;
        return rest;
      }),
      history,
      globalPreset,
      pageTitle,
    };
    const next: SavedPage = { name, saved_at: new Date().toISOString(), state };
    const list = listSavedPages().filter((p) => p.name !== name);
    list.unshift(next);
    writeSavedPages(list);
    setPages(list);
    setNewPageName('');
    showToast(`Saved page: ${name}`);
  }

  function loadPage(name: string) {
    const p = listSavedPages().find((x) => x.name === name);
    if (!p) return;
    if (!confirm(`Load "${name}"? Current workspace will be replaced.`)) return;
    localStorage.setItem('hw_page_v1', JSON.stringify({
      state: {
        cells: p.state.cells,
        datasets: p.state.datasets,
        currentPreset: p.state.globalPreset,
        globalPreset: p.state.globalPreset,
        pageTitle: p.state.pageTitle,
        history: p.state.history,
      },
      version: 0,
    }));
    location.reload();
  }

  function deletePage(name: string) {
    if (!confirm(`Delete saved page "${name}"?`)) return;
    const list = listSavedPages().filter((p) => p.name !== name);
    writeSavedPages(list);
    setPages(list);
    showToast(`Deleted page: ${name}`);
  }

  function newBlankPage() {
    if (!confirm('Start a new page? Current workspace will be cleared (save first if needed).')) return;
    localStorage.removeItem('hw_page_v1');
    location.reload();
  }

  useEffect(() => {
    claudeHealth().then(setHealth).catch(() => setHealth(null));
    refreshCache();
  }, []);

  function refreshCache() {
    fetch('/api/analyze/cache/stats').then((r) => r.json()).then(setCacheInfo).catch(() => {});
  }

  async function clearAnalyzerCache() {
    if (!confirm('Clear analyzer disk cache? Next analysis will re-run from scratch.')) return;
    setBusy(true);
    try {
      const r = await fetch('/api/analyze/cache', { method: 'DELETE' });
      const j = await r.json();
      showToast(`Cleared ${j.removed} cached analyses`);
      refreshCache();
    } catch (e) {
      showToast(`Cache clear failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  function resetEverything() {
    if (!confirm('Reset EVERYTHING? Clears the current page + all saved pages + history. Backend upload files on disk are preserved.')) return;
    localStorage.clear();
    location.reload();
  }

  return (
    <>
      <div className="set-group">
        <h4>Pages</h4>
        <div className="set-info">
          <div className="set-row-info">
            <span className="k">Current</span>
            <b>{pageTitle || '(untitled)'}</b>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
            <input
              value={newPageName}
              onChange={(e) => setNewPageName(e.target.value)}
              placeholder="Save as… (leave blank to use current title)"
              style={{
                flex: 1, padding: '6px 10px', borderRadius: 6,
                background: 'rgba(23,27,94,.5)', color: '#E2E8F0',
                border: '1px solid rgba(255,255,255,.08)', outline: 0,
                font: '500 11.5px/1 Pretendard,sans-serif',
              }}
            />
            <button onClick={saveAsPage} style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
              background: '#F09708', color: '#0B0E2E', border: 'none',
              font: '700 11px/1 Pretendard,sans-serif',
            }}>
              <Save size={12} /> Save page
            </button>
          </div>
        </div>

        {pages.length > 0 && (
          <div className="set-info" style={{ marginTop: 10 }}>
            {pages.map((p) => (
              <div key={p.name} className="set-row-info" style={{ justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1, minWidth: 0 }}>
                  <span style={{ color: '#F09708', fontWeight: 700, flexShrink: 0 }}>{p.name}</span>
                  <span style={{ color: '#6B7280', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {new Date(p.saved_at).toLocaleString()}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    onClick={() => loadPage(p.name)}
                    style={{
                      padding: '3px 8px', borderRadius: 5, cursor: 'pointer',
                      background: 'rgba(167,139,250,.1)', color: '#A78BFA',
                      border: '1px solid rgba(167,139,250,.3)',
                      font: '600 10px/1 Pretendard,sans-serif',
                    }}
                  ><FolderOpen size={10} /> Load</button>
                  <button
                    onClick={() => deletePage(p.name)}
                    style={{
                      padding: '3px 6px', borderRadius: 5, cursor: 'pointer',
                      background: 'transparent', color: '#6B7280',
                      border: '1px solid rgba(255,255,255,.08)',
                    }}
                  ><Trash2 size={10} /></button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="set-actions">
          <button onClick={newBlankPage}>
            <RotateCcw size={12} /> Start a new blank page
          </button>
        </div>
      </div>

      <div className="set-group">
        <h4>Claude API</h4>
        <div className="set-info">
          <div className="set-row-info">
            <span className="k">Model</span>
            <code>{health?.model || '—'}</code>
          </div>
          <div className="set-row-info">
            <span className="k">API key</span>
            <span className={`set-dot ${health?.key_present ? 'ok' : 'bad'}`}>
              {health?.key_present ? '● ready' : '● missing'}
            </span>
          </div>
          <div className="set-row-info">
            <span className="k">Provider</span>
            <code>{health?.provider || '—'}</code>
          </div>
        </div>
        <ApiKeyEditor
          keyPresent={!!health?.key_present}
          onSaved={() => {
            // Refresh health immediately
            fetch('/api/claude/health').then((r) => r.json()).then(setHealth).catch(() => {});
          }}
        />
      </div>

      <div className="set-group">
        <h4>Analyzer cache</h4>
        <div className="set-info">
          <div className="set-row-info">
            <span className="k">Disk entries</span>
            <b>{cacheInfo?.disk_entries ?? '—'}</b>
          </div>
          <div className="set-row-info">
            <span className="k">Disk size</span>
            <b>{cacheInfo?.disk_mb ?? '—'} MB</b>
          </div>
          <div className="set-row-info">
            <span className="k">Location</span>
            <code style={{ fontSize: 9, wordBreak: 'break-all' }}>{cacheInfo?.cache_dir || '—'}</code>
          </div>
        </div>
        <div className="set-actions">
          <button onClick={refreshCache} disabled={busy}>
            <RefreshCw size={12} /> Refresh
          </button>
          <button onClick={clearAnalyzerCache} disabled={busy} className="danger">
            <Trash2 size={12} /> Clear analyzer cache
          </button>
        </div>
      </div>

      <div className="set-group">
        <h4>Current page</h4>
        <div className="set-info">
          <div className="set-row-info">
            <span className="k">Datasets</span>
            <b>{datasets.length}</b>
          </div>
          <div className="set-row-info">
            <span className="k">Cells</span>
            <b>{cells.length}</b>
          </div>
          <div className="set-row-info">
            <span className="k">History entries</span>
            <b>{history.length}</b>
          </div>
          <div className="set-row-info">
            <span className="k">Journal preset</span>
            <b>{globalPreset.toUpperCase()}</b>
          </div>
        </div>
        <div className="set-actions">
          <button onClick={() => { if (confirm('Clear history timeline?')) clearHistory(); }}>
            <Trash2 size={12} /> Clear history
          </button>
          <button onClick={resetEverything} className="danger">
            <RotateCcw size={12} /> Reset everything (current page + saved pages)
          </button>
        </div>
        <div style={{ padding: '8px 0 0', color: '#6B7280', fontSize: 10.5 }}>
          Tip: backup/restore this page as a JSON file in the <b style={{ color: '#F09708' }}>Exports</b> drawer.
        </div>
      </div>
    </>
  );
}

/**
 * PageBackup · portable JSON export/import of the current page.
 *
 * Lives in the Exports drawer alongside the paper-figure bundle —
 * both are "downloadable artifacts" from the current work. The saved-
 * Pages list (in-browser named snapshots) stays in Settings since it's
 * a different concept (project management, not a one-off artifact).
 */
function PageBackup({ close }: { close: () => void }) {
  const pageTitle = usePage((s) => s.pageTitle);
  const globalPreset = usePage((s) => s.globalPreset);
  const datasets = usePage((s) => s.datasets);
  const cells = usePage((s) => s.cells);
  const history = usePage((s) => s.history);
  const showToast = usePage((s) => s.showToast);

  function exportPage() {
    const blob = new Blob([JSON.stringify({
      schema: 'hw_page_v1',
      exported_at: new Date().toISOString(),
      pageTitle,
      globalPreset,
      datasets,
      cells,
      history,
    }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const safe = (pageTitle || 'page').replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 40);
    a.download = `hwalker_${safe}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    showToast('Page JSON downloaded');
  }

  function importPage() {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = '.json,application/json';
    inp.onchange = async () => {
      const f = inp.files?.[0];
      if (!f) return;
      try {
        const text = await f.text();
        const data = JSON.parse(text);
        if (!data.schema || !data.schema.startsWith('hw_page_')) {
          throw new Error('Not a H-Walker page file');
        }
        if (!confirm('Replace current page with imported file? (Save-as first if you want to keep this one)')) return;
        localStorage.setItem('hw_page_v1', JSON.stringify({
          state: {
            cells: data.cells || [],
            datasets: data.datasets || [],
            currentPreset: data.globalPreset || 'ieee',
            globalPreset: data.globalPreset || 'ieee',
            pageTitle: data.pageTitle || 'Imported page',
            history: data.history || [],
          },
          version: 0,
        }));
        close();
        location.reload();
      } catch (e) {
        showToast(`Import failed: ${(e as Error).message}`);
      }
    };
    inp.click();
  }

  return (
    <div className="exp-group">
      <h4>Page backup · JSON</h4>
      <div style={{ padding: '0 0 10px', color: '#9CA3AF', fontSize: 11.5, lineHeight: 1.5 }}>
        Snapshot the whole page (datasets, cells, history, preset) to a
        portable JSON file. Use this to hand off a study to a collaborator
        or restore a page on a different computer.
      </div>
      <div className="exp-grid">
        <button className="exp-card" onClick={exportPage}>
          <span className="name"><Download size={13} /> Export page JSON</span>
          <span className="sub">{cells.length} cells · {datasets.length} datasets</span>
        </button>
        <button className="exp-card" onClick={importPage}>
          <span className="name"><Upload size={13} /> Import page JSON</span>
          <span className="sub">Replaces current page (save-as first)</span>
        </button>
      </div>
    </div>
  );
}

/** Inline editor that posts the Anthropic key to /api/claude/set-key.
 *  The key is stored in ~/.hwalker.env (chmod 600) and live-bound into
 *  the running server so the user doesn't have to restart. */
function ApiKeyEditor({ keyPresent, onSaved }: { keyPresent: boolean; onSaved: () => void }) {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const showToast = usePage((s) => s.showToast);

  async function save() {
    const k = value.trim();
    if (!k) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch('/api/claude/set-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: k }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail || `${r.status}`);
      setValue('');
      showToast('API key saved to ~/.hwalker.env · live');
      onSaved();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ marginTop: 10, padding: '10px 12px', background: 'rgba(11,14,46,.45)',
                  border: '1px solid rgba(240,151,8,.2)', borderRadius: 8,
                  display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ font: '700 9.5px/1 Pretendard,sans-serif', letterSpacing: '.2em',
                      textTransform: 'uppercase', color: '#F09708' }}>
        {keyPresent ? 'Replace API key' : 'Set API key'}
      </label>
      <div style={{ display: 'flex', gap: 6 }}>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="sk-ant-api03-..."
          style={{
            flex: 1, background: 'rgba(23,27,94,.5)', border: '1px solid rgba(255,255,255,.1)',
            borderRadius: 6, padding: '6px 10px', color: '#fff', font: "500 12px/1 'JetBrains Mono',monospace",
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') save(); }}
        />
        <button
          onClick={save}
          disabled={busy || !value.trim()}
          style={{
            background: '#F09708', color: '#0B0E2E', border: 'none', borderRadius: 6,
            padding: '6px 14px', font: '700 11px/1 Pretendard,sans-serif', letterSpacing: '.06em',
            cursor: 'pointer', opacity: value.trim() ? 1 : 0.5,
          }}
        >
          {busy ? '…saving' : 'SAVE'}
        </button>
      </div>
      <div style={{ font: '500 10px/1.4 Pretendard,sans-serif', color: '#9CA3AF' }}>
        Saved to <code>~/.hwalker.env</code> (chmod 600). The H-Walker CORE
        launcher auto-loads it on every restart. Get one at{' '}
        <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer"
           style={{ color: '#F09708' }}>console.anthropic.com</a>.
      </div>
      {err && (
        <div style={{ color: '#f87171', font: '500 10.5px/1.4 Pretendard,sans-serif' }}>
          ✗ {err}
        </div>
      )}
    </div>
  );
}
