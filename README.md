# Agentic SDLC System

🚀 **Multi-agent orchestration system with real-time control room dashboard**

Watch your AI agents think, act, and collaborate — like SpaceX Mission Control for software development!

## ✨ Features

- 🤖 **Async Multi-Agent System** — Non-blocking ReAct reasoning loop
- 📊 **Real-Time Dashboard** — WebSocket-powered control room
- 🔧 **Extensible Tools** — Git, file operations, linting, type checking
- 🎯 **Production-Ready** — FastAPI + structured logging + observability

## 🎮 Control Room Dashboard

Open `http://localhost:8000` and watch your agents work in real-time!

![Control Room Features](https://img.shields.io/badge/WebSocket-Live-brightgreen)

**See it in action:**
- Agent flow: Think → Act → Observe (with animations!)
- Live trace log with every step
- Metrics: active agents, success rate, duration
- Beautiful dark theme inspired by SpaceX Mission Control

📖 **[Full Control Room Guide →](CONTROL_ROOM.md)**

## Quick Start

```bash
# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key

# Run
uvicorn main:app --reload

# Test agent
curl http://localhost:8000/health
```

## Architecture

- `agents/` - Agent implementations (Reviewer, Fixer, etc.)
- `tools/` - Tool definitions (git, file operations, etc.)
- `orchestrator/` - Multi-agent coordination
- `main.py` - FastAPI application

## Learning Path

1. **Phase 1**: PR Reviewer Agent (single agent with tools)
2. **Phase 2**: Add Fixer Agent (multi-agent communication)
3. **Phase 3**: Full SDLC automation

See `docs/agentic-sdlc-learning-guide.md` for full guide.
