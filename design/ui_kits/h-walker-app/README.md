# H-Walker Web App — UI Kit

A pixel-close recreation of the current 3-panel shell (TopNav · LeftPanel · GraphCanvas · AIPanel) plus a preview of the **redesign target**: a card-grid "Paper Studio" dashboard.

## Files
- `index.html` — interactive demo: type a request, watch a skeleton card resolve into a plotted Figure.
- `components.jsx` — all small JSX components (TopNav, Sidebar, Composer, GraphCard, InsightChips, etc.)
- `screens.jsx` — the two top-level screens: `<LegacyShell/>` (current 3-panel) and `<PaperStudio/>` (redesign target dashboard).

## Recreated from
`frontend/src/App.tsx`, `LeftPanel.tsx`, `AIPanel.tsx`, `GraphCanvas.tsx`, `InsightCard.tsx`, `DrivePanel.tsx`.
