import { useWorkspace } from '../store/workspace';

const KEYS: Array<[string, string]> = [
  ['⌘K / Ctrl+K', 'Command palette'],
  ['?', 'Open this help'],
  ['Esc', 'Close modals / drawers'],
  ['Click graph ↗', 'Focus overlay'],
  ['Drag cell', 'Reorder (Phase B)'],
  ['Enter in LLM dock', 'Ask Claude'],
];

export default function HelpOverlay() {
  const open = useWorkspace((s) => s.helpOpen);
  const toggle = useWorkspace((s) => s.toggleHelp);
  if (!open) return null;

  return (
    <div className="cmdk-wrap open" onClick={(e) => { if (e.target === e.currentTarget) toggle(false); }}>
      <div className="cmdk" style={{ maxWidth: 560 }}>
        <div className="cmdk-input" style={{ borderBottom: '1px solid rgba(255,255,255,.06)' }}>
          <span style={{ color: '#F09708', fontSize: 18 }}>?</span>
          <h3 style={{ margin: 0, color: '#fff', font: '700 15px Pretendard, sans-serif' }}>Keyboard shortcuts</h3>
        </div>
        <div style={{ padding: 18 }}>
          {KEYS.map(([k, v]) => (
            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px dashed rgba(255,255,255,.06)', color: '#E2E8F0', fontSize: 13 }}>
              <span style={{ color: '#9CA3AF' }}>{v}</span>
              <kbd style={{ background: 'rgba(255,255,255,.06)', padding: '3px 8px', borderRadius: 5, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#F09708' }}>{k}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
