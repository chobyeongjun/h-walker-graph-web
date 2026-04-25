import { useEffect, useState } from 'react';

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
  const scheme = useColorScheme();
  // Wordmark follows the system color scheme only — no "publication mode" flip.
  const wordmark = scheme === 'light'
    ? '/brand/wordmark-light.svg'
    : '/brand/wordmark-dark.svg';

  return (
    <nav className="topnav">
      <a className="brand" href="/" aria-label="H-Walker CORE home">
        <img src={wordmark} alt="H-Walker CORE" height={36} />
      </a>

      <div className="nav-spacer" />

      <div className="nav-pill" title="Click-driven Library + per-sync Inspector. No LLM, no chat, no fake data.">
        <span className="dot" />
        <span>Local engine</span>
        <small>ready</small>
      </div>
    </nav>
  );
}
