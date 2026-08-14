#!/usr/bin/env bash
# Recall 本地启动脚本（Git Bash / macOS / Linux）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Recall 启动 =="

# 1. 后端
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  echo "[backend] 创建虚拟环境..."
  python3 -m venv .venv
  ./.venv/bin/python -m pip install -r requirements.txt
fi
echo "[backend] 迁移数据库..."
./.venv/bin/python -m alembic upgrade head
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 2. 前端
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  echo "[frontend] 安装依赖..."
  npm install
fi
echo "[frontend] 启动开发服务器 http://127.0.0.1:5173"
npm run dev

# Ctrl+C 时同时停止后端
trap "kill $BACKEND_PID 2>/dev/null || true" EXIT
