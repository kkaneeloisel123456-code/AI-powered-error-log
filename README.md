# Recall - AI 智能错题本

单用户本地部署的 AI 错题管理 Web 应用：拍照/文本/对话录入 → AI 归档 → SM-2 复习计划 → AI 变体题与批改 → 数据看板与知识图谱 → AI 答疑。

- **输入文档**：`Recall-AI智能错题本-PRD.pdf` v0.9、`Recall-UIUX-Design-Spec.pdf`、`UIUX设计文档.pdf` v1.0、`开发规划文档.pdf` v1.0
- **UI 风格**：方案 A「极简专业风 / Study OS」全局主风格；复习与 AI 答疑提供「专注舱」深色变体；PDF 导出用「纸感学术风」
- **里程碑**：M0 工程初始化 ✅ → M1 基础骨架 ✅ → M2 识图录入 ✅ → M3 复习闭环 ✅ → M4 数据与导出 ✅ → M5 对话与打磨 ✅

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Pinia + Vue Router + ECharts（自研组件库，严格对齐 Design Token） |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic 2 |
| 数据库 | SQLite（WAL）+ Alembic 迁移 |
| OCR | PaddleOCR-VL（接口抽象，默认 mock 可演示） |
| LLM | DeepSeek API（OpenAI 兼容协议，AiGateway 封装 + mock 降级） |
| 测试 | Pytest / Vitest / Playwright |

## 快速开始

```bash
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
# 或 Git Bash
bash scripts/start.sh
# 或 Docker
docker compose up
```

- 前端 http://127.0.0.1:5173 ，后端 http://127.0.0.1:8000 （API 文档 /docs）
- 首次进入自动揭示本地 Token（仅一次），之后凭 Token 进入；数据全部在 `data/` 目录

## 目录结构

```
recall-ai/
├── backend/          # FastAPI：api/（薄路由）+ services/（业务）+ db/ + ai/ + ocr/ + tasks/ + storage/
│   ├── app/
│   ├── alembic/      # 迁移（0001 为基线）
│   └── tests/        # pytest 单元/契约测试
├── frontend/         # Vue3 SPA
│   └── src/
│       ├── app-shell/    # 全局外壳（导航/顶栏/底部导航/主题切换）
│       ├── pages/        # home/import/mistakes/review/dashboard/chat/help/settings
│       ├── components/   # mistake/import/review/dashboard/chat/common
│       ├── stores/       # Pinia
│       ├── api/          # apiClient + SSE
│       ├── styles/       # tokens.css / base.css / responsive.css
│       └── constants/zh.ts
├── docs/
│   ├── testcases/    # 各里程碑测试用例文档
│   └── acceptance/   # 验收记录
├── data/             # SQLite + 图片 + 备份 + Token（不入库）
└── scripts/          # 一键启动
```

## 依赖说明（开发规划 5.5「不引入未登记的新依赖」登记）

| 包 | 用途 | 文档依据 |
|---|---|---|
| lucide-vue-next | Lucide 线性图标（线宽 1.5px） | UI/UX 2.3 组件规范 |
| echarts | 看板图表 / 知识图谱 | 技术基线 |
| marked + dompurify | AI 流式 Markdown 渲染 + 防注入 | PRD 8.1「Markdown 渲染」 |
| cryptography | API Key 本机加密 | 开发规划 5.5 |
| Pillow | 图片校验/压缩 | PRD 5.1.1 |

组件库决策：UI/UX 2.3 的按钮高度/描边/圆角/悬停态等规范与主流组件库默认样式冲突面大，自研轻量组件（Button/Card/Dialog/Toast/Skeleton 等）以 Design Token 为唯一来源，零额外依赖、完全合规。

## 环境变量

见 `.env.example`。默认 `RECALL_AI_MOCK=true`、`RECALL_OCR_MOCK=true`（无 Key / 无 Paddle 环境可跑通主流程）。

## 测试

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest   # 后端（97 用例）
cd frontend && npm test                               # 前端单元（37 用例）
cd frontend && npm run test:e2e                       # Playwright 全流程 E2E（需后端已启动）
backend/.venv/Scripts/python.exe scripts/perf_test.py # 万级数据性能压测
```

各里程碑测试用例见 `docs/testcases/`（M0~M5 六份文档），验收记录见 `docs/acceptance/`。
