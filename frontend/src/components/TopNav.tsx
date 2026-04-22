import { useEffect, useState } from 'react';
import { useWorkspace } from '../store/workspace';

/** Dark/light auto-detect. User can override via settings drawer (future). */
function useColorScheme(): 'dark' | 'light' {
  const [scheme, setScheme] = useState<'dark' | 'light'>(() =>
    window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark',
  );
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const on = () => setScheme(mq.matches ? 'light' : 'dark');
    mq.addEventListener?.('change', on);
    return () => mq.removeEventListener?.('change', on);
  }, []);
  return scheme;
}

export default function TopNav() {
  const mode = useWorkspace((s) => s.mode);
  const setMode = useWorkspace((s) => s.setMode);
  const toggleCmdK = useWorkspace((s) => s.toggleCmdK);
  const scheme = useColorScheme();

  // In publication mode the canvas goes white — use the light wordmark then too.
  const useLightWordmark = scheme === 'light' || mode === 'pub';
  const wordmark = useLightWordmark
    ? '/brand/wordmark-light.svg'
    : '/brand/wordmark-dark.svg';

  return (
    <nav className="topnav">
      <a className="brand" href="/" aria-label="H-Walker CORE home">
        <img src={wordmark} alt="H-Walker CORE" height={36} />
      </a>

      <div className="nav-spacer" />

      <div className="nav-pill">
        <span className="dot" />
        <span>Claude Haiku 4.5</span>
        <small>ready</small>
      </div>

      <button className="kbd" onClick={() => toggleCmdK(true)} title="Command palette">
        <kbd>⌘</kbd><kbd>K</kbd>
        <span>Search & act</span>
      </button>

      <div className="mode-toggle">
        <button className={mode === 'quick' ? 'on' : ''} onClick={() => setMode('quick')}>QUICK</button>
        <button className={mode === 'pub' ? 'on' : ''} onClick={() => setMode('pub')}>PUBLICATION</button>
      </div>
    </nav>
  );
}
