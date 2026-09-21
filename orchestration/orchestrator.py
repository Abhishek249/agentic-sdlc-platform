"""
Orchestrator - Coordinates multi-agent workflows.

The "conductor" of the agent orchestra!
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from messaging import Message, message_bus
from agents.observable import ObservableAgent
import structlog
import asyncio

logger = structlog.get_logger()


@dataclass
class WorkflowStep:
    """A step in a multi-agent workflow."""
    agent_type: str  # "reviewer", "fixer", etc.
    depends_on: List[str]  # Agent IDs that must complete first
    config: Dict[str, Any]


class Orchestrator:
    """
    Orchestrates multi-agent workflows.
    
    Example workflow:
    1. Reviewer Agent reviews code
    2. If issues found, Fixer Agent fixes them
    3. Reviewer re-reviews the fixes
    4. Report final status
    """
    
    def __init__(self, broadcast_fn=None):
        self.broadcast = broadcast_fn or self._no_op_broadcast
        self.active_agents: Dict[str, ObservableAgent] = {}
        
        # Listen to all messages for orchestration
        message_bus.add_observer(self._handle_message)
    
    async def run_review_and_fix_workflow(
        self,
        reviewer_agent: ObservableAgent,
        fixer_agent: ObservableAgent,
        repo_path: str,
        target_branch: str,
        auto_fix: bool = True
    ) -> Dict[str, Any]:
        """
        Run the Review → Fix workflow.
        
        1. Reviewer reviews code
        2. If issues found and auto_fix=True, Fixer fixes them
        3. Reviewer re-reviews
        4. Return final results
        """
        logger.info(
            "workflow_started",
            workflow="review_and_fix",
            repo=repo_path
        )
        
        # Broadcast workflow start
        await self.broadcast({
            "event": "workflow_started",
            "workflow": "review_and_fix",
            "repo": repo_path,
            "agents": ["reviewer", "fixer"]
        })
        
        # Step 1: Initial Review
        logger.info("workflow_step", step=1, action="initial_review")
        task = f"Review the code changes in {repo_path} compared to {target_branch}"
        
        reviewer_result = await reviewer_agent.execute(task)
        
        # Extract issues from review
        issues = self._extract_issues_from_review(reviewer_result)
        
        if not issues or not auto_fix:
            # No issues or auto-fix disabled
            logger.info("workflow_complete", issues_found=len(issues), auto_fix=auto_fix)
            
            await self.broadcast({
                "event": "workflow_completed",
                "workflow": "review_and_fix",
                "steps_completed": 1,
                "issues_found": len(issues),
                "fixes_applied": 0
            })
            
            return {
                "success": True,
                "workflow": "review_and_fix",
                "steps": [
                    {
                        "step": "initial_review",
                        "agent": "reviewer",
                        "issues_found": len(issues)
                    }
                ],
                "final_status": "approved" if not issues else "needs_fixes"
            }
        
        # Step 2: Send fix request to Fixer Agent
        logger.info("workflow_step", step=2, action="send_fix_request")
        
        # Send message from Reviewer to Fixer
        fix_request = Message(
            from_agent="reviewer",
            to_agent="fixer",
            message_type="request",
            content={
                "issues": issues,
                "repo_path": repo_path,
                "target_branch": target_branch
            }
        )
        
        await message_bus.send(fix_request)
        
        # Broadcast inter-agent message
        await self.broadcast({
            "event": "agent_message",
            "from_agent": "reviewer",
            "to_agent": "fixer",
            "message_type": "fix_request",
            "issues_count": len(issues)
        })
        
        # Step 3: Fixer applies fixes
        logger.info("workflow_step", step=3, action="apply_fixes")
        
        # Execute fixer (it will receive the message and process)
        fixer_task = f"Apply fixes for issues in {repo_path}"
        fixer_result = await fixer_agent.execute(fixer_task)
        
        # Step 4: Re-review
        logger.info("workflow_step", step=4, action="re_review")
        
        re_review_result = await reviewer_agent.execute(
            f"Re-review {repo_path} after fixes were applied"
        )
        
        # Workflow complete!
        logger.info("workflow_complete", steps=4)
        
        await self.broadcast({
            "event": "workflow_completed",
            "workflow": "review_and_fix",
            "steps_completed": 4,
            "issues_found": len(issues),
            "fixes_applied": len(self._extract_fixes(fixer_result))
        })
        
        return {
            "success": True,
            "workflow": "review_and_fix",
            "steps": [
                {
                    "step": "initial_review",
                    "agent": "reviewer",
                    "issues_found": len(issues)
                },
                {
                    "step": "apply_fixes",
                    "agent": "fixer",
                    "fixes_applied": len(self._extract_fixes(fixer_result))
                },
                {
                    "step": "re_review",
                    "agent": "reviewer",
                    "final_status": "approved" if re_review_result.success else "needs_review"
                }
            ],
            "messages_exchanged": 1,
            "final_status": "approved" if re_review_result.success else "needs_review"
        }
    
    async def _handle_message(self, message: Message):
        """Handle messages for orchestration visibility."""
        # Broadcast message to dashboard
        await self.broadcast({
            "event": "agent_message",
            "message_id": message.id,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "message_type": message.message_type,
            "timestamp": message.timestamp.isoformat()
        })
    
    def _extract_issues_from_review(self, result) -> List[Dict[str, Any]]:
        """Extract issues from reviewer result."""
        # Parse the review text for issues
        # (In production, you'd have structured output)
        issues = []
        
        # Look for common issue patterns
        review_text = result.answer.lower()
        
        if "issue" in review_text or "problem" in review_text or "fix" in review_text:
            # Found some issues (simplified extraction)
            issues.append({
                "description": "Code quality issues found",
                "severity": "medium"
            })
        
        return issues
    
    def _extract_fixes(self, result) -> List[str]:
        """Extract fixes from fixer result."""
        fixes = []
        for step in result.execution_steps:
            if step.action == "write_file":
                fixes.append(f"Modified file")
        return fixes
    
    async def _no_op_broadcast(self, message: dict):
        """Default no-op broadcast."""
        pass
