# Agentic SDLC System

Multi-agent orchestration system for automating software development lifecycle.

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
