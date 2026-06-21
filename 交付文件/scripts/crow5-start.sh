#!/bin/sh
# LoopOS 启动脚本 —— 终端原生 CLI 工具，无 Web 服务、无固定端口
# 真实入口由 pyproject.toml [project.scripts] 定义：loopos = "loopos.cli.app:main"
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

# 优先用仓库自带 venv，其次回退到系统 python
if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x ".venv/bin/python3" ]; then
  PY=".venv/bin/python3"
else
  PY="python"
fi

echo "[Crow5] LoopOS 启动"
echo "[Crow5] 项目目录：$ROOT_DIR"
echo "[Crow5] Python：$PY"
echo "[Crow5] 入口：loopos.cli.app:main （pyproject.toml 已注册 console_script: loopos）"
echo "[Crow5] 端口：不适用（terminal-native CLI，AGENTS.md 明确 MVP 无 Web UI）"
echo ""
echo "—— 首次运行：安装依赖 ——"
"$PY" -m pip install -e ".[dev]" >/dev/null 2>&1 || echo "[Crow5] 警告：依赖安装失败，请手动执行：$PY -m pip install -e \".[dev]\""
echo ""
echo "—— 烟雾测试 ——"
"$PY" -m loopos.cli.app --help
