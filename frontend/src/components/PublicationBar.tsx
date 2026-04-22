import { useWorkspace } from '../store/workspace';
import { JOURNAL_PRESETS } from '../data/journalPresets';

export default function PublicationBar() {
  const preset = useWorkspace((s) => s.globalPreset);
  const setPreset = useWorkspace((s) => s.setGlobalPreset);
  const P = JOURNAL_PRESETS[preset];

  return (
    <div className="pubbar">
      <div className="pubbar-inner">
        <div className="pubbar-label">
          <div className="pubbar-eyebrow">Publication preset</div>
          <div className="pubbar-title">{P?.full || P?.name || '—'}</div>
        </div>
        <div className="pubbar-tabs">
          {Object.entries(JOURNAL_PRESETS).map(([k, v]) => (
            <button
              key={k}
              className={`pubbar-tab${preset === k ? ' active' : ''}`}
              onClick={() => setPreset(k)}
            >
              {v.name}
            </button>
          ))}
        </div>
        <div className="pubbar-spec">
          <div className="spec-item">
            <span className="spec-k">2-col</span>
            <span className="spec-v">{P?.col2.w}mm</span>
          </div>
          <div className="spec-item">
            <span className="spec-k">Body</span>
            <span className="spec-v">{P?.sizes.body}pt {P?.font}</span>
          </div>
          <div className="spec-item">
            <span className="spec-k">DPI</span>
            <span className="spec-v">{P?.dpi}</span>
          </div>
          <div className="spec-item spec-swatch">
            <span className="spec-k">Palette</span>
            <span className="palette-chips">
              {P?.palette.slice(0, 6).map((c, i) => (
                <span key={i} className="pchip" style={{ background: c }} />
              ))}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
