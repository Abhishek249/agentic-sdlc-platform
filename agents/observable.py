"""Observable agent wrapper for real-time dashboard updates."""

from typing import Optional, Callable, Dict, Any
from agents.base import BaseAgent, AgentResult
import uuid


class ObservableAgent:
    """
    Wraps an agent and broadcasts execution updates.
    
    This is how we get real-time updates to the dashboard!
    """
    
    def __init__(
        self,
        agent: BaseAgent,
        broadcast_fn: Optional[Callable] = None
    ):
        self.agent = agent
        self.broadcast = broadcast_fn or self._no_op_broadcast
        self.execution_id = str(uuid.uuid4())
    
    async def execute(self, task: str) -> AgentResult:
        """Execute agent with real-time updates."""
        
        # Broadcast start
        await self.broadcast({
            "event": "agent_started",
            "agent_id": self.execution_id,
            "agent_name": self.agent.name,
            "task": task
        })
        
        # Monkey-patch the agent's methods to broadcast updates
        original_think = self.agent.think
        original_act = self.agent.act
        original_observe = self.agent.observe
        
        async def think_with_broadcast():
            await self.broadcast({
                "event": "step_update",
                "agent_id": self.execution_id,
                "agent_name": self.agent.name,
                "step": len(self.agent.steps) + 1,
                "total_steps": self.agent.max_steps,
                "phase": "thinking"
            })
            return await original_think()
        
        async def act_with_broadcast(action_decision: str):
            result = await original_act(action_decision)
            
            if "action" in result and result["action"] != "final_answer":
                await self.broadcast({
                    "event": "step_update",
                    "agent_id": self.execution_id,
                    "agent_name": self.agent.name,
                    "step": len(self.agent.steps),
                    "total_steps": self.agent.max_steps,
                    "phase": "acting",
                    "tool": result.get("action"),
                    "tool_input": str(result.get("input", {}))
                })
            
            return result
        
        async def observe_with_broadcast(action_result: Dict[str, Any]):
            observation = await original_observe(action_result)
            
            await self.broadcast({
                "event": "step_update",
                "agent_id": self.execution_id,
                "agent_name": self.agent.name,
                "step": len(self.agent.steps),
                "total_steps": self.agent.max_steps,
                "phase": "observing",
                "observation": observation[:200]  # Limit size
            })
            
            return observation
        
        # Apply monkey patches
        self.agent.think = think_with_broadcast
        self.agent.act = act_with_broadcast
        self.agent.observe = observe_with_broadcast
        
        # Execute agent
        try:
            result = await self.agent.execute(task)
            
            # Broadcast completion
            await self.broadcast({
                "event": "agent_completed",
                "agent_id": self.execution_id,
                "agent_name": self.agent.name,
                "status": "success" if result.success else "failed",
                "steps_taken": result.total_steps,
                "error": result.error
            })
            
            return result
            
        except Exception as e:
            # Broadcast failure
            await self.broadcast({
                "event": "agent_completed",
                "agent_id": self.execution_id,
                "agent_name": self.agent.name,
                "status": "failed",
                "error": str(e)
            })
            raise
        finally:
            # Restore original methods
            self.agent.think = original_think
            self.agent.act = original_act
            self.agent.observe = original_observe
    
    async def _no_op_broadcast(self, message: dict):
        """Default no-op broadcast if none provided."""
        pass
