import { useEffect } from 'react';
import { useWorkspace } from './store/workspace';
import TopNav from './components/TopNav';
import Sidebar from './components/Sidebar';
import PublicationBar from './components/PublicationBar';
import Canvas from './components/Canvas';
import LlmDock from './components/LlmDock';
import FocusOverlay from './components/FocusOverlay';
import CmdK from './components/CmdK';
import ColumnMapperModal from './components/ColumnMapperModal';
import Drawer from './components/Drawer';
import HelpOverlay from './components/HelpOverlay';
import Toast from './components/Toast';

export default function App() {
  const mode = useWorkspace((s) => s.mode);
  const toggleCmdK = useWorkspace((s) => s.toggleCmdK);
  const toggleHelp = useWorkspace((s) => s.toggleHelp);
  const closeDrawer = useWorkspace((s) => s.closeDrawer);
  const closeMapper = useWorkspace((s) => s.closeMapper);
  const focusCell = useWorkspace((s) => s.focusCell);

  // Publication-mode body class + global keyboard shortcuts
  useEffect(() => {
    document.body.classList.toggle('pub', mode === 'pub');
  }, [mode]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        toggleCmdK();
      } else if (e.key === '?' && !(e.target as HTMLElement).matches?.('input, textarea, [contenteditable]')) {
        e.preventDefault();
        toggleHelp();
      } else if (e.key === 'Escape') {
        closeDrawer();
        closeMapper();
        focusCell(null);
        toggleCmdK(false);
        toggleHelp(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleCmdK, toggleHelp, closeDrawer, closeMapper, focusCell]);

  return (
    <div className="app">
      <TopNav />
      <Sidebar />
      <div style={{ gridColumn: 2, gridRow: '2 / 3', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {mode === 'pub' && <PublicationBar />}
        <Canvas />
      </div>
      <div style={{ gridColumn: 2, gridRow: '3 / 4' }}>
        <LlmDock />
      </div>
      <div className="footer">
        <span>H-WALKER CORE · v3</span>
        <span>PRETENDARD · JETBRAINS MONO</span>
      </div>
      <FocusOverlay />
      <CmdK />
      <ColumnMapperModal />
      <Drawer />
      <HelpOverlay />
      <Toast />
    </div>
  );
}
