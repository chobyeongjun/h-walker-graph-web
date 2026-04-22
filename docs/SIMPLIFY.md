# UI Simplification Candidates

**Goal:** "앱 기능이 너무 직관적이지가 않음 → 불필요한 것들 먼저 리스트업"

각 항목은 `[제거]` / `[축소]` / `[통합]` 중 하나로 분류. 숫자는 예상 충격도 (1=작음 → 5=매우 큼). 모든 결정은 사용자 승인 후 실행.

---

## 🔴 바로 제거 추천 (사용 빈도 낮고 인지 부담 높음)

### 1. `[제거]` ⌘K Command Palette (2)
- **왜 불필요한가:** 기능이 전부 사이드바 + 셀 툴바 + LlmDock 에 이미 노출됨. 팔레트는 파워유저용인데 이 도구는 연구자 1인 전용이라 **클릭 동선이 더 빠름**.
- **현재 위치:** `src/components/CmdK.tsx`, TopNav `⌘K` 버튼
- **대체:** LlmDock에 자연어로 "force 그래프 추가해줘" 하면 됨 (Claude proxy 이미 있음)
- **지울 파일:** `CmdK.tsx`, TopNav `.kbd` 버튼 + handler

### 2. `[제거]` Help Overlay (`?` key) (1)
- **왜 불필요한가:** 단축키가 ⌘K + Esc 밖에 없음. ⌘K 제거하면 Esc 하나만 남아서 도움말 오버레이 의미 사라짐.
- **지울 파일:** `HelpOverlay.tsx`, App.tsx 의 `?` 키 handler
- **대체:** 사이드바 맨 아래 "Docs" 링크 → README 로 이동

### 3. `[제거]` History Drawer (3)
- **왜 불필요한가:** 현재는 하드코딩된 mock 데이터 (`HISTORY` in catalogs.ts) 만 표시. 실제 undo/checkpoint 시스템은 Phase B+ 작업. **있어보이지만 동작 안 함** → 사용자 혼란.
- **지울 파일:** `Drawer.tsx` 의 history 케이스, `HISTORY` export
- **대체:** Zustand persist 가 로컬스토리지에 상태 저장 중 — 필요하면 "Reset workspace" 버튼만 추가

### 4. `[제거]` Settings Drawer (2)
- **왜 불필요한가:** Auto-save (10s), LLM (Haiku 4.5), Accent 3개 — 전부 **고정값**이고 실제로 설정 안 됨. 보이기만 하는 UI 는 오히려 "이걸 건드려야 하나?" 부담.
- **지울 파일:** `Drawer.tsx` 의 settings 케이스
- **대체:** 환경변수로 제어 (`ANTHROPIC_MODEL`, `LLM_PROVIDER`)

### 5. `[제거]` Stats Library Drawer (2)
- **왜 불필요한가:** 통계 선택은 StatCell 안에 이미 OP 버튼 9개로 노출됨. 별도 드로어는 중복.
- **지울 파일:** `Drawer.tsx` 의 stats 케이스, `STATS_LIB` export
- **대체:** StatCell 툴바의 test-select 가 드롭다운 → 드로어 기능 대체

### 6. `[제거]` Publication Mode 별도 토글 (3)
- **왜 불필요한가:** 각 GraphCell 툴바에 "Journal" select 가 이미 있음. 전역 pub 모드를 또 토글하는 건 **두 개의 진실**이 됨 (global preset vs per-cell preset). 혼란 요인.
- **지울 파일:** TopNav 의 `mode-toggle`, `body.pub` 관련 CSS
- **대체:** **항상 journal preset 기반**으로 동작. 셀 툴바의 Journal select 에서 "dark preview" 옵션 추가 (기본값) 으로 지금의 "quick" 모드 재현.

### 7. `[제거]` Page breadcrumbs + Page-title 편집 (1)
- **왜 불필요한가:** "Project / Treadmill / Pilot 03" breadcrumb 은 단일 사용자 로컬 앱에서 무의미. 페이지 제목도 하나뿐이라 편집할 이유 없음.
- **지울 파일:** Canvas.tsx 의 `.page-head` 전체
- **대체:** TopNav 에 간단히 dataset 이름만 표시

---

## 🟡 축소 권장 (기능은 유지, 시각적 부담 감소)

### 8. `[축소]` Sidebar → 아이콘 3개로 (2)
- **현재:** Home / History / Stats / Exports / Settings (5개)
- **추천:** **Home + Exports** 2개만. 나머지는 위에서 제거.
- **파일:** `Sidebar.tsx` ITEMS 배열 정리

### 9. `[축소]` Dataset card 정보 (2)
- **현재:** tag + name + rows + dur + hz + mapped cols chips (5+줄)
- **추천:** **name + n rows + hz** 한 줄. columns 세부는 ColumnMapperModal 에서만 노출.
- **파일:** `DatasetPanel.tsx` `.ds-card` 내부

### 10. `[축소]` LlmDock context chip (1)
- **현재:** "Context · ds1 · N cells"
- **추천:** 그냥 활성 dataset 이름만. N cells 는 메타 정보 불필요.
- **파일:** `LlmDock.tsx` `.llm-ctx`

