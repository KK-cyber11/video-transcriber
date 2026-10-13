#!/bin/sh
# 一次性安装：在 scripts/.venv 里装好依赖和无头浏览器
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
if command -v uv >/dev/null 2>&1; then
  uv venv -q --clear --python 3.12 .venv && uv pip install -q -p .venv -r requirements.txt
else
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    echo "需要 Python 3.10+（macOS 自带的 Xcode python3 通常是 3.9）。请先安装 uv：curl -LsSf https://astral.sh/uv/install.sh | sh ，或 brew install python@3.12，然后重新运行本脚本。"; exit 1
  fi
  python3 -m venv --clear .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/python -m playwright install chromium
if [ "$(uname)" = "Linux" ]; then .venv/bin/python -m playwright install-deps chromium 2>/dev/null || echo "（如浏览器启动失败，请用 sudo 运行：.venv/bin/python -m playwright install-deps chromium）"; fi
.venv/bin/python -c "import faster_whisper, opencc, yt_dlp, playwright, imageio_ffmpeg; print('安装完成 ✅')"
