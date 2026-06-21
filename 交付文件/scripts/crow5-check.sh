#!/bin/sh
# LoopOS 项目自检脚本 —— 运行 pytest / ruff / mypy 三件套
# 这些命令与 Makefile、.github/workflows/ci.yml、README「Development」小节一致
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python"
fi

echo "[Crow5] 自检目录：$ROOT_DIR"
echo "[Crow5] Python：$PY"
echo ""
echo "=== 1/3 pytest（确定性、离线测试套件） ==="
"$PY" -m pytest -q
echo ""
echo "=== 2/3 ruff（代码风格） ==="
"$PY" -m ruff check .
echo ""
echo "=== 3/3 mypy（类型检查，只扫 loopos + tests，与 Makefile 一致） ==="
"$PY" -m mypy loopos tests
echo ""
echo "[Crow5] 自检通过。"
