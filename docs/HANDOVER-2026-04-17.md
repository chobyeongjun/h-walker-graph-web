# H-Walker Graph App LLM + Plotting 검증/수정 인수인계

> 작성일: 2026-04-17
> 대상: H-Walker Graph App (`tools/graph_app/`)
> 목적: LLM 자연어 파싱 + 논문급 Plot 정확도 보장

---

## 1. 요약 (TL;DR)

H-Walker CSV (`Force_50N_adm_m2_c15.CSV` 등)를 대상으로 LLM 자연어 명령을 정확히 파싱하여 Quick(Plotly) / Publication(matplotlib SVG) 그래프를 생성하는 시스템. 다음 5개 핵심 문제를 해결했다.

| # | 문제 | 해결 |
|---|---|---|
| 1 | `run.py` 라우터 prefix 중복 → Drive/Chat 404 | prefix 정리, `main.py`와 일치 |
| 2 | LLM 키워드 매핑 단순 → 의도 파악 실패 | 도메인 지식 Markdown 주입 + 대화형 `action` 필드 |
| 3 | 임의 CSV (MoCap/Vision) 미지원 | 업로드 시 헤더 자동 파싱 → LLM에 동적 주입 |
| 4 | Plot에서 Desired/Actual 구분 없음 | Des=점선, Act=실선 자동 적용 + 동일 색상 쌍 |
| 5 | GCP 정규화 불량 (82/279 교대 stride) | active segment 기반 stride 감지 + active 구간만 리샘플 |

추가: Publication SVG에서 **L/R 자동 서브플롯 분리**

---

## 2. 원클릭 실행 방법

```bash
cd /Users/chobyeongjun/h-walker-ws/tools/graph_app
python3 run.py
```

- 기본 포트 8000 (`--port N`으로 변경 가능)
- `--no-browser`로 브라우저 자동 실행 비활성화
- Ollama가 `localhost:11434`에서 `gemma4:e4b` 모델로 실행 중이어야 함
- Google Drive 연동은 `~/.hw_graph/token.json`이 이미 있음

### 접속
- UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

---

## 3. 시스템 구조

```
tools/graph_app/
├── run.py                          # 실행 스크립트 (수정됨)
├── backend/
│   ├── main.py                     # FastAPI 앱
│   ├── models/
│   │   ├── schema.py               # AnalysisRequest, COLUMN_GROUPS
│   │   └── chat_schema.py          # ChatResponse + action 필드 (수정됨)
│   ├── routers/
│   │   ├── graph.py                # /api/files/upload + /graph/quick|publication (수정됨)
│   │   ├── chat.py                 # /api/chat + /ws/chat (수정됨)
│   │   ├── drive.py                # /api/drive/*
│   │   └── journal.py              # /api/journal/*
│   └── services/
│       ├── analysis_engine.py      # CSV 로드 + stride 감지 (수정됨)
│       ├── llm_client.py           # Ollama Gemma4 래퍼 (수정됨)
│       ├── knowledge_loader.py     # 도메인 지식 로더 (신규)
│       ├── graph_quick.py          # Plotly JSON 생성 (수정됨)
│       ├── graph_publication.py    # matplotlib SVG 렌더 (수정됨)
│       ├── drive_client.py         # Google Drive OAuth2
│       └── journal_resolver.py     # 저널 스타일 해결
└── frontend/dist/                  # 빌드된 React + Plotly (소스 없음)
```

### 외부 지식 베이스 (vault 연동)
```
~/.hw_graph/knowledge/
└── h-walker-domain.md              # LLM에 주입되는 도메인 지식

~/0xhenry.dev/vault/Research/10_Wiki/
└── h-walker-graph-app-knowledge.md  # 위 파일로의 symlink
```

---

## 4. 수정된 파일 상세

### 4.1 `run.py` — 라우터 prefix 수정

**문제:** `run.py`는 `main.py`와 다르게 라우터를 마운트하고 있었음
- `chat_router` → `/api/chat_rest` (프론트엔드는 `/api/chat` 호출 → 404)
- `drive_router` → `/api` + 자체 `/api/drive` = `/api/api/drive` (이중 prefix → 404)

**수정:**
```python
app.include_router(graph_router, prefix="/api")   # graph는 자체 prefix 없음
app.include_router(journal_router)                 # 자체 /api/journal
app.include_router(chat_router)                    # 자체 /api/chat
app.include_router(ws_router)                      # 자체 /ws/chat
app.include_router(drive_router)                   # 자체 /api/drive
```

### 4.2 `analysis_engine.py` — Stride 감지 수정

