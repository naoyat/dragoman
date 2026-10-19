#!/bin/bash
#
# macOS のサービス (右クリックのメニュー「dragoman で解析」) から呼ばれる: 選択したテキスト (標準入力) を dragoman で解析し、
# 解析結果のノート (HTML) をブラウザで開く。言語は文字から推定する (短い選択では取り違えることがある)
#
#   echo "Ua ʻai ke keiki i ka poi." | tools/macos/dragoman-service.sh
#
# DRAGOMAN_PYTHON: 使う Python (サービスはログインシェルの PATH を引き継がないので、tools/macos/install_service.py が書き込む)
# 一時ファイル: ${TMPDIR}/dragoman-service/ (選択したテキスト・ノート・ログ)
#
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${DRAGOMAN_PYTHON:-python3}"
OUT="${TMPDIR:-/tmp}/dragoman-service"
mkdir -p "$OUT"
stamp="$(date +%Y%m%d-%H%M%S)-$$"
text="$OUT/$stamp.txt"
html="$OUT/$stamp.html"
log="$OUT/$stamp.log"
cat > "$text"
if [ ! -s "$text" ]; then
    osascript -e 'display alert "dragoman" message "テキストが選択されていません"' >/dev/null
    exit 0
fi
cd "$REPO" && "$PYTHON" "$REPO/dragoman.py" --html "$html" "$text" > "$log" 2>&1
if [ -s "$html" ]; then
    open "$html"
else
    message="$(tail -3 "$log" | tr '"\\' "''" | tr '\n' ' ')"
    osascript -e "display alert \"dragoman\" message \"解析できませんでした: $message\"" >/dev/null
fi
