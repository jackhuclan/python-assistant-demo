# 智能客服 Agent · AI Customer Service Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?logo=python&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18_Vite-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/TailwindCSS-3-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind">
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">
</p>

---

## 🇨🇳 中文说明

### 项目简介

一个开箱即用的「智能客服 Agent」Web 应用。后端基于 **Python FastAPI + SQLite**，前端基于 **React 18 + Vite + TypeScript + Tailwind CSS**，接入任意 **OpenAI 兼容大模型接口**，支持多轮流式对话、FAQ 知识库检索、用户意图自动识别，并在无法解决时自动转接人工客服，形成完整的人工服务闭环。

### 功能说明

| 功能 | 说明 |
|---|---|
| 💬 多轮对话 | SSE 流式输出、打字机效果，携带近 10 轮上下文 |
| 📚 FAQ 知识库检索 | 字符 bigram 余弦相似度 + 关键词加权，取 Top3 注入提示词；预置 8 条示例 FAQ |
| 🎯 意图自动识别 | LLM JSON 分类：退款 / 查询订单 / 技术支持 / 一般咨询；LLM 不可用时关键词规则兜底 |
| 🙋 自动转人工 | 意图为退款、置信度过低、连续 2 轮未命中 FAQ、或用户主动要求时自动转接 |
| 👥 客服工作台 | 转人工会话进入待处理队列，客服实时回复，用户端轮询秒级送达，处理完成一键交还机器人 |
| 🗂 对话历史持久化 | SQLite 存储会话 / 消息 / 评价，支持按状态与意图筛选浏览 |
| 📊 满意度统计 | 星级评价（1-5 分）+ 评论，平均分、评分分布、意图分布可视化 |
| 🔐 管理后台 | 密码登录（HMAC 签名令牌 + HttpOnly Cookie），对话记录 / FAQ 增删改查 / 统计看板 |

### 目录结构

```
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── main.py        # 入口（托管前端构建产物）
│   │   ├── config.py      # 配置（环境变量 / .env）
│   │   ├── database.py    # SQLite 模型 + 预置 FAQ
│   │   ├── llm.py         # LLM 客户端（流式 / 非流式）
│   │   ├── agent.py       # 意图识别 / FAQ 检索 / 转人工判定
│   │   ├── auth.py        # 管理后台令牌
│   │   └── routers/       # chat(SSE) / faq / admin
│   ├── tests/             # pytest（20 个用例）
│   └── Dockerfile
├── frontend/              # React 前端
│   ├── src/pages/Chat.tsx # 用户聊天页
│   ├── src/pages/admin/   # 登录 / 工作台 / 记录 / FAQ / 统计
│   ├── nginx.conf         # 静态托管 + /api 反向代理
│   └── Dockerfile
├── docker-compose.yaml    # 一键启动前后端
└── run.py                 # 云端部署入口（读取 $PORT）
```

### 运行方式

#### 方式一：Docker Compose（推荐）

```bash
# 1. 准备环境变量
cp backend/.env.example backend/.env   # 编辑填入 LLM_BASE_URL / LLM_API_KEY 等

# 2. 一键构建并启动
docker compose up -d --build

# 3. 访问
#    聊天页：http://localhost:8080
#    管理后台：http://localhost:8080/admin
#    后端 API：http://localhost:8000/docs
```

#### 方式二：本地开发

```bash
# 后端（先配置 backend/.env）
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# 前端开发模式（已配置 /api 代理到 8000）
cd frontend
npm install
npm run dev          # http://localhost:5173

# 生产构建（产物由 FastAPI 托管）
npm run build
```

#### 运行测试

```bash
cd backend && python -m pytest tests -q
```

### 配置项

通过 `backend/.env` 或 `docker-compose.yaml` 的 `environment` 配置：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_BASE_URL` | `http://192.168.3.184:3001/v1` | OpenAI 兼容接口地址（不带 `/chat/completions`） |
| `LLM_API_KEY` | 无 | 大模型 API Key |
| `LLM_MODEL` | `deepseek-v4.1-flash` | 模型名称 |
| `LLM_TIMEOUT` | `60` | LLM 请求超时（秒） |
| `ADMIN_PASSWORD` | `admin123` | 管理后台登录密码 |
| `JWT_SECRET` | `csa-change-me-in-production` | 令牌签名密钥（生产环境务必修改） |
| `TOKEN_TTL_HOURS` | `24` | 登录令牌有效期（小时） |
| `DB_PATH` | `backend/data/csa.db` | SQLite 数据库路径 |
| `FAQ_HIT_THRESHOLD` | `0.25` | FAQ 相似度命中阈值 |
| `INTENT_CONFIDENCE_THRESHOLD` | `0.4` | 低于此置信度触发转人工 |
| `MAX_HISTORY_TURNS` | `10` | 携带的最大对话轮数 |
| `UNRESOLVED_ROUNDS_TO_TRANSFER` | `2` | 连续未解决轮数阈值（触发转人工） |

