# H-Walker Graph App — Design Spec

**Date:** 2026-04-15
**Status:** Approved

---

## Goal

자연어로 명령하면 H-Walker CSV 데이터를 즉시 분석하고 그래프를 생성하는 풀스택 웹 앱.  
실험 후 빠른 피드백(Quick 모드)과 논문/발표용 고품질 그래프(Publication 모드) 두 가지 워크플로우를 단일 앱에서 지원한다.

---

## Users

랩 멤버 2-5명, 같은 네트워크에서 접속. H-Walker 데이터 구조를 알고 있음. 인증 불필요 (로컬 네트워크).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND  React + TypeScript + Vite                            │
│  ┌──────────────┐  ┌──────────────────────────┐  ┌──────────┐  │
│  │ Left Panel   │  │   Center: Graph Canvas   │  │  Right   │  │
│  │ Drive 파일   │  │  Quick: Plotly.js        │  │  AI      │  │
│  │ 트리 브라우저│  │  Publication: <img> SVG  │  │  Panel   │  │
│  └──────────────┘  └──────────────────────────┘  └──────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API + WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│  BACKEND  FastAPI + Python                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐  │
│  │  AI Router   │  │ Graph Router │  │  Drive   │  │Analysis│  │
│  │  Ollama      │  │  Plotly JSON │  │  Router  │  │ Engine │  │
│  │  Gemma4:e4b  │  │  matplotlib  │  │  OAuth2  │  │ pandas │  │
│  └──────────────┘  └──────────────┘  └──────────┘  └────────┘  │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
    Ollama (localhost:11434)        Google Drive API
```

---

## Tech Stack

| 레이어 | 기술 |
|--------|------|
| Frontend | React 18 + TypeScript + Vite |
| Routing | React Router v6 |
| Graph (Quick) | Plotly.js + react-plotly.js |
| Graph (Publication) | matplotlib (서버 사이드) → SVG |
| State 관리 | Zustand |
| HTTP/WS | axios + native WebSocket |
| Backend | FastAPI + uvicorn |
| AI | Ollama Python SDK (gemma4:e4b) |
| Data | pandas + numpy |
| Drive | Google Drive API v3 (google-auth, google-api-python-client) |
| 스타일 | Tailwind CSS |

---

## Layout — C형 3패널

```
┌─────────────────────────────────────────────────────────┐
│  [H-Walker]  ⚡Quick  📄Publication  🕐History  [gemma4:e4b] │  ← TopNav
├───────────┬─────────────────────────────┬───────────────┤
│           │                             │               │
│  Drive    │       Graph Canvas          │   AI Panel    │
│  File     │                             │               │
│  Tree     │  Quick: Plotly interactive  │  스트리밍 채팅 │
│           │  Publication: SVG viewer    │  자동 인사이트 │
│  📁 2026  │  + Publication toolbar      │  대화 히스토리 │
│    trial1 │                             │               │
│    trial2 │                             │  [입력창    ↑] │
│           │                             │               │
└───────────┴─────────────────────────────┴───────────────┘
```

- **Left Panel (220px 고정):** Drive 파일 트리, 드래그&드롭 업로드
- **Center (flex-grow):** 모드에 따라 Plotly 또는 SVG + Publication 툴바
- **Right Panel (320px 고정):** AI 채팅 + 인사이트 카드

---

## 모드 상세

### ⚡ Quick Mode

자연어 입력 → Gemma 4 파싱 → 즉시 Plotly 그래프.

**지원 분석 유형:**

| 분석 | 기본 컬럼 |
|------|----------|
| force | L/R_ActForce_N, L/R_DesForce_N |
| velocity | L/R_ActVel_mps |
| position | L/R_ActPos_deg |
| current | L/R_ActCurr_A |
| imu | L/R_Pitch, Roll, Yaw |
| gyro | L/R_Gx/Gy/Gz |
| gait | GCP + Force + Phase + Event |
| compare | 다중 파일 subplot |

**Plotly 기능:**
- 줌/팬/호버 tooltips
- GCP X축 정규화 토글
- 다중 파일 오버레이 (색상 자동 배정)
- compare 모드: 파일별 subplot
- 범례 클릭으로 시리즈 토글

### 📄 Publication Mode

Quick 그래프를 Publication 버튼으로 전환 → matplotlib 서버 렌더 → SVG 반환.

**Publication 툴바 (그래프 위):**

```
[저널 선택 ▼] [Mean±SD] [Annotation +] [Axis Editor] [Legend] [Figure 크기] [Export SVG]
```

**저널 스타일 어댑터:**

기본 내장 저널 10개:
- IEEE TNSRE
- JNER (Journal of NeuroEngineering and Rehabilitation)
- IEEE RA-L
- Science Robotics
- Journal of Biomechanics
- Gait & Posture
- Medical Engineering & Physics
- PLOS ONE
- Nature / Nature Medicine
- ICRA / IROS (proceedings)

각 저널 스타일은 `backend/journal_styles/` JSON으로 관리:
```json
{
  "name": "IEEE TNSRE",
  "font_family": "Times New Roman",
  "font_size": 8,
  "line_width": 1.0,
  "figure_width_mm": 88,
  "figure_height_mm": 66,
  "color_mode": "grayscale_friendly",
  "dpi": 300,
  "legend_frameon": false
}
```

**알 수 없는 저널 동적 처리:**
1. 사용자가 저널 이름 직접 입력
2. Gemma 4가 해당 저널 figure guideline 추론
3. matplotlib rcParams 자동 생성
4. 결과 로컬 캐시에 저장

**Annotation 기능:**
- 텍스트 박스 추가 (좌표 지정)
- 화살표 추가 (start/end 좌표)
- Mean±SD 밴드 오버레이 (stride-normalized)
- Axis 레이블/제목 인라인 편집
- Figure 크기 mm 단위 직접 입력

**Export:**
- 기본: SVG (벡터, 어떤 크기로도 완벽한 품질)
- 선택: PNG (DPI 지정 가능, 기본 300)

---

## AI Analysis Partner

### 자연어 파싱

Ollama Gemma 4 E4B + Pydantic structured output.

```
사용자: "오늘 실험 Force 비교해줘"
→ AnalysisRequest {
    analysis_type: "force",
    file_pattern: "2026-04-15",
    compare_mode: true,
    normalize_gcp: false,
    sides: ["both"]
  }
