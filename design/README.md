# H-Walker Design Artifacts

This folder contains all design mockups + the Claude Code handoff doc for the
**H-Walker CORE** biomechanics analysis workspace.

## Start here

- **[HANDOFF_CLAUDE_CODE.md](./HANDOFF_CLAUDE_CODE.md)** — Copy-paste commands
  for Claude Code. React component tree, FastAPI contract, library pinning,
  visual-fidelity checklist.
- **[phase2/core_v3.html](./phase2/core_v3.html)** — Main mockup. Open in a
  browser. This is what the ported React app should look and feel like.

## File map

```
design/
├── HANDOFF_CLAUDE_CODE.md      ← start here (porting instructions)
├── README.md                   ← original design-system readme
├── colors_and_type.css         ← design tokens (--accent, fonts, etc.)
│
├── phase1/
│   └── core.html               ← landing / dataset upload screen
│
├── phase2/
│   ├── core.html               ← v1 (basic analysis workspace)
│   ├── core_v2.html            ← v2 (+ publication mode, recipes)
│   ├── core_v3.html            ← v3 (+ compute cells, drawers, real Claude) ★ current
│   ├── app.js / app_v2.js      ← extracted scripts (core_v3 is self-contained)
│   └── journal_presets.js      ← IEEE / Nature / APA / Elsevier / MDPI specs
│
├── preview/                    ← design-system preview pages
│   ├── colors-core.html
│   ├── type-scale.html
│   ├── components-*.html       ← button, input, chat, graph-card, etc.
│   └── ...
│
├── ui_kits/                    ← imported component references
├── fonts/                      ← Pretendard + JetBrains Mono
└── assets/                     ← favicon, logos
```

## How to use

### 1. View the design
Open `phase2/core_v3.html` in your browser.

### 2. Port to your React app
Open `HANDOFF_CLAUDE_CODE.md` and paste the commands from §3 into Claude Code
one at a time.

### 3. Reference the design system
Open any file in `preview/` to see isolated components (buttons, inputs,
typography, colors, etc.).

## Notes

- `core_v3.html` is a self-contained 2900-line single HTML file. It uses
  `window.claude.complete` for LLM calls — in the React port this becomes
  a `/api/claude/complete` FastAPI route (see handoff doc §2.6).
- The design uses hand-rolled SVG charts, **not** Recharts/Plotly. This is
  intentional — journal presets require exact mm widths / DPI / palettes.
- All state in the mockup is ephemeral (in-memory + localStorage for autosave).
  The React port should use Zustand + a backend (see handoff doc §1).
