import { useState } from 'react';
import { usePage } from '../store/page';
import { Folder, Play, FileText, CheckCircle2, Clipboard, ChevronLeft } from 'lucide-react';

export default function StudyPanel() {
  const [dir, setDir] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  
  const discoverAndRunStudy = usePage((s) => s.discoverAndRunStudy);
  const studies = usePage((s) => s.studies);
  const studyResults = usePage((s) => s.studyResults);
  const showToast = usePage((s) => s.showToast);

  const selectedStudy = studies.find(s => s.id === selectedStudyId);
  const selectedResult = selectedStudyId ? studyResults[selectedStudyId] : null;

  async function handleRun() {
    if (!dir || !name) return;
    setBusy(true);
    try {
      await discoverAndRunStudy(dir, name);
      showToast('Study analysis complete!');
    } catch (e) {
      showToast(`Error: ${(e as Error).message}`);
    }
    setBusy(false);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!');
  }

  if (selectedStudyId && selectedResult) {
    return (
      <div className="drawer-inner p-4 overflow-y-auto max-h-screen">
        <button 
          onClick={() => setSelectedStudyId(null)}
          className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white mb-4 transition-colors"
        >
          <ChevronLeft size={14} /> Back to Studies
        </button>
        
        <header className="mb-6">
          <h2 className="text-xl font-bold text-white">{selectedStudy?.name}</h2>
          <div className="text-xs text-zinc-500 mt-1">{selectedResult.file_summaries.length} datasets analyzed</div>
        </header>

        <section className="space-y-6">
          <div className="prose prose-invert prose-sm max-w-none">
             <div className="text-zinc-200 whitespace-pre-wrap font-sans text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: selectedResult.report_md.replace(/\n/g, '<br/>') }} />
          </div>

          {selectedResult.report_latex && (
            <div className="space-y-2 mt-8">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Journal LaTeX Table</h4>
                <button 
                  onClick={() => copyToClipboard(selectedResult.report_latex!)}
                  className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-widest"
                >
                  <Clipboard size={12} /> Copy LaTeX
                </button>
              </div>
              <pre className="bg-black/40 border border-zinc-800 p-3 rounded-md text-[10px] text-zinc-400 font-mono overflow-x-auto">
                {selectedResult.report_latex}
              </pre>
            </div>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="drawer-inner p-4">
      <header className="flex items-center gap-2 mb-6">
        <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
          <Folder size={20} />
        </div>
        <h2 className="text-lg font-semibold">Study Management</h2>
      </header>

      <section className="space-y-4 mb-8">
        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Study Name</label>
          <input
            type="text"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
            placeholder="e.g. Pilot Study 01"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Local Directory</label>
          <input
            type="text"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:border-indigo-500"
            placeholder="/Users/name/data/study1"
            value={dir}
            onChange={(e) => setDir(e.target.value)}
          />
        </div>
        <button
          onClick={handleRun}
          disabled={busy || !dir || !name}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2 rounded-md flex items-center justify-center gap-2 transition-colors font-medium"
        >
          {busy ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/20 border-t-white" /> : <Play size={16} />}
          {busy ? 'Processing Study...' : 'Run Batch Analysis'}
        </button>
      </section>

      <section className="space-y-4">
        <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Recent Studies</h3>
        {studies.length === 0 && (
          <div className="text-center py-8 border border-dashed border-zinc-800 rounded-lg text-zinc-500 text-sm">
            No studies run yet
          </div>
        )}
        <div className="space-y-3">
          {studies.map((s) => (
            <div 
              key={s.id} 
              onClick={() => setSelectedStudyId(s.id)}
              className="bg-zinc-900/50 border border-zinc-800 p-3 rounded-lg group cursor-pointer hover:border-indigo-500/50 hover:bg-zinc-900 transition-all"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-zinc-200 group-hover:text-indigo-400">{s.name}</span>
                {studyResults[s.id] && <CheckCircle2 size={14} className="text-emerald-500" />}
              </div>
              <div className="flex items-center gap-3 text-[10px] text-zinc-500">
                <span className="flex items-center gap-1"><FileText size={10} /> {s.files.length} files</span>
                <span className="opacity-0 group-hover:opacity-100 transition-opacity">Click to view report →</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
