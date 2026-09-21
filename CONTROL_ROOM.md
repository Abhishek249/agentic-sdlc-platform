# 🚀 Agentic SDLC Platform - Control Room

![Agent Control Room](https://img.shields.io/badge/Status-Live-brightgreen)
![WebSocket](https://img.shields.io/badge/WebSocket-Enabled-blue)
![Python](https://img.shields.io/badge/Python-3.11+-blue)

**Your Mission Control for AI Agents** — Watch your agents think, act, and collaborate in real-time!

## 🎮 What is This?

This is a **multi-agent orchestration system** with a **real-time control room dashboard** — like watching a SpaceX rocket launch, but for AI agents building software!

### Features

✅ **Real-Time Agent Visualization** — See agents flow through Think → Act → Observe cycles  
✅ **Live Execution Trace** — Every thought, tool call, and observation streamed instantly  
✅ **WebSocket Architecture** — Non-blocking async communication  
✅ **Beautiful UI** — Dark theme, animations, SpaceX-inspired design  
✅ **Production-Ready** — FastAPI + async/await + structured logging  

---

## 🏃 Quick Start

### 1. Install Dependencies

```bash
cd agentic-system
pip install fastapi uvicorn openai python-dotenv structlog websockets
```

### 2. Set Your OpenAI API Key

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start the Control Room

```bash
python3 main.py
```

Server starts at `http://localhost:8000`

### 4. Open the Dashboard

Open your browser and navigate to:

```
http://localhost:8000
```

You'll see the **Control Room** interface!

---

## 🎯 How to Trigger an Agent

### Option 1: Via API

```bash
curl -X POST http://localhost:8000/agent/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/path/to/your/repo",
    "target_branch": "main",
    "current_branch": "feature-branch"
  }'
```

### Option 2: Via Python

```python
import requests

response = requests.post(
    "http://localhost:8000/agent/review",
    json={
        "repo_path": "/Users/ajain/pcp-repos/pcubed-pro-api",
        "target_branch": "develop",
        "current_branch": "feature/my-feature"
    }
)

print(response.json())
```

---

## 🎨 What You'll See in the Control Room

### 1. **Header Metrics**
- **Active Agents**: How many agents are running right now
- **Total Executions**: How many times agents have run
- **Success Rate**: Percentage of successful completions
- **Avg Duration**: Average execution time

### 2. **Agent Cards** (The Magic!)

Each active agent gets a card showing:

```
┌────────────────────────────────────┐
│ PR Reviewer Agent #1               │
│ Status: 🤔 THINKING                │
│ Step 3/10                          │
│                                    │
│  ┌──────┐  ▶  ┌──────┐  ▶  ┌──────┐ │
│  │THINK │     │ ACT  │     │OBSERVE││
│  └──────┘     └──────┘     └──────┘│
│        ↑ Active phase               │
│                                    │
│ Current Action:                    │
│ Executing: git_diff                │
└────────────────────────────────────┘
```

**The flow boxes animate** as the agent moves through phases!

### 3. **Live Trace Log**

```
[11:24:21] PR Reviewer #1: 🚀 Started execution
[11:24:21] PR Reviewer #1: 🤔 Thinking (step 1/10)...
[11:24:22] PR Reviewer #1: 🔧 Calling tool: git_diff
[11:24:22] PR Reviewer #1: 👀 Observed: No changes found
[11:24:23] PR Reviewer #1: ✅ Completed successfully!
```

Real-time updates stream in as they happen!

---

## 🏗️ Architecture

### The Tech Stack

- **FastAPI** — Async web framework
- **WebSockets** — Real-time bidirectional communication
- **OpenAI GPT-4** — Agent reasoning engine
- **Structured Logging** — `structlog` for observability
- **Pure HTML/JS** — No frontend frameworks needed!

### The Agent Flow

```
                    ┌──────────────┐
                    │   User/API   │
                    └──────┬───────┘
                           │
                    ┌──────▼────────┐
                    │  FastAPI      │
                    │  Endpoint     │
                    └──────┬────────┘
                           │
                    ┌──────▼────────┐
                    │ Observable    │
                    │ Agent Wrapper │◄──┐
                    └──────┬────────┘   │
                           │            │
          ┌────────────────┼────────┐   │
          │                │        │   │
    ┌─────▼─────┐   ┌─────▼────┐  ┌▼───▼───┐
    │   THINK   │──▶│   ACT    │─▶│ OBSERVE│
    │  (LLM)    │   │ (Tools)  │  │ (Parse)│
    └───────────┘   └──────────┘  └────────┘
          │                │           │
          └────────────────┼───────────┘
                           │
                    ┌──────▼────────┐
                    │  WebSocket    │
                    │  Broadcast    │
                    └──────┬────────┘
                           │
                    ┌──────▼────────┐
                    │  Dashboard    │
                    │  (Browser)    │
                    └───────────────┘
```

### Key Components

#### 1. **BaseAgent** (`agents/base.py`)
- ReAct reasoning loop
- Async methods: `think()`, `act()`, `observe()`, `is_finished()`
- OpenAI integration

#### 2. **ObservableAgent** (`agents/observable.py`)
- Wraps any BaseAgent
- Broadcasts updates via WebSocket
- Monkey-patches agent methods for observability

#### 3. **ConnectionManager** (`main.py`)
- Manages WebSocket connections
- Broadcasts to all connected dashboards
- Handles connect/disconnect

#### 4. **Dashboard** (`static/dashboard.html`)
- Pure JavaScript WebSocket client
- Real-time DOM updates
- Animations and visual effects

---

## 🔧 Adding Your Own Agent

### Step 1: Create Agent Class

```python
from agents.base import BaseAgent

class MyCustomAgent(BaseAgent):
    """Your specialized agent."""
    
    def __init__(self, tools, **kwargs):
        super().__init__(
            name="My Custom Agent",
            tools=tools,
            system_prompt="You are a specialized agent that...",
            **kwargs
        )
```

### Step 2: Add Endpoint

```python
@app.post("/agent/mycustom")
async def run_my_agent(request: MyRequest):
    """Run my custom agent."""
    
    # Create agent
    agent = MyCustomAgent(tools=my_tools)
    
    # Wrap with observable
    observable = ObservableAgent(agent, broadcast_fn=manager.broadcast)
    
    # Execute
    result = await observable.execute(task)
    
    return result
```

### Step 3: Watch in Control Room!

The dashboard automatically picks up ANY agent running through `ObservableAgent`!

---

## 🎓 Learning Notes

### Why Async?

```python
# ❌ BAD: Blocking (one agent at a time)
def execute(task):
    response = openai.chat.completions.create(...)  # Blocks!
    return response

# ✅ GOOD: Async (multiple agents concurrently)
async def execute(task):
    response = await openai.chat.completions.create(...)  # Non-blocking!
    return response
```

### Why WebSockets?

**HTTP (Old Way):**
- Client asks: "Any updates?"
- Server: "Nope"
- Client waits 1 second...
- Client asks again: "Now?"
- Server: "Nope"
- (Inefficient polling!)

**WebSocket (New Way):**
- Client: "Connect to me!"
- Server: "Connected!"
- Server pushes updates instantly when they happen
- (Efficient real-time!)

### Why ObservableAgent?

**Without Observable:**
```python
# Agent runs... but you have no idea what it's doing
result = await agent.execute(task)
# Finally done! But what happened?
```

**With Observable:**
```python
# Every step broadcasts to dashboard in real-time!
observable = ObservableAgent(agent, broadcast_fn=manager.broadcast)
result = await observable.execute(task)
# You watched it think, act, observe in real-time!
```

---

## 🚀 What's Next?

### Phase 1: Single Agent ✅ (Done!)
- [x] BaseAgent with ReAct loop
- [x] Tool system
- [x] Async execution
- [x] Real-time dashboard

### Phase 2: Multi-Agent Communication 🚧 (Next!)
- [ ] Agent-to-agent messaging
- [ ] Shared memory/context
- [ ] Orchestrator agent
- [ ] Dependency graph visualization

### Phase 3: Production Features 📋 (Future)
- [ ] Cost tracking per agent
- [ ] Token budgets
- [ ] Error recovery
- [ ] Caching layer
- [ ] Agent persistence
- [ ] Replay/time-travel debugging

---

## 🎬 Demo Video

**Coming soon!** We'll record a demo showing:
1. Starting the server
2. Opening the control room
3. Triggering multiple agents
4. Watching them execute in parallel
5. Seeing the live trace updates

---

## 📚 Documentation

- **Architecture**: See `docs/architecture.md` (coming soon)
- **Agent Guide**: See `docs/agents.md` (coming soon)
- **API Reference**: See `docs/api.md` (coming soon)

---

## 🤝 Contributing

This is a learning project! Feel free to:
- Add new agents
- Improve the dashboard
- Add features
- Fix bugs

---

## 📝 License

MIT License - Use this however you want!

---

## 🎯 Credits

Built with inspiration from:
- **SpaceX Mission Control** — UI design inspiration
- **LangChain** — Agent patterns
- **AutoGPT** — Multi-agent concepts
- **Dagster** — Orchestration UI patterns

---

**Now go build something amazing! 🚀**

Open `http://localhost:8000` and watch your agents work!