**문제:** H-Walker CSV의 L/R GCP는 **독립적 톱니파** (각 다리 stance phase에만 0→1.48)
- 기존 로직은 GCP drop을 heel strike로 잡고 consecutive drop 사이 전체를 stride로 취급
- 결과: `82, 279, 80, 263, 82, ...` 교대 (short=정상, long=다른 다리 active 구간 포함)

**수정:**
```python
def detect_heel_strikes(gcp_or_df, ...):
    # GCP > 0.01로 active segment 정의
    active = gcp > 0.01
    edges = np.diff(active.astype(int), prepend=0)
    starts = np.where(edges == 1)[0]  # 0→1 전환 지점
    # 각 active segment의 start가 진짜 heel strike
    return starts
```

```python
def normalize_to_gcp(signal, hs_indices, gcp=None):
    # gcp가 주어지면 active 구간만 잘라서 리샘플
    for start in hs_indices:
        end = start
        while end < len(gcp) and gcp[end] > 0.01:
            end += 1
        chunk = signal[start:end]  # active 구간만
        resampled = np.interp(gcp_axis, np.linspace(0,1,len(chunk)), chunk)
```

**결과:**
- L: 21 strides × 65 samples (각 ~0.59s stance phase)
- R: 15 strides × 65 samples
- ActForce 프로파일 깔끔, RMSE 계산 정확

### 4.3 `llm_client.py` — 도메인 지식 주입 + 대화형

**수정 사항:**
1. `_build_system_prompt()`: `~/.hw_graph/knowledge/*.md` 전체 로드 → system prompt에 주입
2. `parse_command(command, history, csv_columns_text)`: CSV 헤더 동적 주입
3. 대화형 응답: 확실하면 `action="plot"`, 애매하면 `action="clarify"` + 질문

**사용 예:**
```python
result = parse_command("Force 그래프 보여줘")
# → {'action': 'plot', 'analysis_request': {...}, 'message': '...'}

result = parse_command("ㅎㅇ")
# → {'action': 'clarify', 'message': '어떤 데이터를 보고 싶으신가요?'}
```

### 4.4 `knowledge_loader.py` (신규)

```python
KNOWLEDGE_DIR = Path("~/.hw_graph/knowledge").expanduser()

def load_knowledge() -> str:
    """모든 .md 파일을 읽어 합쳐서 반환 (런타임 로드)"""

def register_csv_columns(path, columns):
    """업로드된 CSV 헤더를 세션 캐시에 저장"""

def get_csv_columns_text() -> str:
    """저장된 CSV 헤더를 LLM 프롬프트용 텍스트로 포맷"""
```

### 4.5 `chat_schema.py` — action 필드

```python
class ChatResponse(BaseModel):
    message: str
    action: str = "plot"  # "plot" | "clarify" | "insight"
    analysis_request: Optional[AnalysisRequest] = None
    insights: list[str] = []
```

### 4.6 `graph.py` (routers) — CSV 헤더 반환

```python
@router.post("/files/upload", response_model=UploadResponse)
def upload_files(payload):
    # ...
    df = pd.read_csv(tmp.name, nrows=0)
    cols = [c.strip() for c in df.columns.tolist()]
    all_columns.append(cols)
    register_csv_columns(tmp.name, cols)  # 세션에 등록
    # ...
    return UploadResponse(paths=paths, columns=all_columns)
```

### 4.7 `graph_quick.py` — Des=점선, Act=실선

```python
def _is_desired_column(col: str) -> bool:
    return "Des" in col or "des" in col

def _color_key(col: str) -> str:
    """L_DesForce_N과 L_ActForce_N이 같은 색상 그룹이 되도록"""
    return col.replace("Des", "").replace("Act", "").replace("Err", "")

# build_traces()에서:
dash = "dash" if _is_desired_column(col) else "solid"
width = 1.2 if _is_desired_column(col) else 1.8
# 같은 _color_key() 그룹은 동일 SERIES_COLOR 사용
```

### 4.8 `graph_publication.py` — L/R 서브플롯 분리 + 점선

**핵심:** `sides=["both"]`이고 L/R 컬럼 모두 있으면 **자동으로 1×2 서브플롯** 생성

```python
has_left = any(c.startswith("L_") for c in columns)
has_right = any(c.startswith("R_") for c in columns)
split_lr = has_left and has_right and "both" in request.sides

if split_lr:
    fig, axes_lr = plt.subplots(1, 2, figsize=(fig_w * 1.8, fig_h), sharey=True)
    # 왼쪽 서브플롯: L_ 컬럼만, 오른쪽: R_ 컬럼만
    # 라벨: "Desired" (점선), "Actual" (실선) — side prefix 제거
```

