# 🤖↔️🤖 Phase 2: Multi-Agent Communication

## What's New

**Phase 2 adds agent-to-agent communication!** Agents can now talk to each other, coordinate work, and collaborate on tasks.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Message Bus                              │
│          (Central Communication Hub)                         │
└──┬───────────────────────────────────────────────────┬──────┘
   │                                                    │
   │  subscribe                              subscribe │
   │                                                    │
┌──▼──────────────┐                         ┌─────────▼──────┐
│  Reviewer Agent │─────── send message ───▶│  Fixer Agent   │
│                 │         (fix_request)    │                │
│  - Reviews code │                          │  - Fixes issues│
│  - Finds issues │◀──── send response ─────│  - Reports back│
│  - Re-reviews   │       (fix_complete)     │                │
└─────────────────┘                          └────────────────┘
        │                                            │
        └────────────┬───────────────────────────────┘
                     │
              ┌──────▼──────┐
              │ Orchestrator│
              │ (Coordinator)│
              └─────────────┘
                     │
              ┌──────▼──────┐
              │  Dashboard  │
              │  (Watches)  │
              └─────────────┘
```

## Key Components

### 1. Message Bus (`messaging/message_bus.py`)

**The Post Office for Agents!**

```python
class Message:
    from_agent: str      # Who sent it
    to_agent: str        # Who receives it
    message_type: str    # "request", "response", "broadcast"
    content: dict        # The actual message
    correlation_id: str  # Link request/response

class MessageBus:
    async def send(message)           # Send a message
    def subscribe(agent_id, handler)  # Agent registers to receive
    def add_observer(callback)        # Dashboard watches all messages
```

**How it works:**
1. Agents subscribe to the bus with their ID
2. When a message arrives for them, their handler is called
3. Observers (like the dashboard) watch ALL traffic
4. Message history is kept for debugging

### 2. Fixer Agent (`agents/fixer.py`)

**Automatically fixes issues found by reviewers!**

```python
class FixerAgent(BaseAgent):
    """Fixes code issues identified by reviewers."""
    
    async def _handle_message(message):
        # Receives fix request
        issues = message.content["issues"]
        
        # Apply fixes using tools
        result = await self.execute(fix_task)
        
        # Send response back
        response = Message(
            from_agent="fixer",
            to_agent=message.from_agent,
            message_type="response",
            content={"fixes_applied": [...]}
        )
        await message_bus.send(response)
```

**Capabilities:**
- Receives fix requests via message bus
- Uses same tools as reviewer (read/write files, linters, etc.)
- Reports back what was fixed
- Conservative (won't break working code)

### 3. Orchestrator (`orchestration/orchestrator.py`)

**The Conductor of the Agent Orchestra!**

```python
class Orchestrator:
    async def run_review_and_fix_workflow(
        reviewer_agent,
        fixer_agent,
        repo_path,
        auto_fix=True
    ):
        # Step 1: Review
        review = await reviewer_agent.execute(review_task)
        
        # Step 2: Extract issues
        issues = extract_issues(review)
        
        # Step 3: Send fix request
        await message_bus.send(Message(
            from_agent="reviewer",
            to_agent="fixer",
            message_type="request",
            content={"issues": issues}
        ))
        
        # Step 4: Fixer applies fixes
        await fixer_agent.execute(fix_task)
        
        # Step 5: Re-review
        final_review = await reviewer_agent.execute(re_review_task)
        
        return result
```

**Workflow Steps:**
1. **Initial Review** — Reviewer finds issues
2. **Message Passing** — Reviewer sends issues to Fixer
3. **Apply Fixes** — Fixer fixes the issues
4. **Re-Review** — Reviewer verifies fixes
5. **Report** — Return final status

### 4. Dashboard Updates

**New Section: Agent Communication Flow**

Shows messages flowing between agents in real-time!

```
🔄 Agent Communication Flow
┌────────────────────────────────────────────────┐
│ Reviewer  →  fix_request (3 issues)  →  Fixer │
│ Reviewer  ←  fix_complete (3 fixed)  ←  Fixer │
└────────────────────────────────────────────────┘
```

**What you see:**
- Who sent the message
- Who received it
- Message type and content summary
- Timestamp
- Animated arrows showing direction

## How to Use

### Option 1: Single Agent (Phase 1)

```bash
curl -X POST http://localhost:8888/agent/review \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/path/to/repo",
    "target_branch": "main"
  }'
```

**What happens:**
- One Reviewer Agent runs
- Reviews code and reports issues
- No fixing

### Option 2: Multi-Agent Workflow (Phase 2) 🆕

```bash
curl -X POST http://localhost:8888/agent/review-and-fix \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/path/to/repo",
    "target_branch": "main",
    "auto_fix": true
  }'
