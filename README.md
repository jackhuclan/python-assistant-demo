# AI Customer Service Agent · 智能客服 Agent

<p align="center">
  <a href="./README.zh.md">🇨🇳 中文文档</a> | 🇬🇧 English
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-FastAPI-009688?logo=python&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18_Vite-61DAFB?logo=react&logoColor=white" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/TailwindCSS-3-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind">
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">
</p>

## Introduction

A production-ready **AI Customer Service Agent** web application. Backend is built with **Python FastAPI + SQLite**, frontend with **React 18 + Vite + TypeScript + Tailwind CSS**, and it connects to any **OpenAI-compatible LLM endpoint**. It provides multi-turn streaming conversations, FAQ knowledge-base retrieval, automatic intent recognition, and hands off to a human agent automatically when the bot cannot resolve an issue.

## Features

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

## Directory Layout

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
│   ├── tests/             # pytest (22 cases)
│   └── Dockerfile
├── frontend/              # React frontend
│   ├── src/pages/Chat.tsx # Customer chat page
│   ├── src/pages/admin/   # Login / workbench / history / FAQ / stats
│   ├── nginx.conf         # Static hosting + /api reverse proxy
│   └── Dockerfile
├── docker-compose.yaml    # One-command startup (frontend + backend)
└── run.py                 # Cloud deploy entry (reads $PORT)
```

## Getting Started

### Option 1: Docker Compose (recommended)

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

### Option 2: Local development

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

### Running tests

```bash
cd backend && python -m pytest tests -q
```

## Configuration

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

> **Note**: `backend/.env` is git-ignored and will NOT be committed. Use `backend/.env.example` as the template.

## License

MIT
