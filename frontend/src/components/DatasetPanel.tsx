import { useEffect, useMemo, useRef, useState } from 'react';
import { Link2, Trash2, Home, Plus, X } from 'lucide-react';
import { usePage, type Dataset, type WorkspaceRoom } from '../store/page';
import { uploadDataset, deleteDataset as apiDeleteDataset, syncAlign, syncGatesPreview, syncGatesExecute, syncTrimExecute, type GateInfo } from '../api';

// ── Experiment prefix extraction ─────────────────────────────────────────
// Strips known data-type suffixes so "S01_Walk_Pre_force.csv" and
// "S01_Walk_Pre_imu.csv" both map to room "S01_Walk_Pre".
const _TYPE_SUFFIX = /[_\s\-]+(force|imu|mocap|fp|forceplate|robot|treadmill|emg|acc|gyro|kin(?:ematics)?|grf|motion|sync|trial\d*)$/i;

function experimentPrefix(filename: string): string {
  const base = filename.replace(/\.csv$/i, '').trim();
  return base.replace(_TYPE_SUFFIX, '').trim() || base;
}

export default function DatasetPanel() {
  const datasets = usePage((s) => s.datasets);
  const rooms = usePage((s) => s.rooms);
  const activeRoomId = usePage((s) => s.activeRoomId);
  const createRoom = usePage((s) => s.createRoom);
  const setActiveRoom = usePage((s) => s.setActiveRoom);
  const deleteRoom = usePage((s) => s.deleteRoom);
  const renameRoom = usePage((s) => s.renameRoom);
  const addDatasetToRoom = usePage((s) => s.addDatasetToRoom);
  const setActive = usePage((s) => s.setActiveDataset);
  const addDataset = usePage((s) => s.addDataset);
  const removeDataset = usePage((s) => s.removeDataset);
  const setDatasetMeta = usePage((s) => s.setDatasetMeta);
  const applyRecipes = usePage((s) => s.applyRecipes);
  const showToast = usePage((s) => s.showToast);
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  // Multi-select for "create comparison room"
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }
  function createComparisonRoom() {
    if (selectedIds.size === 0) return;
    const name = window.prompt('Comparison room name:', `Compare ${new Date().toLocaleTimeString().slice(0, 5)}`);
    if (!name || !name.trim()) return;
    const ids = Array.from(selectedIds);
    const id = createRoom(name.trim(), ids);
    setSelectedIds(new Set());
    setActiveRoom(id);
    showToast(`✓ "${name}" created with ${ids.length} datasets`);
  }

  // When in a room, show only that room's datasets
  const activeRoom = rooms.find((r) => r.id === activeRoomId) ?? null;
  const visibleDatasets = activeRoomId && activeRoom
    ? datasets.filter((d) => activeRoom.datasetIds.includes(d.id))
    : datasets;

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    let accepted = 0;
    const skipped: string[] = [];

    for (const f of Array.from(files)) {
      const n = f.name.toLowerCase();
      const looksCsv = /\.csv(\b|$|\s|\.)/.test(n) || !/\.\w+$/.test(n);
      if (!looksCsv) { skipped.push(f.name); continue; }

      try {
        const ds = await uploadDataset(f);

        // ── 1. Auto room assignment by filename prefix ──────────────────
        const prefix = experimentPrefix(f.name);
        const existingRoom = rooms.find((r) => r.name.toLowerCase() === prefix.toLowerCase());
        let roomId: string;
        if (existingRoom) {
          roomId = existingRoom.id;
          addDatasetToRoom(roomId, ds.id);
        } else {
          roomId = createRoom(prefix, [ds.id]);
        }

        addDataset(ds);
        setActive(ds.id);
        setActiveRoom(roomId);

        // ── 2. Auto gate-split if sync_col detected ────────────────────
        const syncCol = (ds as { sync_col?: string | null }).sync_col;
        let didGateSplit = false;
        if (syncCol) {
          try {
            const preview = await syncGatesPreview({ ds_id: ds.id, min_gate_width_s: 2.0 });
            if (preview.n_trials >= 2) {
              showToast(`Sync gate detected — auto-splitting ${preview.n_trials} trials…`);
              const split = await syncGatesExecute({ ds_id: ds.id, min_gate_width_s: 2.0 });
              const allDs: Dataset[] = await fetch('/api/datasets').then((r) => r.json());
              split.gates.forEach((g) => {
                const trial = allDs.find((x) => x.id === g.new_ds_id);
                if (trial) {
                  addDataset(trial);
                  addDatasetToRoom(roomId, trial.id);
                }
              });
              showToast(`✓ Auto-split into ${split.n_trials} trials in room "${prefix}"`);
              didGateSplit = true;
            }
          } catch { /* no gates detected — proceed normally */ }
        }

        // ── 3. Fallback: no sync column → auto edge-trim (앞/뒤 3걸음) ──
        if (!didGateSplit && !syncCol) {
          try {
            const trim = await syncTrimExecute({ ds_id: ds.id, n_edge: 3 });
            if (trim.new_ds_id) {
              const allDs: Dataset[] = await fetch('/api/datasets').then((r) => r.json());
              const trimmed = allDs.find((x) => x.id === trim.new_ds_id);
              if (trimmed) {
                addDataset(trimmed);
                addDatasetToRoom(roomId, trimmed.id);
              }
              const kept = trim.info.kept_footfalls;
              const total = trim.info.total_footfalls;
              showToast(`✓ Edge-trimmed: ${kept}/${total} steps (dropped 3 at each end)`);
            }
          } catch { /* no force column or too few steps — skip silently */ }
        }

        showToast(`Uploaded ${f.name}`);
        applyRecipes(ds.id).catch((e) => showToast(`Auto-run failed: ${(e as Error).message}`));
        accepted += 1;
      } catch (e) {
        showToast(`Upload failed (${f.name}): ${(e as Error).message}`);
      }
    }
    if (accepted === 0 && skipped.length) {
      showToast(`Not CSV files: ${skipped.slice(0, 3).join(', ')}${skipped.length > 3 ? '…' : ''}`);
    }
  }

  // Phase 3 · cross-source sync detection (within visible datasets only)
  const syncStatus = useMemo(() => {
    const unsynced = visibleDatasets.filter((d) => !('synced_from' in d) || !d.synced_from);
    const rates = new Set(unsynced.map((d) => d.hz));
    const sourceTypes = new Set(unsynced.map((d) => (d as { source_type?: string }).source_type || 'unknown').filter((s) => s !== 'unknown'));
    const cross = sourceTypes.size >= 2;
    const hzMismatch = rates.size >= 2;
    const withA7 = unsynced.filter((d) => (d as { sync_col?: string | null }).sync_col).length;
    return {
      needed: unsynced.length >= 2 && (cross || hzMismatch),
      unsynced,
      rates: Array.from(rates),
      cross,
      hzMismatch,
      withA7,
    };
  }, [datasets]);

  const [syncBusy, setSyncBusy] = useState(false);

  async function runSync() {
    if (!syncStatus.needed || syncBusy) return;
    setSyncBusy(true);
    try {
      const resp = await syncAlign({
        dataset_ids: syncStatus.unsynced.map((d) => d.id),
        crop_to_a7: syncStatus.withA7 > 0,
      });
      // Reload datasets so the new _synced entries appear
      showToast(`✓ Synced ${resp.aligned.length} dataset(s) @ ${Math.round(resp.target_hz)} Hz · ${resp.common_duration_s.toFixed(2)}s window`);
      // Fetch the new _synced datasets and add them to the store
      const list = await fetch('/api/datasets').then((r) => r.json());
      resp.aligned.forEach((a) => {
        const d = list.find((x: { id: string }) => x.id === a.new_id);
        if (d) addDataset(d);
      });
    } catch (e) {
      showToast(`Sync failed: ${(e as Error).message}`);
    } finally {
      setSyncBusy(false);
    }
  }

  return (
    <div className="ds-panel">
      <div className="ds-head">
        <span className="ey">DATA SOURCES</span>
        <span className="label">Datasets</span>
        <div className="rest">
          <button className="ds-btn plain" onClick={() => fileRef.current?.click()}>＋ Add CSV</button>
        </div>
      </div>

      {/* ── Room tabs ──────────────────────────────────────────────────── */}
      <RoomTabs
        rooms={rooms}
        activeRoomId={activeRoomId}
        onSelect={setActiveRoom}
        onDelete={deleteRoom}
        onRename={renameRoom}
        onCreate={() => {
          const id = createRoom(`Room ${rooms.length + 1}`);
          setActiveRoom(id);
        }}
      />

      {syncStatus.needed && (
        <div className="ds-sync-banner" style={{
          margin: '8px 12px 0', padding: '10px 12px',
          background: 'rgba(167,139,250,.08)', border: '1px solid rgba(167,139,250,.4)',
          borderRadius: 10, display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <Link2 size={16} style={{ color: '#A78BFA', flexShrink: 0 }} />
          <div style={{ flex: 1, font: '500 11.5px/1.5 Pretendard,sans-serif', color: '#E2E8F0' }}>
            <b style={{ color: '#A78BFA' }}>
              {syncStatus.cross ? 'Cross-source datasets detected' : 'Sample-rate mismatch'}
            </b>
            {' — '}
            {syncStatus.hzMismatch && <>Hz differs: {syncStatus.rates.join(' vs ')}. </>}
            {syncStatus.withA7 > 0
              ? <>A7 trigger found in <b>{syncStatus.withA7}</b> file(s) → will crop + upsample linearly.</>
              : <>No A7 column — will resample without cropping (assumes time-aligned already).</>}
          </div>
          <button
            onClick={runSync}
            disabled={syncBusy}
            style={{
              background: '#A78BFA', color: '#0B0E2E', border: 'none', borderRadius: 7,
              padding: '6px 14px', font: '700 10.5px/1 Pretendard,sans-serif',
              letterSpacing: '.08em', textTransform: 'uppercase', cursor: 'pointer',
              opacity: syncBusy ? 0.5 : 1, display: 'flex', alignItems: 'center', gap: 5,
            }}
          >
            <Link2 size={11} />
            {syncBusy ? 'Syncing…' : 'Sync now'}
          </button>
        </div>
      )}

      {selectedIds.size > 0 && (
        <div className="compare-row">
          <span className="n-sel">{selectedIds.size} selected</span>
          <button
            className="ds-btn"
            onClick={createComparisonRoom}
            style={{ background: '#F09708', color: '#0B0E2E', fontWeight: 700 }}
          >
            <Plus size={12} /> Create comparison room
          </button>
          <button className="ds-btn plain" onClick={() => setSelectedIds(new Set())}>
            Clear
          </button>
        </div>
      )}

      {visibleDatasets.length === 0 && (
        <div className="ds-empty">
          <div className="ds-empty-title">
            {activeRoomId ? 'Room is empty' : 'No datasets yet'}
          </div>
          <div className="ds-empty-sub">
            {activeRoomId
              ? 'Drop a CSV here — it will be auto-assigned to this room.'
              : 'Drop a CSV below to get started — default recipe auto-runs and fills the canvas.'}
          </div>
        </div>
      )}

      <div className="ds-grid">
        {visibleDatasets.map((d) => (
          <div
            key={d.id}
            className={`ds-card${d.active ? ' active' : ''}`}
            onClick={() => setActive(d.id)}
          >
            <div className="ds-row1">
              <input
                type="checkbox"
                className="ds-chk"
                checked={selectedIds.has(d.id)}
                onChange={() => toggleSelected(d.id)}
                onClick={(e) => e.stopPropagation()}
                title="Select for comparison room"
              />
              <span className={`tag ${d.tag}`}>{d.tag}</span>
              {(d as { source_type?: string }).source_type && (d as { source_type?: string }).source_type !== 'unknown' && (
                <span style={{
                  font: '600 8.5px/1 JetBrains Mono, monospace',
                  padding: '2px 5px', borderRadius: 3, letterSpacing: '.08em',
                  background: 'rgba(167,139,250,.12)', color: '#A78BFA',
                  textTransform: 'uppercase',
                }} title="Source type auto-detected from filename/columns">
                  {(d as { source_type: string }).source_type}
                </span>
              )}
              {(d as { synced_from?: string | null }).synced_from && (
                <span style={{
                  font: '600 8.5px/1 JetBrains Mono, monospace',
                  padding: '2px 5px', borderRadius: 3, letterSpacing: '.08em',
                  background: 'rgba(0,255,178,.14)', color: '#00FFB2',
                  textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 3,
                }} title={`Synced from ${(d as { synced_from: string }).synced_from}`}>
                  <Link2 size={8} /> synced
                </span>
              )}
              {(d as { sync_col?: string | null }).sync_col && !(d as { synced_from?: string | null }).synced_from && (
                <span style={{
                  font: '600 8.5px/1 JetBrains Mono, monospace',
                  padding: '2px 5px', borderRadius: 3, letterSpacing: '.08em',
                  background: 'rgba(240,151,8,.12)', color: '#F09708',
                }} title={`Analog sync column: ${(d as { sync_col: string }).sync_col}`}>
                  A7
                </span>
              )}
              <span className="name" title={d.name}>{d.name}</span>
              <button
                className="ds-del"
                title="Delete dataset"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!confirm(`Delete ${d.name}? This also removes linked cells' bindings.`)) return;
                  apiDeleteDataset(d.id)
                    .catch(() => { /* proceed with local removal anyway */ })
                    .finally(() => {
                      removeDataset(d.id);
                      showToast(`Deleted ${d.name}`);
                    });
                }}
              ><Trash2 size={12} /></button>
            </div>
            <div className="ds-row2">
              <span><b>{d.rows.toLocaleString()}</b> rows</span>
              <span><b>{d.dur}</b></span>
              <span><b>{d.hz}</b></span>
              {d.analyzing && <span style={{ color: '#F09708' }}>· analyzing…</span>}
              {d.analysis && 'mode' in d.analysis && d.analysis.mode === 'hwalker' && (
                <span style={{ color: '#00FFB2' }}>
                  · {d.analysis.left.n_strides}L / {d.analysis.right.n_strides}R strides
                </span>
              )}
              {d.analysis && 'fallback_mode' in d.analysis && (
                <span style={{ color: '#7FB5E4' }}>· generic mode</span>
              )}
              {d.analyzeError && (
                <span style={{ color: '#f87171' }}>· err: {d.analyzeError.slice(0, 40)}</span>
              )}
            </div>
            <div className="ds-tags" onClick={(e) => e.stopPropagation()}>
              <DatasetTag
                label="subj"
                value={d.subject_id || ''}
                placeholder="s01"
                onChange={(v) => setDatasetMeta(d.id, { subject_id: v })}
              />
              <DatasetTag
                label="cond"
                value={d.condition || ''}
                placeholder="Pre / Post / Control"
                onChange={(v) => setDatasetMeta(d.id, { condition: v, group: v })}
              />
              {d.group && d.group !== d.condition && (
                <DatasetTag
                  label="group"
                  value={d.group}
                  placeholder="—"
                  onChange={(v) => setDatasetMeta(d.id, { group: v })}
                />
              )}
            </div>
            <TreadmillEditor dataset={d} />
            {(d as { sync_col?: string | null }).sync_col && !(d as { split_from?: string | null }).split_from && (
              <GateSplitPanel dataset={d} />
            )}
            <div className="ds-cols">
              {d.cols.slice(0, 5).map((c, i) => (
                <span key={i} className={`ds-col${c.mapped && c.mapped !== '—' ? ' mapped' : ''}`}>
                  {c.name}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div
        className={`ds-upload${dragOver ? ' drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div className="ds-drop" onClick={() => fileRef.current?.click()}>
          <b>Drop CSV</b>&nbsp;files here, or click to browse
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          multiple
          hidden
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
      </div>
    </div>
  );
}

/** Phase 2 · inline tag editor for subject/condition/group. */
function DatasetTag({ label, value, placeholder, onChange }: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
}) {
  return (
    <span className={`ds-tag-ed${value ? ' set' : ''}`}>
      <span className="ds-tag-lbl">{label}</span>
      <input
        className="ds-tag-inp"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </span>
  );
}

// ── Room Tabs ─────────────────────────────────────────────────────────────
// Compact tab strip at the top of the DatasetPanel. "거실" = global view,
// other tabs = experiment rooms auto-created from filename prefixes.

function RoomTabs({ rooms, activeRoomId, onSelect, onDelete, onRename, onCreate }: {
  rooms: WorkspaceRoom[];
  activeRoomId: string | null;
  onSelect: (id: string | null) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, name: string) => void;
  onCreate: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editVal, setEditVal] = useState('');

  if (rooms.length === 0) return null;

  const tabStyle = (active: boolean): React.CSSProperties => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '5px 8px', borderRadius: 6, cursor: 'pointer',
    border: 'none', flexShrink: 0,
    font: '600 10.5px/1.4 Pretendard,sans-serif',
    letterSpacing: '.04em',
    background: active ? 'rgba(240,151,8,.18)' : 'rgba(255,255,255,.04)',
    color: active ? '#F09708' : '#94A3B8',
    transition: 'background .15s, color .15s',
    whiteSpace: 'nowrap',
  });

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4,
      padding: '8px 12px 6px', overflowX: 'auto',
      borderBottom: '1px solid rgba(255,255,255,.06)',
      scrollbarWidth: 'none',
      WebkitOverflowScrolling: 'touch' as any,
    }}>
      {/* 거실 */}
      <button style={tabStyle(!activeRoomId)} onClick={() => onSelect(null)} title="거실 — see all datasets">
        <Home size={10} />
        거실
      </button>

      {rooms.map((r) => (
        <div key={r.id} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          {editingId === r.id ? (
            <input
              autoFocus
              value={editVal}
              onChange={(e) => setEditVal(e.target.value)}
              onBlur={() => { onRename(r.id, editVal || r.name); setEditingId(null); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { onRename(r.id, editVal || r.name); setEditingId(null); }
                if (e.key === 'Escape') setEditingId(null);
              }}
              style={{
                width: 90, font: '600 10.5px/1 Pretendard,sans-serif',
                background: 'rgba(240,151,8,.12)', border: '1px solid #F09708',
                borderRadius: 5, padding: '3px 6px', color: '#F09708', outline: 'none',
              }}
            />
          ) : (
            <button
              style={tabStyle(activeRoomId === r.id)}
              onClick={() => onSelect(r.id)}
              onDoubleClick={() => { setEditingId(r.id); setEditVal(r.name); }}
              title={`${r.name} · ${r.datasetIds.length} datasets — double-click to rename`}
            >
              {r.name.length > 14 ? r.name.slice(0, 13) + '…' : r.name}
              <span style={{
                marginLeft: 2, fontSize: 9, opacity: .6,
                background: 'rgba(255,255,255,.1)', borderRadius: 3, padding: '1px 3px',
              }}>{r.datasetIds.length}</span>
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(r.id); }}
            title={`Delete room "${r.name}"`}
            style={{
              border: 'none', background: 'none', cursor: 'pointer',
              color: '#64748B', padding: '2px 2px', borderRadius: 3,
              display: 'flex', alignItems: 'center',
            }}
          ><X size={9} /></button>
        </div>
      ))}

      <button
        onClick={onCreate}
        title="Create new empty room"
        style={{
          ...tabStyle(false), flexShrink: 0,
          color: '#64748B', background: 'none',
        }}
      ><Plus size={10} /></button>
    </div>
  );
}

/**
 * GateSplitPanel — shown when a dataset has an analog sync column but
 * hasn't been split yet. Lets the user preview detected HIGH gate regions
 * (one per MoCap recording) then split them into separate sub-datasets.
 */
function GateSplitPanel({ dataset }: { dataset: Dataset }) {
  const addDataset = usePage((s) => s.addDataset);
  const showToast = usePage((s) => s.showToast);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'preview' | 'splitting'>('idle');
  const [gates, setGates] = useState<GateInfo[]>([]);
  const [sigCol, setSigCol] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function preview(e: React.MouseEvent) {
    e.stopPropagation();
    setPhase('loading');
    setError(null);
    try {
      const resp = await syncGatesPreview({ ds_id: dataset.id });
      setGates(resp.gates);
      setSigCol(resp.signal_col);
      setPhase('preview');
    } catch (err) {
      setError((err as Error).message);
      setPhase('idle');
    }
  }

  async function execute(e: React.MouseEvent) {
    e.stopPropagation();
    setPhase('splitting');
    try {
      const resp = await syncGatesExecute({ ds_id: dataset.id });
      const list: Dataset[] = await fetch('/api/datasets').then((r) => r.json());
      resp.gates.forEach((g) => {
        const d = list.find((x) => x.id === g.new_ds_id);
        if (d) addDataset(d);
      });
      showToast(`✓ Split into ${resp.n_trials} trials via sync gate`);
      setPhase('idle');
    } catch (err) {
      showToast(`Split failed: ${(err as Error).message}`);
      setPhase('preview');
    }
  }

  const btnBase: React.CSSProperties = {
    border: 'none', borderRadius: 6, cursor: 'pointer',
    font: '700 10px/1 Pretendard,sans-serif',
    letterSpacing: '.08em', textTransform: 'uppercase', padding: '5px 10px',
  };

  if (phase === 'loading') {
    return (
      <div style={{ margin: '6px 0 2px', fontSize: 11, color: '#F09708' }}
           onClick={(e) => e.stopPropagation()}>
        Detecting gates…
      </div>
    );
  }

  if (phase === 'splitting') {
    return (
      <div style={{ margin: '6px 0 2px', fontSize: 11, color: '#A78BFA' }}
           onClick={(e) => e.stopPropagation()}>
        Splitting…
      </div>
    );
  }

  if (phase === 'preview') {
    return (
      <div style={{ margin: '6px 0 2px' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontSize: 11, color: '#E2E8F0', marginBottom: 5 }}>
          <b style={{ color: '#F09708' }}>{gates.length}</b> trials · col:{' '}
          <span style={{ fontFamily: 'JetBrains Mono,monospace', color: '#7FB5E4' }}>{sigCol}</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginBottom: 7 }}>
          {gates.map((g) => (
            <span key={g.trial_index} style={{
              font: '600 9.5px/1 JetBrains Mono,monospace',
              padding: '2px 6px', borderRadius: 4,
              background: 'rgba(240,151,8,.12)', color: '#F09708',
            }}>
              trial_{String(g.trial_index).padStart(2, '0')} {g.duration_s.toFixed(1)}s
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={execute}
                  style={{ ...btnBase, background: '#F09708', color: '#0B0E2E' }}>
            Split
          </button>
          <button onClick={(e) => { e.stopPropagation(); setPhase('idle'); }}
                  style={{ ...btnBase, background: 'rgba(255,255,255,.07)', color: '#94A3B8' }}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // idle
  return (
    <div style={{ margin: '6px 0 2px' }} onClick={(e) => e.stopPropagation()}>
      <button onClick={preview} style={{
        ...btnBase,
        background: 'rgba(240,151,8,.12)', color: '#F09708',
        border: '1px solid rgba(240,151,8,.3)',
      }}>
        ⧉ Split trials
      </button>
      {error && (
        <span style={{ marginLeft: 8, fontSize: 10, color: '#f87171' }}>
          {error.slice(0, 60)}
        </span>
      )}
    </div>
  );
}

/** Inline treadmill toggle + belt-speed input. Stops event propagation so
 *  clicking fields inside this block doesn't bubble to the card's
 *  setActive handler. */
function TreadmillEditor({ dataset }: { dataset: Dataset }) {
  const setMeta = usePage((s) => s.setDatasetMeta);
  const isTM = !!(dataset as { is_treadmill?: boolean }).is_treadmill;
  const belt = (dataset as { belt_speed_ms?: number | null }).belt_speed_ms;
  const [local, setLocal] = useState<string>(belt == null ? '' : String(belt));

  useEffect(() => {
    setLocal(belt == null ? '' : String(belt));
  }, [belt]);

  return (
    <div className="ds-tags" onClick={(e) => e.stopPropagation()}
         style={{ paddingTop: 4 }}>
      <label className="ds-tag-ed" style={{
        cursor: 'pointer', background: isTM ? 'rgba(167,139,250,.14)' : 'transparent',
      }} title="Flag as treadmill data — stride_length then uses belt_speed × stride_time instead of ZUPT">
        <span className="ds-tag-lbl">treadmill</span>
        <input
          type="checkbox"
          checked={isTM}
          onChange={(e) => setMeta(dataset.id, { is_treadmill: e.target.checked })}
          style={{ margin: '0 4px', accentColor: '#A78BFA' }}
        />
      </label>
      {isTM && (
        <label className="ds-tag-ed set"
               title="Belt speed in m/s. Normal walking = 0.8~1.4 m/s. Clinical slow walking = 0.3~0.6 m/s.">
          <span className="ds-tag-lbl">belt m/s</span>
          <input
            className="ds-tag-inp"
            type="number"
            step="0.05"
            min="0"
            max="5"
            value={local}
            placeholder="1.0"
            onChange={(e) => setLocal(e.target.value)}
            onBlur={() => {
              const v = local.trim() === '' ? null : parseFloat(local);
              if (v === belt) return;
              setMeta(dataset.id, { belt_speed_ms: v } as Partial<Dataset>);
            }}
            style={{ width: 56 }}
          />
        </label>
      )}
    </div>
  );
}
