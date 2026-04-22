# H-Walker Graph Web

케이블 드리븐 보행 재활 로봇 **H-Walker** 실험 데이터용 자연어 분석·시각화 데스크톱 웹앱.
CSV 업로드 → 자연어 요청 → 인터랙티브 그래프 + 논문용 SVG/PNG export 까지 한 곳에서.

## Stack

- **Frontend**: React 18 + TypeScript + Vite + Tailwind + Plotly.js + Zustand
- **Backend**: FastAPI + pandas + matplotlib
- **LLM**: Claude Haiku 4.5 (Anthropic API) — 자연어 → `AnalysisRequest` 파싱
- **Optional**: Google Drive 연동, Ollama fallback

## 🚀 완전히 빈 컴퓨터에서 설치

상세 가이드: **[SETUP.md](./SETUP.md)** 참고. 요약:

```bash
# 1. 툴 설치 (한 번만)
brew install python@3.13 node git          # Mac
# 또는 apt install python3 python3-pip nodejs npm git  # Linux/WSL

# 2. API 키
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 3. 클론 + 설치 + 실행
git clone https://github.com/chobyeongjun/h-walker-graph-web.git
cd h-walker-graph-web
pip3 install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
python3 run.py
# → http://localhost:8000 자동으로 열림
```

## Quick Start

```bash
# 1) Python deps
pip install -r requirements.txt  # or: fastapi uvicorn pandas matplotlib anthropic ollama

# 2) Frontend build (최초 1회)
cd frontend
npm install
npm run build
cd ..

# 3) Run
export ANTHROPIC_API_KEY=sk-ant-...
python3 run.py
# → http://localhost:8000
```

## Frontend Dev (hot reload)

```bash
cd frontend
npm run dev   # http://localhost:5173
# 백엔드는 별도 터미널에서 python3 run.py
```

## Project Layout

```
frontend/
├── src/
│   ├── App.tsx              # 3-panel shell + top nav
│   ├── store.ts             # Zustand (mode, csvPaths, graphSpec, chat, ...)
│   ├── api.ts               # fetch wrappers
│   ├── types.ts
│   └── components/
│       ├── LeftPanel.tsx        # Files (Drive/Local)
│       ├── DrivePanel.tsx
│       ├── GraphCanvas.tsx      # center plot area
│       ├── AIPanel.tsx          # chat + insights
│       ├── InsightCard.tsx
│       └── PublicationBar.tsx   # journal preset + export
├── index.html, vite.config.ts, tailwind.config.js, tsconfig*.json
└── package.json

backend/
├── main.py (mounted by run.py)
├── routers/   (graph, chat, drive, journal, feedback)
├── services/  (analysis_engine, graph_quick, graph_publication, llm_client, ...)
└── models/    (schema.py: AnalysisRequest, GraphSpec, ...)

run.py     # one-click launcher: spawns FastAPI + serves frontend/dist
```

## Phase 2 Status

**Phase A (scaffold, merged):**
- ✅ Port `design/phase2/core_v3.html` shell → React (TopNav, Sidebar, Canvas, DatasetPanel, Cells, LlmDock, Drawer, CmdK, FocusOverlay, ColumnMapper, HelpOverlay, Toast)
- ✅ Extract verbatim constants (JOURNAL_PRESETS, GRAPH_TPLS, STAT_OPS, COMPUTE_METRICS, CANONICAL_RECIPES, HISTORY, STATS_LIB, EXPORT_FORMATS)
- ✅ Full CSS port (49 kB gzipped 9 kB)
- ✅ Zustand workspace store with persist
- ✅ Claude proxy (`/api/claude/complete`) + Datasets router (`/api/datasets/*`)
- ✅ Pretendard + JetBrains Mono self-hosted

**Phase B (todo):**
- `/api/compute`, `/api/stats`, `/api/graphs/render`, `/api/export/bundle` — real backends (SciPy + matplotlib + pingouin)
- Brush-zoom and crosshair in FocusOverlay
- `@dnd-kit/sortable` reordering for cells
- SSE stream at `/api/claude/stream`
- Playwright e2e tests per HANDOFF §3.5

## Design Goals

1. **Paper-ready all-in-one** — 업로드 → 요청 → 카드 그리드 → 저널 export, 한 페이지에서 종결.
2. **즉시 로딩 피드백** — 요청 즉시 스켈레톤 카드 생성 → 렌더 완료 시 플롯 삽입.
3. **다중 그래프 관리** — Figma/Observable 스타일 카드 그리드, 인라인 제목·캡션 편집.
4. **저널 프리셋** — 각 카드에서 IEEE/Nature/Science 등 선택 → SVG/PNG 일괄 export.

## Deployment

- Single-user, localhost only. 연구자 본인 Mac/PC에서 `python3 run.py` 로 실행.
- Mac `.app` 번들 제공 (별도 빌드).

## License

TBD (개인 연구용).