---

## 5. API 엔드포인트 전체 목록

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 |
| GET | `/api/drive/auth` | OAuth2 인증 상태 |
| GET | `/api/drive/callback` | OAuth2 callback |
| GET | `/api/drive/files?folder_id=root` | Drive 폴더 목록 |
| GET | `/api/drive/download/{file_id}?filename=X` | CSV 다운로드 (캐싱) |
| GET | `/api/drive/search?q=...` | Drive 파일 검색 |
| GET | `/api/journal/list` | 저널 프리셋 목록 (10개) |
| GET | `/api/journal/resolve?journal_name=X` | 저널 스타일 해결 (Gemma4 fallback) |
| GET | `/api/chat/models` | Ollama 모델 목록 |
| POST | `/api/chat` | LLM 자연어 파싱 |
| WS | `/ws/chat` | 스트리밍 채팅 |
| POST | `/api/files/upload` | base64 CSV 업로드 → 경로 + 헤더 반환 |
| POST | `/api/graph/quick` | Plotly JSON (interactive) |
| POST | `/api/graph/publication?journal=X` | SVG (publication) |
| POST | `/api/analyze/full` | 전체 gait 분석 + 그래프 묶음 |

---

## 6. 사용 시나리오

### 6.1 기본 플로우
1. 브라우저에서 `http://localhost:8000` 접속
2. 왼쪽 **FILES** 패널에서 Drive 또는 Local 선택
3. Local: CSV 드래그앤드롭 / Drive: 폴더 탐색 → 파일 클릭
4. 파일 선택되면 왼쪽 하단 "분석" 버튼 활성화
5. 오른쪽 채팅창에 자연어로 요청 (예: "Force 그래프", "보행 분석")
6. LLM이 파싱 → 중앙에 그래프 렌더링
7. **Quick 모드** (Plotly, interactive) ↔ **Publication 모드** (SVG, 저널급)

### 6.2 지원되는 자연어 명령
| 입력 | analysis_type | 기타 |
|---|---|---|
| "Force 그래프" / "힘 추종" / "케이블 힘" | force | — |
| "속도" / "velocity" | velocity | — |
| "위치" / "position" / "관절 각도" | position / imu | — |
| "전류" / "current" / "토크" | current | — |
| "IMU" / "Roll/Pitch/Yaw" | imu | — |
| "보행" / "gait" / "걸음걸이" | gait | normalize_gcp=true |
| "보행주기" / "GCP" | — | normalize_gcp=true |
| "왼쪽" / "left" | — | sides=["left"] |
| "오른쪽" / "right" | — | sides=["right"] |
| "비교" / "compare" | compare | compare_mode=true |
| "에러" / "error" / "오차" | — | columns=[Err...] |

### 6.3 Publication 저널 프리셋 (10개)
- `ieee_ral`, `ieee_tnsre`, `icra_iros` — IEEE
- `nature`, `science_robotics` — 고 impact
- `jner`, `biomechanics`, `gait_posture`, `plos_one`, `medical_eng_physics` — 생체공학

---

## 7. 도메인 지식 편집 방법

Obsidian에서 직접 편집 가능:
```
~/0xhenry.dev/vault/Research/10_Wiki/h-walker-graph-app-knowledge.md
```
→ 이것은 `~/.hw_graph/knowledge/h-walker-domain.md`로의 **심볼릭 링크**

**재시작 불필요:** `llm_client.py`의 `_build_system_prompt()`가 매 호출마다 파일을 다시 읽음

**추가 .md 파일 더하기:**
```bash
echo "# 새 지식" > ~/.hw_graph/knowledge/new-topic.md
```
→ 자동으로 `load_knowledge()`가 모든 `.md`를 합쳐서 LLM에 주입

---

## 8. 임의 CSV 지원 (MoCap/Vision 등)

CSV 업로드 시 헤더가 자동 파싱되어 LLM에 "현재 로드된 컬럼"으로 주입됨.

**예: MoCap 데이터**
```
Hip_Moment, Hip_Power, Hip_Angle, Knee_Angle, Ankle_Angle
```
→ "Hip_Moment 그래프 보여줘" 하면 LLM이 `columns=["Hip_Moment"]`로 직접 지정

**예: Vision 데이터 vs MoCap 비교**
```
Vision_Hip_X, MoCap_Hip_X
```
→ "Vision이랑 MoCap hip 비교해줘" 하면 두 컬럼을 compare_mode로 렌더

---

## 9. 트러블슈팅

