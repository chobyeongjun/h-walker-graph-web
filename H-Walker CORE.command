#!/bin/bash
# ==============================================================
#  H-Walker CORE · double-click launcher (macOS + Linux)
#
#  Finder에서 이 파일을 더블클릭하면 Terminal이 열리면서 서버를
#  띄우고 앱 창이 뜹니다. Dock으로 드래그하면 상주 앱 아이콘처럼
#  쓸 수 있어요.
#
#  pywebview가 설치돼 있으면 네이티브 창(desktop.py),
#  없으면 기본 브라우저 탭(run.py) 으로 자동 분기합니다.
# ==============================================================

set -e
cd "$(dirname "$0")"

# zsh/bash 프로필 로드 — ANTHROPIC_API_KEY 같은 env 가 export 돼 있도록
for f in ~/.zshrc ~/.zprofile ~/.bash_profile ~/.bashrc; do
    [ -f "$f" ] && source "$f" 2>/dev/null || true
done

echo "=============================================="
echo " H-Walker CORE"
echo " repo : $(pwd)"
echo " key  : ${ANTHROPIC_API_KEY:+set}${ANTHROPIC_API_KEY:-NOT SET ─ Claude will 503}"
echo "=============================================="
echo

# pywebview 유무로 네이티브 창 vs 브라우저 분기
if python3 -c "import webview" 2>/dev/null; then
    echo "[launcher] pywebview detected → opening native window"
    python3 desktop.py "$@"
else
    echo "[launcher] pywebview not installed → opening in browser"
    echo "             (to get a native window: pip3 install pywebview)"
    python3 run.py "$@"
fi
