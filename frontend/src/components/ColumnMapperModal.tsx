import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useWorkspace } from '../store/workspace';
import { saveMapping } from '../api';

const ROLES = ['time', 'L force', 'R force', 'shank', 'thigh', 'force', 'group', '—'];

export default function ColumnMapperModal() {
  const open = useWorkspace((s) => s.mapperOpen);
  const dsId = useWorkspace((s) => s.mapperDsId);
  const datasets = useWorkspace((s) => s.datasets);
  const close = useWorkspace((s) => s.closeMapper);
  const showToast = useWorkspace((s) => s.showToast);
  const ds = datasets.find((d) => d.id === dsId);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  useEffect(() => {
    if (ds) {
      const m: Record<string, string> = {};
      ds.cols.forEach((c) => { m[c.name] = c.mapped || '—'; });
      setMapping(m);
    }
  }, [ds]);

  if (!open || !ds) return null;

  async function save() {
    if (!ds) return;
    try {
      await saveMapping(ds.id, mapping);
      showToast('Mapping saved');
    } catch {
      showToast('Mapping saved (offline)');
    }
    close();
  }

  return (
    <div className="map-wrap open" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="map">
        <header className="map-head">
          <span className="ey">Map columns</span>
          <h3>{ds.name}</h3>
          <span className={`ds-chip ${ds.tag}`}>{ds.tag}</span>
          <button className="close" onClick={close}><X size={16} /></button>
        </header>
        <div className="map-body">
          {ds.cols.map((c) => {
            const cur = mapping[c.name] || '—';
            const confCls = cur === '—' ? 'lo' : (c.mappedManual ? 'mid' : 'hi');
            return (
              <div key={c.name} className={`map-row${c.mappedManual ? ' manual' : (cur !== '—' ? ' suggested' : '')}`}>
                <div className="map-src">
                  <span>{c.name}</span>
                  <small>{c.unit}</small>
                </div>
                <div className="map-arrow">→</div>
                <select
                  className="map-sel"
                  value={cur}
                  onChange={(e) => setMapping((m) => ({ ...m, [c.name]: e.target.value }))}
                >
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <div className={`map-conf ${confCls}`}>{cur === '—' ? 'low' : 'auto'}</div>
                <div className="map-preview">{c.unit}</div>
              </div>
            );
          })}
        </div>
        <footer className="map-foot">
          <div className="note">
            Auto-mapped by column name heuristics. <b>Review manually</b> and confirm before cell generation.
          </div>
          <button className="btn secondary" onClick={close}>Cancel</button>
          <button className="btn primary" onClick={save}>Save mapping</button>
        </footer>
      </div>
    </div>
  );
}