### 11. `[축소]` Cell 툴바 tools (3)
- **현재 그래프 셀:** Focus / Duplicate / Delete (3개) + Graph-select + Journal-select + Stride-avg + Export (4개) = **7개 컨트롤**
- **추천:**
  - Focus, Duplicate 제거 (Dup 은 Export → SVG 로 대체 가능, Focus 는 카드 자체 클릭으로 확대)
  - Graph-select 를 셀 제목 클릭 → 변경 팝오버로 이동
  - Stride-avg 는 "force" 템플릿일 때만 노출 (이미 되어 있음)
- **결과:** Delete + Journal + Export 3개 핵심으로 축소

### 12. `[축소]` Drawer 구조 (3)
- **현재:** history / exports / stats / settings = 4종
- **추천:** **exports 만** 남기고 3개 제거. 사이드바에도 Download 아이콘 하나만.
- **파일:** `Drawer.tsx`, `Sidebar.tsx`

---

## 🟢 통합 (UX 충돌 제거)

### 13. `[통합]` Global preset vs per-cell preset override (4)
- **현재:** Publication bar 의 저널 탭 → `globalPreset` / 각 그래프 셀 Journal select → `cell.preset` (override)
- **문제:** 사용자가 "IEEE로 했는데 이 그래프는 왜 Nature로 보이지?" 혼란 생김
- **추천:** **단일 전역 preset**. 셀별 override 는 고급 옵션으로 숨기거나 제거.
- **파일:** `GraphCell.tsx` Journal select 제거, `PublicationBar` 또는 TopNav dropdown 으로 단일 노출

### 14. `[통합]` Add cell 입구 중복 (2)
- **현재:** (a) ⌘K 팔레트 (b) LlmDock 자연어 (c) Recipes 체크박스 Apply (d) Stats Library drawer 클릭 (e) (없는) add-slot 버튼
- **추천:** **(b) LlmDock 자연어 + (c) Recipes** 만. 나머지 제거 → 모든 셀 추가는 자연어 또는 recipe 템플릿으로.

---

## 🛠️ 기술적 정리 (사용자 체감 없지만 장기 유지보수)

### 15. `[제거]` Legacy `frontend/src.legacy/` (1)
- Phase 2 전환 시 구 React 트리를 보존해뒀는데, git history에도 있음. 디스크 낭비.
- **명령:** `rm -rf ~/h-walker-graph-web/frontend/src.legacy`

### 16. `[제거]` Backend 의 구 legacy 라우터 (2)
- `chat.py`, `feedback.py`, `drive.py`, `journal.py`, `graph.py` — 전부 Phase 1 시절 endpoint. Phase 2 프론트엔드는 `/api/claude/*`, `/api/datasets/*`, `/api/graphs/*` 만 사용.
- **추천:** 구 라우터는 **삭제 후보** (drive 는 제외 — 사용 중이면 유지). 또는 `/api/v1/` prefix 로 격리.
- **영향:** `/api/files/upload`, `/api/chat`, `/api/graph/quick`, `/api/graph/publication`, `/api/analyze/full` 사라짐

### 17. `[통합]` Tools vendoring (1)
- `tools/auto_analyzer/` 와 `tools/graph_analyzer/` 전체를 vendor 했는데 실제로 사용하는 함수는 `analysis_engine.py` 의 6~7개 뿐. **필요한 함수만 추출해서 `backend/services/analysis_core.py` 로 이전** → `tools/` 폴더 제거 가능.

---

## ✅ 유지 권장 (핵심 가치)

- **LlmDock** — 자연어 상호작용이 이 도구의 차별점
- **GraphCell + SVG 직접 렌더** — 논문 미리보기 WYSIWYG
- **Publication bar (journal preset picker)** — 핵심 워크플로우
- **ColumnMapperModal** — CSV 매핑은 필수
- **Toast** — 비파괴적 피드백
- **Drag&drop CSV upload** — 요청한 대로 "선 넘은" 기본 기능

---

## 🎯 추천 실행 순서 (효과 대비 리스크)

1. **1-Week quick wins (저리스크, 즉각 체감):**
   - [제거 1, 2, 3, 4, 5] = 4개 drawer 중 3개 + cmdK + help → 코드 -500 lines, 인지 부담 급감
   - [축소 8, 10] = 사이드바 아이콘 3개로, LlmDock chip 단순화
   - [제거 15] = legacy 폴더 제거

2. **2-Week 구조 개선 (중간 리스크):**
   - [제거 6, 7] = publication 전역 토글 제거 + breadcrumbs 제거
   - [통합 13] = global vs per-cell preset 단일화
   - [축소 11] = 셀 툴바 3개 핵심으로

3. **Phase B 같이 (의존성 큼):**
   - [제거 16] = 구 backend 라우터 삭제
   - [통합 17] = tools vendoring 정리

---

**다음 단계:** 이 리스트 중 어느 항목부터 실행할지 선택해줘. 예를 들어 `"1,2,3,4,5,8,15 실행해줘"` 라고 하면 Quick wins 한 번에 처리.