### Ollama 연결 실패
```bash
curl http://localhost:11434/api/tags
```
실패하면:
```bash
ollama serve &  # 또는 OS 서비스로 실행
ollama pull gemma4:e4b
```

### Drive 인증 실패
```bash
# 토큰 삭제 후 재인증
rm ~/.hw_graph/token.json
# 브라우저 재접속 → Drive 탭 → 자동 OAuth 재시작
```

### Port 8000 이미 사용 중
```bash
lsof -ti:8000 | xargs kill -9
python3 run.py
```

### Plot이 빈 그래프로 나옴
1. CSV에 `L_GCP`/`R_GCP` 컬럼이 있는지 확인
2. GCP 값 범위 확인 (0~1.48 정상)
3. `detect_heel_strikes()` 결과 확인: L ~20, R ~15이면 정상

### LLM이 잘못 파싱
1. `~/.hw_graph/knowledge/h-walker-domain.md` 수정
2. 재시작 불필요 — 다음 요청부터 반영
3. 또는 더 구체적 명령 사용 ("왼쪽 힘 추종", "force GCP 정규화")

---

## 10. 확장 포인트

- **배치 명령**: "파일A 힘, 파일B 속도 비교" → 현재 LLM은 단일 요청만. 확장 시 `parse_command`에서 멀티 AnalysisRequest 반환하도록 변경
- **History 기반 대화**: 이미 `history: list[ChatMessage]` 전달 경로 있음. WebSocket에서 활용
- **Insight 자동 생성**: `generate_insights_stream()` 이미 있음 → UI에서 Plot 후 자동 스트리밍 연결
- **추가 저널 스타일**: `backend/journal_styles/*.json` 추가 또는 자연어로 요청하면 Gemma4가 생성 후 캐싱

---

## 11. 검증 완료 체크리스트

- [x] 모든 9개 수정 파일 syntax check 통과
- [x] Core API 3개 (`/drive/auth`, `/journal/list`, `/chat/models`) 모두 200
- [x] Drive 폴더 목록 (5 subfolders, 29 files) 정상
- [x] 실제 CSV로 stride 감지 (L=21, R=15, 각 65 samples)
- [x] Quick Plotly traces: Act=solid, Des=dash, 같은 색상 쌍
- [x] Publication SVG: L/R 서브플롯 자동 분리, 점선 4개
- [x] LLM 파싱 5가지 시나리오 모두 정확
- [x] CSV 헤더 자동 감지 (60 columns, L_GCP/R_GCP 포함)
- [x] 도메인 지식 로드 (3,907 chars) + MoCap/admittance 포함
- [x] Vault symlink 정상

---

## 12. 중요 파일 경로 모음

```
실행 파일:
  /Users/chobyeongjun/h-walker-ws/tools/graph_app/run.py

설정 파일 (유저 홈):
  ~/.hw_graph/client_secret.json     # Google OAuth
  ~/.hw_graph/token.json              # OAuth 토큰
  ~/.hw_graph/cache/                  # Drive 다운로드 캐시
  ~/.hw_graph/knowledge/*.md          # LLM 도메인 지식

Vault 연동:
  ~/0xhenry.dev/vault/Research/10_Wiki/h-walker-graph-app-knowledge.md
    (symlink → ~/.hw_graph/knowledge/h-walker-domain.md)

테스트 CSV:
  /Users/chobyeongjun/Library/CloudStorage/GoogleDrive-admin@arlabcau.com/
    공유 드라이브/ARLAB/02_Research_(연구)/[H-Walker]/03_Data/
    04. Walker - Gaitmat test/Robot data/Force_50N_adm_m2_c15.CSV

인수인계 문서 (이 파일):
  /Users/chobyeongjun/h-walker-ws/tools/graph_app/docs/HANDOVER-2026-04-17.md
  ~/0xhenry.dev/vault/Research/10_Wiki/h-walker-graph-app-llm-plotting-handover.md
```

---

## 13. 최근 commit 필요 파일

```
M  tools/graph_app/run.py
M  tools/graph_app/backend/models/chat_schema.py
M  tools/graph_app/backend/routers/chat.py
M  tools/graph_app/backend/routers/graph.py
M  tools/graph_app/backend/services/analysis_engine.py
M  tools/graph_app/backend/services/llm_client.py
M  tools/graph_app/backend/services/graph_quick.py
M  tools/graph_app/backend/services/graph_publication.py
A  tools/graph_app/backend/services/knowledge_loader.py
A  tools/graph_app/docs/HANDOVER-2026-04-17.md
A  ~/.hw_graph/knowledge/h-walker-domain.md  (프로젝트 외부)
```