---

## 🇬🇧 English

### Introduction

A production-ready **AI Customer Service Agent** web application. Backend is built with **Python FastAPI + SQLite**, frontend with **React 18 + Vite + TypeScript + Tailwind CSS**, and it connects to any **OpenAI-compatible LLM endpoint**. It provides multi-turn streaming conversations, FAQ knowledge-base retrieval, automatic intent recognition, and hands off to a human agent automatically when the bot cannot resolve an issue.

### Features

| Feature | Description |
|---|---|
| 💬 Multi-turn chat | SSE streaming with typewriter effect, last 10 turns of context |
| 📚 FAQ retrieval | Character-bigram cosine similarity + keyword boosting, Top-3 injected into the prompt; 8 seed FAQs included |
| 🎯 Intent recognition | LLM JSON classification: refund / order query / tech support / general; keyword-rule fallback when LLM is unavailable |
| 🙋 Auto handoff | Triggers when intent = refund, confidence is low, 2 consecutive unresolved rounds, or the user asks for a human |
| 👥 Agent workbench | Handoff queue with real-time agent replies, delivered to the user by polling; one click to hand back to the bot |
| 🗂 Persisted history | SQLite stores conversations / messages / ratings, filterable by status and intent |
| 📊 Satisfaction stats | 1-5 star ratings + comments, average score, rating and intent distribution charts |
| 🔐 Admin console | Password login (HMAC-signed token + HttpOnly cookie), chat history, FAQ CRUD, analytics dashboard |

### Directory Layout

```
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py        # Entry point (serves built frontend)
│   │   ├── config.py      # Configuration (env vars / .env)
│   │   ├── database.py    # SQLite schema + seed FAQs
│   │   ├── llm.py         # LLM client (streaming / one-shot)
│   │   ├── agent.py       # Intent / FAQ retrieval / handoff logic
│   │   ├── auth.py        # Admin token signing
│   │   └── routers/       # chat(SSE) / faq / admin
│   ├── tests/             # pytest (20 cases)
│   └── Dockerfile
├── frontend/              # React frontend
│   ├── src/pages/Chat.tsx # Customer chat page
│   ├── src/pages/admin/   # Login / workbench / history / FAQ / stats
│   ├── nginx.conf         # Static hosting + /api reverse proxy
│   └── Dockerfile
├── docker-compose.yaml    # One-command startup (frontend + backend)
└── run.py                 # Cloud deploy entry (reads $PORT)
```

### Getting Started

#### Option 1: Docker Compose (recommended)

```bash
# 1. Prepare environment
cp backend/.env.example backend/.env   # fill in LLM_BASE_URL / LLM_API_KEY etc.

# 2. Build and start
docker compose up -d --build

# 3. Visit
#    Chat page:      http://localhost:8080
#    Admin console:  http://localhost:8080/admin
#    Backend API:    http://localhost:8000/docs
```

#### Option 2: Local development

```bash
# Backend (configure backend/.env first)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# Frontend dev server (proxies /api to :8000)
cd frontend
npm install
npm run dev          # http://localhost:5173

# Production build (served by FastAPI)
npm run build
```

#### Running tests

```bash
cd backend && python -m pytest tests -q
```

### Configuration

Configure via `backend/.env` or the `environment` section of `docker-compose.yaml`:

| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | `http://192.168.3.184:3001/v1` | OpenAI-compatible base URL (without `/chat/completions`) |
| `LLM_API_KEY` | — | LLM API key |
| `LLM_MODEL` | `deepseek-v4.1-flash` | Model name |
| `LLM_TIMEOUT` | `60` | LLM request timeout (seconds) |
| `ADMIN_PASSWORD` | `admin123` | Admin console password |
| `JWT_SECRET` | `csa-change-me-in-production` | Token signing secret (change in production) |
| `TOKEN_TTL_HOURS` | `24` | Login token TTL (hours) |
| `DB_PATH` | `backend/data/csa.db` | SQLite database path |
| `FAQ_HIT_THRESHOLD` | `0.25` | FAQ similarity hit threshold |
| `INTENT_CONFIDENCE_THRESHOLD` | `0.4` | Confidence below this triggers handoff |
| `MAX_HISTORY_TURNS` | `10` | Max conversation turns sent as context |
| `UNRESOLVED_ROUNDS_TO_TRANSFER` | `2` | Consecutive unresolved rounds before handoff |

---

## License

MIT