```

**지원 자연어 패턴:**
- 날짜: "오늘", "어제", "2026-04-15"
- 측면: "왼쪽만", "오른쪽만", "양쪽"
- 모드: "비교", "오버레이", "GCP에 맞춰서"
- 수정: "아까 그거 왼쪽만 다시", "범례 빼줘"

### 대화 맥락 유지

WebSocket으로 대화 히스토리 유지. 이전 분석 결과를 컨텍스트로 포함하여 후속 명령 처리.

### 자동 인사이트

그래프 생성 후 자동으로:
- Peak force (L/R 비교)
- 보행 비대칭 지수 (Symmetry Index)
- Stride variability (CV%)
- Stance/Swing 비율

인사이트는 AI 패널 상단 카드로 표시. 경고 수준(> 10% 비대칭) 자동 감지.

---

## Google Drive 연동

### 인증 흐름

1. 최초 실행 시 OAuth2 브라우저 플로우 (1회)
2. `~/.hw_graph/credentials.json` 저장
3. 이후 자동 갱신

### 파일 브라우저

- 폴더 트리 (날짜별 정렬)
- CSV 클릭 → 즉시 로드 (로컬 캐시 우선)
- 여러 파일 Ctrl+클릭 다중 선택
- 검색창: 파일명 필터링

### 로컬 캐시

`~/.hw_graph/cache/` — Drive에서 다운받은 CSV 로컬 저장.  
파일 수정 시각 비교로 자동 갱신.

---

## API 엔드포인트

```
POST /api/chat                  자연어 → AnalysisRequest + AI 응답
WS   /ws/chat                   스트리밍 채팅
GET  /api/graph/quick           Plotly JSON spec 반환
POST /api/graph/publication     matplotlib SVG 렌더링 반환
GET  /api/drive/files           Drive 파일 트리
GET  /api/drive/download/{id}   CSV 다운로드 (캐시 우선)
GET  /api/journal/list          저널 스타일 목록
POST /api/journal/resolve       알 수 없는 저널 동적 스타일 생성
GET  /api/history               분석 히스토리
```

---

## 프로젝트 구조

```
tools/graph_app/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LeftPanel/        DriveTree, FileList
│   │   │   ├── GraphCanvas/      QuickGraph (Plotly), PublicationGraph (SVG)
│   │   │   ├── PublicationBar/   툴바: 저널선택, Annotation, Axis, Export
│   │   │   ├── AIPanel/          ChatMessages, InsightCards, InputBar
│   │   │   └── TopNav/           모드 탭, 모델 표시
│   │   ├── stores/               Zustand stores (graphStore, chatStore, driveStore)
│   │   ├── hooks/                useWebSocket, usePlotly, useChat
│   │   └── api/                  axios 클라이언트
│   ├── package.json
│   └── vite.config.ts
└── backend/
    ├── main.py                   FastAPI app
    ├── routers/
    │   ├── chat.py               AI chat + WebSocket
    │   ├── graph.py              Quick + Publication 그래프
    │   ├── drive.py              Google Drive 연동
    │   └── journal.py            저널 스타일 관리
    ├── services/
    │   ├── llm_client.py         Ollama Gemma 4 래퍼
    │   ├── analysis_engine.py    pandas 분석, GCP 정규화, 통계
    │   ├── graph_quick.py        Plotly JSON 생성
    │   ├── graph_publication.py  matplotlib SVG 렌더링
    │   └── drive_client.py       Google Drive API
    ├── models/
    │   ├── schema.py             AnalysisRequest, GraphSpec Pydantic 모델
    │   └── journal_styles/       *.json (저널별 스타일)
    └── requirements.txt
```

---

## 실행 방법 (완성 후)

```bash
# Backend
cd tools/graph_app/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd tools/graph_app/frontend
npm run dev
```

브라우저: `http://localhost:5173`  
랩 멤버 접속: `http://<서버IP>:5173`

---

## Out of Scope

- 사용자 인증/권한 관리
- 실시간 로봇 데이터 스트리밍 (별도 앱)
- CSV 이외 데이터 포맷 (ROS bag 등)
- 모바일 반응형 디자인
- 클라우드 배포 (로컬 네트워크 전용)