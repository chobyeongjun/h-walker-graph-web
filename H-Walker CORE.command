#!/bin/zsh
# ==============================================================
#  H-Walker CORE · double-click launcher (macOS + Linux)
#
#  Finder에서 이 파일을 더블클릭하면 Terminal 창이 열리고 서버가
#  뜹니다. 서버를 Ctrl-C 로 멈추기 전까지 창은 유지됩니다.
#
#  pywebview가 설치돼 있으면 네이티브 창(desktop.py) 으로,
#  없으면 브라우저 탭(run.py) 으로 자동 분기합니다.
# ==============================================================

# zsh 에서 bash 스타일로 쓰려고 옵션 고정
emulate -L zsh
setopt LOCAL_OPTIONS SH_WORD_SPLIT PIPE_FAIL

# 창이 실수로 닫히더라도 원인을 남기도록 에러 trap
trap 'print -P "\n%F{red}[launcher] exited with code $? — press Enter to close%f"; read' EXIT ERR

cd "${0:h}"

# ── ENV 로딩 ────────────────────────────────────────────────
# .zshrc 를 source 하는 대신, 전용 env 파일을 먼저 읽는다.
# 이유: Finder 가 띄우는 Terminal은 이미 login-shell 이라서
#       zshrc 는 이미 한 번 실행된 상태. 두 번째 source 는
#       exec/exit 때문에 창이 꺼질 수 있다.
for f in ~/.hwalker.env ~/.config/hwalker.env ./.env; do
    if [[ -f "$f" ]]; then
        set -a; source "$f" 2>/dev/null; set +a
        print -P "[launcher] loaded %F{244}$f%f"
    fi
done

# ── 헤더 출력 ─────────────────────────────────────────────────
print "=============================================="
print " H-Walker CORE"
print " repo : $(pwd)"
if [[ -n "$ANTHROPIC_API_KEY" ]]; then
    print -P " key  : %F{green}SET%f (${ANTHROPIC_API_KEY:0:12}…)"
else
    print -P " key  : %F{red}NOT SET%f — Claude endpoints will 503"
    print "       → export ANTHROPIC_API_KEY=sk-ant-…"
    print "       → or save it to ~/.hwalker.env"
fi
print "=============================================="
print

# ── Python3 유무 체크 ────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
    print -P "%F{red}[launcher] python3 not found.%f"
    print "  Install:  brew install python@3.13"
    exit 1
fi

# ── frontend/dist 빌드 여부 확인 ──────────────────────────────
if [[ ! -d "frontend/dist/assets" ]]; then
    print -P "%F{yellow}[launcher] frontend/dist missing — rebuilding…%f"
    if ! command -v npm >/dev/null 2>&1; then
        print -P "%F{red}  npm not found. Install Node.js (brew install node).%f"
        exit 1
    fi
    (cd frontend && [[ ! -d node_modules ]] && npm install --silent; npm run build) || {
        print -P "%F{red}[launcher] frontend build failed%f"; exit 1;
    }
fi

# ── pywebview 유무로 네이티브 창 vs 브라우저 분기 ─────────────
# Finder 더블클릭 시 arg 는 비어 있음. 터미널에서 넘긴 run.py-전용
# arg (--no-browser) 는 desktop.py 가 거부하므로 필터.
args=()
for a in "$@"; do
    case "$a" in
        --no-browser) ;;  # desktop.py 는 항상 네이티브 창이므로 drop
        *) args+=("$a") ;;
    esac
done

if python3 -c "import webview" 2>/dev/null; then
    print "[launcher] pywebview detected → opening native window"
    exec python3 desktop.py "${args[@]}"
else
    print "[launcher] pywebview not installed → opening in browser"
    print "             (to get a native window: pip3 install pywebview)"
    exec python3 run.py "$@"
fi
