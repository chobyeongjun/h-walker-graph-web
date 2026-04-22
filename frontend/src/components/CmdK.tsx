import { useMemo, useState, useEffect, useRef } from 'react';
import { useWorkspace } from '../store/workspace';
import { STATS_LIB } from '../data/catalogs';
import { GRAPH_TPLS } from '../data/graphTemplates';
import { COMPUTE_METRICS } from '../data/computeMetrics';
import { BarChart3, LineChart, Table2, Sparkles } from 'lucide-react';

interface Action {
  id: string;
  label: string;
  section: string;
  icon?: React.ReactNode;
  run: () => void;
}

export default function CmdK() {
  const open = useWorkspace((s) => s.cmdkOpen);
  const toggle = useWorkspace((s) => s.toggleCmdK);
  const addCell = useWorkspace((s) => s.addCell);
  const openDrawer = useWorkspace((s) => s.openDrawer);
  const setMode = useWorkspace((s) => s.setMode);
  const [q, setQ] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const actions = useMemo<Action[]>(() => {
    const list: Action[] = [];
    Object.entries(GRAPH_TPLS).forEach(([k, v]) => {
      list.push({
        id: 'graph-' + k, label: `Add graph: ${v.title}`, section: 'Graphs',
        icon: <LineChart size={14} />,
        run: () => {
          addCell({ id: 'c' + Date.now(), type: 'graph', graph: k, dsIds: [v.ds] });
          toggle(false);
        },
      });
    });
    STATS_LIB.forEach((s) => {
      list.push({
        id: 'stat-' + s.op, label: `Add stat: ${s.name}`, section: 'Stats',
        icon: <BarChart3 size={14} />,
        run: () => {
          addCell({
            id: 'c' + Date.now(), type: 'stat', op: s.op, dsIds: [],
            fmt: 'apa', inputs: { a: '', b: '' },
          });
          toggle(false);
        },
      });
    });
    Object.entries(COMPUTE_METRICS).forEach(([k, v]) => {
      list.push({
        id: 'compute-' + k, label: `Add compute: ${v.label}`, section: 'Compute',
        icon: <Table2 size={14} />,
        run: () => {
          addCell({ id: 'c' + Date.now(), type: 'compute', metric: k, dsIds: [] });
          toggle(false);
        },
      });
    });
    list.push({ id: 'mode-quick', label: 'Switch to Quick mode', section: 'Mode', run: () => { setMode('quick'); toggle(false); } });
    list.push({ id: 'mode-pub', label: 'Switch to Publication mode', section: 'Mode', run: () => { setMode('pub'); toggle(false); } });
    list.push({ id: 'drw-hist', label: 'Open history', section: 'Drawers', icon: <Sparkles size={14} />, run: () => { openDrawer('history'); toggle(false); } });
    list.push({ id: 'drw-exp', label: 'Open exports', section: 'Drawers', icon: <Sparkles size={14} />, run: () => { openDrawer('exports'); toggle(false); } });
    list.push({ id: 'drw-stats', label: 'Open stats library', section: 'Drawers', icon: <Sparkles size={14} />, run: () => { openDrawer('stats'); toggle(false); } });
    return list;
  }, [addCell, openDrawer, setMode, toggle]);

  const filtered = useMemo(() => {
    if (!q) return actions;
    const lq = q.toLowerCase();
    return actions.filter((a) => a.label.toLowerCase().includes(lq) || a.section.toLowerCase().includes(lq));
  }, [q, actions]);

  useEffect(() => { if (open) { setQ(''); setCursor(0); setTimeout(() => inputRef.current?.focus(), 50); } }, [open]);
  useEffect(() => { setCursor(0); }, [q]);

  if (!open) return null;

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') { setCursor((c) => Math.min(c + 1, filtered.length - 1)); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { setCursor((c) => Math.max(c - 1, 0)); e.preventDefault(); }
    else if (e.key === 'Enter') { filtered[cursor]?.run(); }
  }

  const sections: Record<string, Action[]> = {};
  filtered.forEach((a) => { (sections[a.section] ||= []).push(a); });

  return (
    <div className="cmdk-wrap open" onClick={(e) => { if (e.target === e.currentTarget) toggle(false); }}>
      <div className="cmdk" onKeyDown={onKey}>
        <div className="cmdk-input">
          <span style={{ color: '#F09708', fontSize: 18 }}>⌘</span>
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search commands, add cells…" />
        </div>
        <div className="cmdk-list">
          {Object.entries(sections).map(([section, items]) => (
            <div key={section}>
              <div className="cmdk-section">{section}</div>
              {items.map((a) => {
                const idx = filtered.indexOf(a);
                return (
                  <div
                    key={a.id}
                    className="cmdk-item"
                    data-active={idx === cursor}
                    onMouseEnter={() => setCursor(idx)}
                    onClick={() => a.run()}
                  >
                    <span className="cmdk-icon">{a.icon || '•'}</span>
                    <span>{a.label}</span>
                    <span className="cmdk-meta">{a.id}</span>
                  </div>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{ padding: 24, color: '#6B7280', fontSize: 13 }}>No commands match.</div>
          )}
        </div>
        <footer className="cmdk-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>⏎</kbd> run</span>
          <span><kbd>esc</kbd> close</span>
        </footer>
      </div>
    </div>
  );
}
