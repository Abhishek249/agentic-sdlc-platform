"""Base agent implementation with ReAct loop."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

import structlog
from openai import AsyncOpenAI

from tools import Tool, ToolExecutionError

logger = structlog.get_logger()


@dataclass
class AgentStep:
    """
    A single step in the agent's execution.
    
    Tracks thought → action → observation for debugging/observability.
    """
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Final result from agent execution."""
    success: bool
    answer: str
    steps: List[AgentStep]
    total_steps: int
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base agent with ReAct (Reason + Act) loop.
    
    Architecture (as you designed it!):
    - Each phase (think, act, observe, decide) is its own async method
    - Methods can run independently without blocking
    - Multiple agent instances can execute concurrently
    """
    
    def __init__(
        self,
        name: str,
        tools: List[Tool],
        model: str = "gpt-4o",
        max_steps: int = 10,
        temperature: float = 0.7
    ):
        self.name = name
        self.tools = {t.name: t for t in tools}
        self.model = model
        self.max_steps = max_steps
        self.temperature = temperature
        
        # OpenAI client (async for non-blocking)
        self.client = AsyncOpenAI()
        
        # Execution state
        self.steps: List[AgentStep] = []
        self.context: List[Dict[str, str]] = []
        
        # Logger with agent context
        self.logger = logger.bind(agent=name)
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """
        System prompt that defines agent's role and behavior.
        
        Subclasses must implement this - it's the agent's "personality"!
        """
        raise NotImplementedError
    
    async def execute(self, task: str) -> AgentResult:
        """
        Main execution loop - orchestrates think → act → observe cycle.
        
        This is async so multiple agents can run concurrently without blocking.
        """
        self.logger.info("agent_started", task=task)
        
        # Reset state
        self.steps = []
        self.context = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {task}"}
        ]
        
        try:
            for step_num in range(1, self.max_steps + 1):
                self.logger.debug("step_started", step=step_num)
                
                # 1. THINK - What should I do next?
                thought, action_decision = await self.think()
                
                current_step = AgentStep(
                    step_number=step_num,
                    thought=thought
                )
                
                # 2. DECIDE - Am I done or should I act?
                if await self.is_finished(action_decision):
                    self.logger.info("agent_finished", steps=step_num)
                    return AgentResult(
                        success=True,
                        answer=action_decision,
                        steps=self.steps,
                        total_steps=step_num
                    )
                
                # 3. ACT - Execute the chosen action
                action_result = await self.act(action_decision)
                current_step.action = action_result.get("action")
                current_step.action_input = action_result.get("input")
                
                # 4. OBSERVE - Get the result
                observation = await self.observe(action_result)
                current_step.observation = observation
                
                self.steps.append(current_step)
                
                # Add to context for next iteration
                self.context.append({
                    "role": "assistant",
                    "content": f"Thought: {thought}\nAction: {action_result}\nObservation: {observation}"
                })
            
            # Max steps reached
            self.logger.warning("max_steps_reached", max_steps=self.max_steps)
            return AgentResult(
                success=False,
                answer="Max steps reached without completing task",
                steps=self.steps,
                total_steps=self.max_steps,
                error="Max steps exceeded"
            )
            
        except Exception as e:
            self.logger.error("agent_failed", error=str(e))
            return AgentResult(
                success=False,
                answer="",
                steps=self.steps,
                total_steps=len(self.steps),
                error=str(e)
            )
    
    async def think(self) -> tuple[str, str]:
        """
        THINK phase - LLM reasons about what to do next.
        
        Returns:
            (thought, action_or_answer): The reasoning and decision
        """
        try:
            # Call LLM with function calling
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=self.context,
                tools=[t.to_openai_schema() for t in self.tools.values()],
                tool_choice="auto",  # LLM decides if it needs a tool
                temperature=self.temperature
            )
            
            message = response.choices[0].message
            
            # Extract thought (reasoning)
            thought = message.content or "Proceeding with action..."
            
            # Check if LLM wants to use a tool or give final answer
            if message.tool_calls:
                # LLM wants to call a tool
                return thought, json.dumps({
                    "tool": message.tool_calls[0].function.name,
                    "arguments": json.loads(message.tool_calls[0].function.arguments)
                })
            else:
                # LLM giving final answer
                return thought, message.content or ""
            
        except Exception as e:
            self.logger.error("think_failed", error=str(e))
            raise
    
    async def act(self, action_decision: str) -> Dict[str, Any]:
        """
        ACT phase - Execute the chosen tool.
        
        This is where the agent actually DOES something in the world.
        """
        try:
            # Parse action decision
            action_data = json.loads(action_decision)
            tool_name = action_data["tool"]
            arguments = action_data["arguments"]
            
            self.logger.info("executing_tool", tool=tool_name, args=arguments)
            
            # Get tool
            if tool_name not in self.tools:
                return {
                    "action": tool_name,
                    "input": arguments,
                    "error": f"Tool {tool_name} not found"
                }
            
            tool = self.tools[tool_name]
            
            # Execute tool (async!)
            result = await tool.execute(**arguments)
            
            return {
                "action": tool_name,
                "input": arguments,
                "result": result
            }
            
        except json.JSONDecodeError:
            # Not a tool call, probably final answer
            return {
                "action": "final_answer",
                "input": {},
                "result": action_decision
            }
        except ToolExecutionError as e:
            self.logger.error("tool_failed", error=str(e))
            return {
                "action": action_data.get("tool", "unknown"),
                "input": action_data.get("arguments", {}),
                "error": str(e)
            }
        except Exception as e:
            self.logger.error("act_failed", error=str(e))
            return {
                "action": "error",
                "input": {},
                "error": str(e)
            }
    
    async def observe(self, action_result: Dict[str, Any]) -> str:
        """
        OBSERVE phase - Process the tool result.
        
        Converts tool output into observation text for the LLM.
        """
        if "error" in action_result:
            return f"❌ Error: {action_result['error']}"
        
        if "result" in action_result:
            result = action_result["result"]
            
            # Limit observation size (LLMs have token limits)
            max_chars = 10000
            if isinstance(result, str) and len(result) > max_chars:
                result = result[:max_chars] + f"\n... (truncated {len(result) - max_chars} chars)"
            
            return f"✅ Result: {result}"
        
        return "No result"
    
    async def is_finished(self, decision: str) -> bool:
        """
        DECIDE phase - Check if agent is done.
        
        Returns True if this is the final answer, False if more work needed.
        """
        try:
            # If decision is JSON (tool call), not finished
            json.loads(decision)
            return False
        except (json.JSONDecodeError, TypeError):
            # Not a tool call, this is the final answer
            return True


class PRReviewerAgent(BaseAgent):
    """
    Specialized agent for reviewing pull requests.
    
    This agent knows how to:
    - Read git diffs
    - Check code quality
    - Review for bugs and issues
    - Provide structured feedback
    """
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert code reviewer specializing in Python.

Your job is to review code changes (pull requests) and provide helpful feedback.

Available tools:
- git_diff: See what changed in the code
- read_file: Read full file contents for context
- run_linter: Check for style/quality issues
- git_log: See commit history

Review process:
1. Use git_diff to see what changed
2. For significant changes, use read_file to understand context
3. Run run_linter to check for code quality issues
4. Provide a structured review with:
   - Summary of changes
   - Issues found (bugs, style, security, etc.)
   - Suggestions for improvement
   - Approval recommendation (approve/request changes)

Be constructive and helpful. Focus on important issues, not nitpicks.
When you have completed your review, provide your final assessment."""


# Example usage (we'll add more agents later)
__all__ = ["BaseAgent", "PRReviewerAgent", "AgentResult", "AgentStep"]
