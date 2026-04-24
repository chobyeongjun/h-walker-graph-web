import { useState } from 'react';
import { usePage } from '../store/page';
import {
  FolderOpen, Play, FileText, CheckCircle2,
  Clipboard, ChevronLeft, FlaskConical, Clock,
  BarChart3, AlertCircle,
} from 'lucide-react';

export default function StudyPanel() {
  const [dir, setDir] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const discoverAndRunStudy = usePage((s) => s.discoverAndRunStudy);
  const studies = usePage((s) => s.studies);
  const studyResults = usePage((s) => s.studyResults);
  const showToast = usePage((s) => s.showToast);

  const selectedStudy = studies.find((s) => s.id === selectedStudyId);
  const selectedResult = selectedStudyId ? studyResults[selectedStudyId] : null;

  async function handleRun() {
    if (!dir.trim() || !name.trim() || busy) return;
    setBusy(true);
    try {
      await discoverAndRunStudy(dir.trim(), name.trim());
      showToast('✓ Study analysis complete!');
      setName('');
      setDir('');
    } catch (e) {
      showToast(`Error: ${(e as Error).message}`);
    }
    setBusy(false);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setCopied(true);
    showToast('Copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  }

  /* ── Report view ── */
  if (selectedStudyId && selectedResult) {
    return (
      <div style={S.wrap}>
        <button onClick={() => setSelectedStudyId(null)} style={S.backBtn}>
          <ChevronLeft size={14} /> Back to Studies
        </button>

        <div style={S.reportHeader}>
          <div style={S.reportIcon}><BarChart3 size={20} /></div>
          <div>
            <div style={S.reportTitle}>{selectedStudy?.name}</div>
            <div style={S.reportMeta}>
              {selectedResult.file_summaries.length} datasets · analysis complete
            </div>
          </div>
          <CheckCircle2 size={18} style={{ color: '#00FFB2', marginLeft: 'auto', flexShrink: 0 }} />
        </div>

        <div style={S.section}>
          <div style={S.sectionLabel}>Research Summary</div>
          <div style={S.reportBody}>
            {selectedResult.report_md
              .split('\n')
              .map((line, i) => {
                if (line.startsWith('# ')) return <div key={i} style={S.mdH1}>{line.slice(2)}</div>;
                if (line.startsWith('## ')) return <div key={i} style={S.mdH2}>{line.slice(3)}</div>;
                if (line.startsWith('### ')) return <div key={i} style={S.mdH3}>{line.slice(4)}</div>;
                if (line.startsWith('- ')) return <div key={i} style={S.mdLi}>· {line.slice(2)}</div>;
                if (line.startsWith('|')) return <div key={i} style={S.mdTable}>{line}</div>;
                if (line.trim() === '') return <div key={i} style={{ height: 8 }} />;
                return <div key={i} style={S.mdP}>{line}</div>;
              })}
          </div>
        </div>

        {selectedResult.report_latex && (
          <div style={S.section}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={S.sectionLabel}>LaTeX Table</div>
              <button onClick={() => copyToClipboard(selectedResult.report_latex!)} style={S.copyBtn}>
                <Clipboard size={12} />
                {copied ? 'Copied!' : 'Copy LaTeX'}
              </button>
            </div>
            <pre style={S.latexBlock}>{selectedResult.report_latex}</pre>
          </div>
        )}
      </div>
    );
  }

  /* ── Main view ── */
  return (
    <div style={S.wrap}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.headerIcon}><FlaskConical size={18} /></div>
        <div>
          <div style={S.headerTitle}>Batch Study</div>
          <div style={S.headerSub}>Analyze multiple datasets automatically</div>
        </div>
      </div>

      {/* Input form */}
      <div style={S.card}>
        <Field
          label="Study Name"
          placeholder="e.g. Pre-Post Analysis · S01"
          value={name}
          onChange={setName}
          icon={<FileText size={13} style={{ color: '#A78BFA' }} />}
        />
        <Field
          label="Data Directory"
          placeholder="/Users/name/data/study"
          value={dir}
          onChange={setDir}
          mono
          icon={<FolderOpen size={13} style={{ color: '#F09708' }} />}
        />
        <button
          onClick={handleRun}
          disabled={busy || !dir.trim() || !name.trim()}
          style={{
            ...S.runBtn,
            opacity: (busy || !dir.trim() || !name.trim()) ? 0.45 : 1,
            cursor: (busy || !dir.trim() || !name.trim()) ? 'not-allowed' : 'pointer',
          }}
        >
          {busy
            ? <><span style={S.spinner} />Analyzing…</>
            : <><Play size={14} fill="currentColor" />Run Batch Analysis</>}
        </button>
      </div>

      {/* Studies list */}
      <div style={S.section}>
        <div style={S.sectionLabel}>
          <Clock size={11} style={{ verticalAlign: 'middle', marginRight: 4 }} />
          Recent Studies
          {studies.length > 0 && (
            <span style={S.countBadge}>{studies.length}</span>
          )}
        </div>

        {studies.length === 0 ? (
          <div style={S.emptyState}>
            <AlertCircle size={28} style={{ color: 'rgba(161,161,170,0.35)', marginBottom: 10 }} />
            <div style={S.emptyTitle}>No studies yet</div>
            <div style={S.emptySub}>Set a directory and run batch analysis to get started.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {studies.map((s) => {
              const result = studyResults[s.id];
              return (
                <button
                  key={s.id}
                  onClick={() => setSelectedStudyId(s.id)}
                  style={S.studyCard}
                >
                  <div style={S.studyCardTop}>
                    <span style={S.studyName}>{s.name}</span>
                    {result
                      ? <CheckCircle2 size={14} style={{ color: '#00FFB2', flexShrink: 0 }} />
                      : <span style={S.pendingDot} />}
                  </div>
                  <div style={S.studyCardBot}>
                    <span style={S.studyMeta}><FileText size={10} style={{ verticalAlign: 'middle' }} /> {s.files.length} files</span>
                    {result && <span style={S.viewHint}>View report →</span>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label, placeholder, value, onChange, mono = false, icon,
}: {
  label: string; placeholder: string; value: string;
  onChange: (v: string) => void; mono?: boolean; icon?: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={S.fieldLabel}>
        {icon && <span style={{ marginRight: 5 }}>{icon}</span>}
        {label}
      </label>
      <input
        style={{ ...S.input, fontFamily: mono ? "'JetBrains Mono', monospace" : 'inherit' }}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
    </div>
  );
}

/* ── Styles ── */
const S: Record<string, React.CSSProperties> = {
  wrap: {
    display: 'flex', flexDirection: 'column', gap: 0,
    padding: '20px 16px', overflowY: 'auto', height: '100%',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex', alignItems: 'center', gap: 12,
    marginBottom: 18,
  },
  headerIcon: {
    width: 36, height: 36, borderRadius: 10, flexShrink: 0,
    background: 'rgba(167,139,250,0.15)',
    border: '1px solid rgba(167,139,250,0.25)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#A78BFA',
  },
  headerTitle: {
    font: '700 14px/1.2 Pretendard, sans-serif',
    color: '#E2E8F0', letterSpacing: '-0.01em',
  },
  headerSub: {
    font: '500 11px/1.3 Pretendard, sans-serif',
    color: '#6B7280', marginTop: 2,
  },
  card: {
    background: 'rgba(23,27,94,0.35)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 12, padding: '16px 14px', marginBottom: 20,
  },
  fieldLabel: {
    display: 'flex', alignItems: 'center',
    font: '600 10.5px/1 JetBrains Mono, monospace',
    color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.1em',
    marginBottom: 7,
  },
  input: {
    width: '100%', background: 'rgba(11,14,46,0.6)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 8, padding: '9px 11px',
    font: '500 12.5px/1 Pretendard, sans-serif', color: '#E2E8F0',
    outline: 'none', transition: 'border-color .15s',
    boxSizing: 'border-box',
  },
  runBtn: {
    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 7, padding: '11px 16px', borderRadius: 9,
    background: 'linear-gradient(135deg, #A78BFA 0%, #7C3AED 100%)',
    color: '#fff', font: '700 12.5px/1 Pretendard, sans-serif',
    letterSpacing: '0.03em', border: 'none',
    boxShadow: '0 4px 20px rgba(124,58,237,0.35)',
    transition: 'all .15s',
    marginTop: 4,
  },
  spinner: {
    display: 'inline-block', width: 13, height: 13,
    border: '2px solid rgba(255,255,255,0.25)',
    borderTopColor: '#fff', borderRadius: '50%',
    animation: 'spin .7s linear infinite',
  },
  section: {
    marginBottom: 16,
  },
  sectionLabel: {
    font: '700 10px/1 JetBrains Mono, monospace',
    color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.14em',
    marginBottom: 10,
    display: 'flex', alignItems: 'center',
  },
  countBadge: {
    marginLeft: 7, background: 'rgba(167,139,250,0.2)',
    color: '#A78BFA', font: '700 9px/1 JetBrains Mono, monospace',
    padding: '2px 6px', borderRadius: 10,
  },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '32px 16px', textAlign: 'center',
    border: '1px dashed rgba(255,255,255,0.07)',
    borderRadius: 10, background: 'rgba(11,14,46,0.2)',
  },
  emptyTitle: {
    font: '600 12.5px/1 Pretendard, sans-serif', color: '#4B5563',
  },
  emptySub: {
    font: '500 11px/1.5 Pretendard, sans-serif', color: '#374151',
    marginTop: 6, maxWidth: 200,
  },
  studyCard: {
    width: '100%', textAlign: 'left', padding: '11px 13px',
    background: 'rgba(23,27,94,0.3)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 10, cursor: 'pointer',
    transition: 'border-color .15s, background .15s',
    outline: 'none',
  },
  studyCardTop: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: 8, marginBottom: 5,
  },
  studyName: {
    font: '600 12.5px/1.3 Pretendard, sans-serif', color: '#E2E8F0',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
    flex: 1,
  },
  studyCardBot: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  studyMeta: {
    font: '500 10.5px/1 JetBrains Mono, monospace', color: '#6B7280',
    display: 'flex', alignItems: 'center', gap: 4,
  },
  viewHint: {
    font: '600 10px/1 Pretendard, sans-serif', color: '#A78BFA',
    opacity: 0.8,
  },
  pendingDot: {
    width: 7, height: 7, borderRadius: '50%',
    background: '#F09708', flexShrink: 0,
    animation: 'pulse 1.5s ease-in-out infinite',
  },
  // Report view
  backBtn: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    font: '600 11px/1 Pretendard, sans-serif', color: '#6B7280',
    cursor: 'pointer', border: 'none', background: 'none',
    padding: '4px 0', marginBottom: 18,
    transition: 'color .12s',
  },
  reportHeader: {
    display: 'flex', alignItems: 'center', gap: 12,
    background: 'rgba(23,27,94,0.4)', border: '1px solid rgba(0,255,178,0.12)',
    borderRadius: 12, padding: '14px 14px', marginBottom: 20,
  },
  reportIcon: {
    width: 40, height: 40, borderRadius: 10, flexShrink: 0,
    background: 'rgba(0,255,178,0.1)',
    border: '1px solid rgba(0,255,178,0.2)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#00FFB2',
  },
  reportTitle: {
    font: '700 14px/1.2 Pretendard, sans-serif',
    color: '#E2E8F0', letterSpacing: '-0.01em',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
    maxWidth: 160,
  },
  reportMeta: {
    font: '500 11px/1 Pretendard, sans-serif',
    color: '#6B7280', marginTop: 4,
  },
  reportBody: {
    background: 'rgba(11,14,46,0.5)', border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 10, padding: '14px', maxHeight: 320, overflowY: 'auto',
  },
  mdH1: { font: '800 15px/1.4 Pretendard, sans-serif', color: '#F09708', marginBottom: 8 },
  mdH2: { font: '700 13px/1.4 Pretendard, sans-serif', color: '#A78BFA', marginBottom: 6, marginTop: 10 },
  mdH3: { font: '600 12px/1.4 Pretendard, sans-serif', color: '#E2E8F0', marginBottom: 4, marginTop: 8 },
  mdLi: { font: '500 11.5px/1.6 Pretendard, sans-serif', color: '#D1D5DB', paddingLeft: 4 },
  mdTable: { font: '500 10.5px/1.8 JetBrains Mono, monospace', color: '#9CA3AF', overflowX: 'auto', whiteSpace: 'pre' },
  mdP: { font: '500 11.5px/1.6 Pretendard, sans-serif', color: '#9CA3AF' },
  copyBtn: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    font: '700 10px/1 JetBrains Mono, monospace', color: '#A78BFA',
    letterSpacing: '0.08em', textTransform: 'uppercase',
    background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)',
    borderRadius: 6, padding: '5px 10px', cursor: 'pointer',
    transition: 'background .12s',
  },
  latexBlock: {
    background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 8, padding: '12px', margin: 0,
    font: '500 10.5px/1.6 JetBrains Mono, monospace', color: '#9CA3AF',
    overflowX: 'auto', whiteSpace: 'pre', maxHeight: 240, overflowY: 'auto',
  },
};
