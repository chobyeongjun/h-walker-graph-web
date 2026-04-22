import { useEffect } from 'react';
import { useWorkspace } from './store/workspace';
import TopNav from './components/TopNav';
import Sidebar from './components/Sidebar';
import PublicationBar from './components/PublicationBar';
import Canvas from './components/Canvas';
import LlmDock from './components/LlmDock';
import FocusOverlay from './components/FocusOverlay';
import ColumnMapperModal from './components/ColumnMapperModal';
import Drawer from './components/Drawer';
import Toast from './components/Toast';

export default function App() {
  const closeDrawer = useWorkspace((s) => s.closeDrawer);
  const closeMapper = useWorkspace((s) => s.closeMapper);
  const focusCell = useWorkspace((s) => s.focusCell);

  // Always use publication styling; body class kept for CSS hooks.
  useEffect(() => {
    document.body.classList.add('pub');
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        closeDrawer();
        closeMapper();
        focusCell(null);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closeDrawer, closeMapper, focusCell]);

  return (
    <div className="app">
      <TopNav />
      <Sidebar />
      <div style={{ gridColumn: 2, gridRow: '2 / 3', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <PublicationBar />
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
      <ColumnMapperModal />
      <Drawer />
      <Toast />
    </div>
  );
}
