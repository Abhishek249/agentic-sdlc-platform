"""FastAPI server for agentic system."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import structlog
import json
from typing import List

from agents import PRReviewerAgent, ObservableAgent
from agents.fixer import FixerAgent
from orchestration import Orchestrator
from messaging import message_bus
from tools import (
    ReadFileTool,
    ListFilesTool,
    GitDiffTool,
    GitLogTool,
    GitShowTool,
    WriteFileTool,
    RunLinterTool,
    RunTypeCheckerTool,
)

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("dashboard_connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("dashboard_disconnected", total_connections=len(self.active_connections))
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected dashboards."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("broadcast_failed", error=str(e))


manager = ConnectionManager()


# Request/Response models
class ReviewRequest(BaseModel):
    """Request to review code changes."""
    target_branch: str = Field(
        default="origin/main",
        description="Branch to compare against (e.g., 'origin/main', 'HEAD~1')"
    )
    repo_path: str = Field(
        default="pcubed-pro-api",
        description="Repository path relative to workspace"
    )


class ReviewAndFixRequest(BaseModel):
    """Request to run review + fix workflow."""
    repo_path: str = Field(..., description="Path to repository")
    target_branch: str = Field(default="main", description="Target branch to compare against")
    current_branch: str = Field(default="HEAD", description="Current branch to review")
    auto_fix: bool = Field(default=True, description="Automatically apply fixes")


class ReviewResponse(BaseModel):
    """Response from code review."""
    success: bool
    review: str
    steps_taken: int
    execution_steps: list[dict]


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle - startup/shutdown."""
    logger.info("server_starting")
    
    # Verify API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not set!")
        raise RuntimeError("OPENAI_API_KEY environment variable required")
    
    yield
    
    logger.info("server_shutdown")


# Create FastAPI app
app = FastAPI(
    title="Agentic SDLC Platform",
    description="Multi-agent system for automating software development lifecycle",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files for dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the control room dashboard."""
    return FileResponse("static/dashboard.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentic-sdlc"}


@app.post("/agent/review-and-fix")
async def run_review_and_fix_workflow(request: ReviewAndFixRequest):
    """
    Run the full Review → Fix workflow with two agents!
    
    Multi-agent communication demo - watch in dashboard!
    """
    try:
        logger.info("review_and_fix_workflow_requested", repo=request.repo_path)
        
        tools = [
            GitDiffTool(), GitLogTool(), GitShowTool(),
            ReadFileTool(), WriteFileTool(),
            RunLinterTool(), RunTypeCheckerTool()
        ]
        
        reviewer = PRReviewerAgent(name="PR Reviewer", tools=tools, model=os.getenv("AGENT_MODEL", "gpt-4o"), max_steps=10)
        observable_reviewer = ObservableAgent(reviewer, broadcast_fn=manager.broadcast)
        
        fixer = FixerAgent(agent_id="fixer", tools=tools, model=os.getenv("AGENT_MODEL", "gpt-4o"), max_steps=10)
        observable_fixer = ObservableAgent(fixer, broadcast_fn=manager.broadcast)
        
        orchestrator = Orchestrator(broadcast_fn=manager.broadcast)
        
        result = await orchestrator.run_review_and_fix_workflow(
            reviewer_agent=observable_reviewer,
            fixer_agent=observable_fixer,
            repo_path=request.repo_path,
            target_branch=request.target_branch,
            auto_fix=request.auto_fix
        )
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error("review_and_fix_workflow_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    """
    Review code changes using PR Reviewer Agent.
    
    This endpoint:
    1. Creates a PR Reviewer agent
    2. Gives it tools (git diff, linter, etc.)
    3. Executes the agent (non-blocking!)
    4. Returns the review
    
    Multiple requests can run concurrently - each gets its own agent instance!
    """
    try:
        logger.info("review_requested", target=request.target_branch, repo=request.repo_path)
        
        # Get workspace root
        workspace = os.getenv("WORKSPACE_ROOT", "/Users/ajain/pcp-repos")
        repo_root = os.path.join(workspace, request.repo_path)
        
        # Create tools for this agent
        tools = [
            GitDiffTool(repo_root=repo_root),
            GitLogTool(repo_root=repo_root),
            ReadFileTool(workspace_root=workspace),
            ListFilesTool(workspace_root=workspace),
            RunLinterTool(repo_root=repo_root),
        ]
        
        # Create agent
        agent = PRReviewerAgent(
            name=f"PR Reviewer #{request.repo_path}",
            tools=tools,
            model=os.getenv("AGENT_MODEL", "gpt-4o"),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "10"))
        )
        
        # Wrap with observable for real-time updates
        observable = ObservableAgent(agent, broadcast_fn=manager.broadcast)
        
        # Execute agent (ASYNC! Non-blocking! With live updates!)
        task = f"Review the code changes in {request.repo_path} compared to {request.target_branch}"
        result = await observable.execute(task)
        
        if not result.success:
            logger.error("review_failed", error=result.error)
            raise HTTPException(
                status_code=500,
                detail=f"Review failed: {result.error}"
            )
        
        logger.info("review_completed", steps=result.total_steps)
        
        return ReviewResponse(
            success=True,
            review=result.answer,
            steps_taken=result.total_steps,
            execution_steps=[
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation[:200] + "..." if s.observation and len(s.observation) > 200 else s.observation
                }
                for s in result.steps
            ]
        )
        
    except Exception as e:
        logger.exception("review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": [
            {
                "name": "PRReviewerAgent",
                "description": "Reviews pull requests for code quality, bugs, and best practices",
                "endpoint": "/agent/review"
            }
        ]
    }


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Sends agent execution updates to connected dashboards.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8888,  # Off the beaten path! 🎰
        reload=True,
        log_level="info"
    )
