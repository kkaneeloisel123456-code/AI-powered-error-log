# Recall 本地启动脚本（Windows PowerShell）
# 用法：powershell -ExecutionPolicy Bypass -File scripts/start.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Recall 启动 ==" -ForegroundColor Cyan

# 1. 后端
$backend = Join-Path $root "backend"
if (-not (Test-Path (Join-Path $backend ".venv"))) {
    Write-Host "[backend] 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv (Join-Path $backend ".venv")
    & (Join-Path $backend ".venv\Scripts\python.exe") -m pip install -r (Join-Path $backend "requirements.txt")
}
$py = Join-Path $backend ".venv\Scripts\python.exe"
Write-Host "[backend] 迁移数据库..." -ForegroundColor Yellow
Push-Location $backend
& $py -m alembic upgrade head
Start-Process -FilePath $py -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WindowStyle Normal
Pop-Location

# 2. 前端
$frontend = Join-Path $root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "[frontend] 安装依赖..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
}
Write-Host "[frontend] 启动开发服务器 http://127.0.0.1:5173" -ForegroundColor Yellow
Push-Location $frontend
npm run dev