```

**What happens:**
1. Reviewer Agent reviews code
2. Finds issues
3. Sends message to Fixer Agent via message bus
4. Fixer Agent receives message and applies fixes
5. Fixer Agent sends completion message back
6. Reviewer Agent re-reviews
7. Returns final status

**Watch in Dashboard:**
- Both agents appear as cards
- Message flow shows communication
- Live trace shows each step
- You see the conversation happen!

## Message Types

### Request
```json
{
  "from_agent": "reviewer",
  "to_agent": "fixer",
  "message_type": "request",
  "content": {
    "issues": [
      {"description": "Unused import", "file": "app.py", "line": 5},
      {"description": "Missing type hint", "file": "utils.py", "line": 12}
    ],
    "repo_path": "/path/to/repo"
  }
}
```

### Response
```json
{
  "from_agent": "fixer",
  "to_agent": "reviewer",
  "message_type": "response",
  "content": {
    "status": "completed",
    "fixes_applied": ["Removed unused import", "Added type hint"],
    "fixes_skipped": []
  },
  "correlation_id": "original-request-id"
}
```

### Broadcast
```json
{
  "from_agent": "orchestrator",
  "to_agent": "*",
  "message_type": "broadcast",
  "content": {
    "event": "workflow_started",
    "workflow": "review_and_fix"
  }
}
```

## What You Learn

### Software Engineering Patterns

1. **Message Bus Pattern**
   - Decoupled communication
   - Pub/sub architecture
   - Event-driven design

2. **Observer Pattern**
   - Dashboard observes all messages
   - No direct coupling between agents and UI
   - Scalable observability

3. **Orchestration**
   - Workflow coordination
   - State management
   - Error handling

4. **Async Communication**
   - Non-blocking message passing
   - Concurrent agent execution
   - Race condition handling

### Multi-Agent Concepts

1. **Agent Autonomy**
   - Each agent is independent
   - Agents don't know about each other directly
   - Communication through messages only

2. **Collaboration**
   - Agents work together on tasks
   - Division of labor (one reviews, one fixes)
   - Coordinated workflows

3. **Message Protocols**
   - Structured message formats
   - Request/response correlation
   - Error handling in messages

## Testing the System

### Test 1: Simple Review (No Issues)

```bash
curl -X POST http://localhost:8888/agent/review-and-fix \
  -d '{"repo_path": "/path/to/clean/repo", "target_branch": "main"}'
```

**Expected:**
- Reviewer runs
- Finds no issues
- Workflow completes early
- No messages sent to Fixer

### Test 2: Review with Auto-Fix

```bash
curl -X POST http://localhost:8888/agent/review-and-fix \
  -d '{"repo_path": "/path/to/repo/with/issues", "target_branch": "main", "auto_fix": true}'
```

**Expected:**
- Reviewer finds issues
- Sends fix_request message to Fixer
- Fixer applies fixes
- Sends fix_complete message back
- Reviewer re-reviews
- Dashboard shows message flow!

### Test 3: Review Only (No Auto-Fix)

```bash
curl -X POST http://localhost:8888/agent/review-and-fix \
  -d '{"repo_path": "/path/to/repo", "auto_fix": false}'
```

**Expected:**
- Reviewer runs
- Finds issues but doesn't fix
- No messages sent
- Returns list of issues

## Extending the System

### Add Your Own Agent

```python
from agents.base import BaseAgent
from messaging import Message, message_bus

class MyCustomAgent(BaseAgent):
    def __init__(self, agent_id, tools, **kwargs):
        super().__init__(
            name=f"My Agent ({agent_id})",
            tools=tools,
            system_prompt="You are a custom agent...",
            **kwargs
        )
        self.agent_id = agent_id
        
        # Subscribe to messages
        message_bus.subscribe(agent_id, self._handle_message)
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages."""
        if message.message_type == "request":
            # Process request
            result = await self.execute(task)
            
            # Send response
            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="response",
                content={"result": result}
            )
            await message_bus.send(response)
```

### Add Your Own Workflow

```python
async def my_custom_workflow(
    agent1: ObservableAgent,
    agent2: ObservableAgent,
    orchestrator: Orchestrator
):
    # Step 1: Agent 1 does something
    result1 = await agent1.execute(task1)
    
    # Step 2: Send message to Agent 2
    await message_bus.send(Message(
        from_agent="agent1",
        to_agent="agent2",
        message_type="request",
        content={"data": result1}
    ))
    
    # Step 3: Agent 2 processes
    result2 = await agent2.execute(task2)
    
    return {"agent1": result1, "agent2": result2}
```

## What's Next? (Phase 3)

### Planned Features:

1. **More Agents**
   - Tester Agent (runs tests)
   - Deployer Agent (deploys code)
   - Monitor Agent (watches production)

2. **Advanced Communication**
   - Agent groups (broadcast to team)
   - Priority messages
   - Message queues

3. **Workflow Engine**
   - Visual workflow builder
   - Conditional branching
   - Parallel execution

4. **Dashboard Enhancements**
   - Interactive flow diagram (drag agents)
   - Message replay
   - Agent performance metrics
   - Cost tracking per agent

5. **Production Features**
   - Message persistence
   - Agent state snapshots
   - Distributed agents (across machines)
   - Authentication & authorization

## Debugging

### View Message History

```python
from messaging import message_bus

# Get all messages
messages = message_bus.get_all_messages(limit=100)

# Get conversation between two agents
convo = message_bus.get_conversation("reviewer", "fixer", limit=50)
```

### Watch Live Messages

Open dashboard → "Agent Communication Flow" section shows live messages!

### Check Logs

```bash
# Server logs show all message activity
tail -f /path/to/server.log | grep message_sent
```

---

## 🎉 You Now Have Multi-Agent Communication!

**Phase 1:** ✅ Single agent with tools  
**Phase 2:** ✅ **Multi-agent communication** 👈 YOU ARE HERE  
**Phase 3:** 🚧 Full SDLC automation (coming soon)

**Your agents can now talk, collaborate, and work together!** 🤖🤝🤖

Open `http://localhost:8888` and watch them communicate in real-time!
