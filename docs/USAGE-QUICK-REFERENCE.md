# H-Walker Graph App 사용 퀵 레퍼런스

## 🚀 실행
```bash
cd /Users/chobyeongjun/h-walker-ws/tools/graph_app
python3 run.py
# 브라우저: http://localhost:8000
```

## 📝 자연어 명령 예시
| 입력 | 결과 |
|---|---|
| `Force 그래프` | 양쪽 힘 (Des 점선, Act 실선) |
| `케이블 힘 추종 확인` | 동일 |
| `보행 분석해줘` | gait + GCP 정규화 |
| `왼쪽 IMU 각도` | L_Pitch/Roll/Yaw 만 |
| `속도 프로파일` | velocity |
| `전류` | current (모터 토크 프록시) |
| `GCP로 정규화해서 보여줘` | normalize_gcp=true 추가 |
| `비교 모드` | compare_mode=true |

## 🎨 Publication 저널 프리셋
- IEEE: `ieee_ral`, `ieee_tnsre`, `icra_iros`
- 고 임팩트: `nature`, `science_robotics`
- 생체공학: `jner`, `biomechanics`, `gait_posture`, `plos_one`, `medical_eng_physics`

## 📁 Drive vs Local
- **Drive 탭**: 내 Google Drive 전체 탐색 → CSV 클릭하면 자동 다운로드+캐싱
- **Local 탭**: 드래그앤드롭 또는 클릭해서 CSV 업로드

## 🔧 도메인 지식 편집
Obsidian에서:
```
vault/Research/10_Wiki/h-walker-graph-app-knowledge.md
```
→ 편집 즉시 반영 (재시작 불필요)

## 📊 주요 출력
- **Quick 모드**: Plotly 인터랙티브 (줌, 팬, hover)
- **Publication 모드**: 논문급 SVG
  - L/R **자동 서브플롯 분리**
  - GCP(%) X축 (0~100% 보행주기)
  - Desired **점선**, Actual **실선** (같은 색상 쌍)
  - mean ± SD 밴드

## 🐛 문제 발생 시
1. Ollama 안 뜸: `ollama serve &`
2. Drive 인증 꼬임: `rm ~/.hw_graph/token.json` → 재접속
3. 포트 충돌: `lsof -ti:8000 | xargs kill -9`
4. 빈 그래프: CSV에 `L_GCP`, `R_GCP` 컬럼 있는지 확인

## 📎 관련 문서
- [[H-Walker Graph App LLM Plotting 검증 수정 인수인계]] — 상세 인수인계
- [[h-walker-graph-app-knowledge]] — LLM에 주입되는 도메인 지식
