"""FastAPI server for agentic system."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import structlog

from agents import PRReviewerAgent
from tools import (
    ReadFileTool,
    ListFilesTool,
    GitDiffTool,
    GitLogTool,
    RunLinterTool,
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentic-sdlc"}


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
            name=f"reviewer-{request.repo_path}",
            tools=tools,
            model=os.getenv("AGENT_MODEL", "gpt-4o"),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "10"))
        )
        
        # Execute agent (ASYNC! Non-blocking!)
        task = f"Review the code changes in {request.repo_path} compared to {request.target_branch}"
        result = await agent.execute(task)
        
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


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
