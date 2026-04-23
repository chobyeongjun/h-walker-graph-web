import { useEffect, useMemo, useRef, useState } from 'react';
import { Link2, Trash2 } from 'lucide-react';
import { usePage, type Dataset } from '../store/page';
import { CANONICAL_RECIPES } from '../data/canonicalRecipes';
import { uploadDataset, deleteDataset as apiDeleteDataset, syncAlign } from '../api';

export default function DatasetPanel() {
  const datasets = usePage((s) => s.datasets);
  const setActive = usePage((s) => s.setActiveDataset);
  const applyRecipes = usePage((s) => s.applyRecipes);
  const toggleRecipe = usePage((s) => s.toggleRecipe);
  const addDataset = usePage((s) => s.addDataset);
  const removeDataset = usePage((s) => s.removeDataset);
  const setDatasetMeta = usePage((s) => s.setDatasetMeta);
  const showToast = usePage((s) => s.showToast);
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const active = datasets.find((d) => d.active) || datasets[0];
  const recipes = active ? CANONICAL_RECIPES[active.kind] || CANONICAL_RECIPES.force : [];

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    let accepted = 0;
    let skipped: string[] = [];
    for (const f of Array.from(files)) {
      // Accept anything whose name ends with .csv (case-insensitive) OR
      // has no recognisable extension (e.g. `foo` — try upload, backend
      // will 422 if it's not a CSV). This catches `.CSV`, `foo.csv (1)`,
      // and Finder-rename quirks that dropped the extension.
      const n = f.name.toLowerCase();
      const looksCsv = /\.csv(\b|$|\s|\.)/.test(n) || !/\.\w+$/.test(n);
      if (!looksCsv) {
        skipped.push(f.name);
        continue;
      }
      try {
        const ds = await uploadDataset(f);
        addDataset(ds);
        setActive(ds.id);
        showToast(`Uploaded ${f.name} · running default recipes…`);
        // Auto-apply default recipes — the "one-click" flow
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

  // Phase 3 · cross-source sync detection
  const syncStatus = useMemo(() => {
    const unsynced = datasets.filter((d) => !('synced_from' in d) || !d.synced_from);
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

      {datasets.length === 0 && (
        <div className="ds-empty">
          <div className="ds-empty-title">No datasets yet</div>
          <div className="ds-empty-sub">
            Drop a CSV below to get started — default recipe auto-runs and
            fills the canvas with graphs + metrics for the active journal
            preset.
          </div>
        </div>
      )}

      <div className="ds-grid">
        {datasets.map((d) => (
          <div
            key={d.id}
            className={`ds-card${d.active ? ' active' : ''}`}
            onClick={() => setActive(d.id)}
          >
            <div className="ds-row1">
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

      {recipes.length > 0 && active && (
        <AutoRecipes
          recipes={recipes}
          active={active}
          onToggle={(id) => toggleRecipe(active.id, id)}
          onApply={() => applyRecipes(active.id)}
        />
      )}
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

/**
 * AutoRecipes · Phase 2I
 *
 * Replaces the old checkbox grid. Compute metrics auto-run (they're just
 * numbers, no user choice needed). Graphs show only the currently-enabled
 * set in a compact chip strip; the user can toggle extras from a
 * "+ more graphs" expandable section. "Apply" button re-runs the active
 * set (skip duplicates thanks to dedup in page.applyRecipes).
 */
function AutoRecipes({ recipes, active, onToggle, onApply }: {
  recipes: Array<{ id: string; label: string; default: boolean; type: 'graph' | 'compute'; hint?: string }>;
  active: { id: string; kind: string; recipeState: Record<string, boolean>; analyzing?: boolean };
  onToggle: (id: string) => void;
  onApply: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const graphs = recipes.filter((r) => r.type === 'graph');
  const computes = recipes.filter((r) => r.type === 'compute');
  const enabledGraph = graphs.filter((r) => active.recipeState[r.id] ?? r.default);
  const disabledGraph = graphs.filter((r) => !(active.recipeState[r.id] ?? r.default));

  return (
    <div className="recipes" style={{ margin: '0 12px 12px' }}>
      <div className="recipes-head">
        <h4>Auto-analysis · {active.kind}</h4>
        <span className="sub">
          {computes.length} metrics run automatically · {enabledGraph.length} graphs enabled
        </span>
        <button
          className="apply"
          onClick={onApply}
          disabled={active.analyzing}
        >
          {active.analyzing ? 'Analyzing…' : 'Run on this dataset'}
        </button>
      </div>

      <div className="auto-summary">
        <span className="auto-lbl">Graphs</span>
        {enabledGraph.map((r) => (
          <button
            key={r.id}
            className="auto-chip on"
            title={r.hint || r.label}
            onClick={() => onToggle(r.id)}
          >
            {r.label}
            <span className="auto-x">×</span>
          </button>
        ))}
        {disabledGraph.length > 0 && (
          <button
            className="auto-more"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? '− hide' : `+ ${disabledGraph.length} more`}
          </button>
        )}
      </div>

      {expanded && (
        <div className="auto-advanced">
          {disabledGraph.map((r) => (
            <button
              key={r.id}
              className="auto-chip off"
              title={r.hint || r.label}
              onClick={() => onToggle(r.id)}
            >
              + {r.label}
            </button>
          ))}
        </div>
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
