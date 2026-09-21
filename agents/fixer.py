"""
Fixer Agent - Automatically fixes issues found by Reviewer Agent.

This agent:
1. Listens for messages from Reviewer Agent
2. Receives list of issues to fix
3. Applies fixes using tools
4. Reports back with results
"""

from agents.base import BaseAgent
from messaging import Message, message_bus
from typing import Dict, Any
import structlog

logger = structlog.get_logger()


class FixerAgent(BaseAgent):
    """
    Agent that fixes code issues identified by reviewers.
    
    Workflow:
    1. Reviewer finds issues
    2. Reviewer sends "fix_request" message
    3. Fixer receives message and fixes issues
    4. Fixer sends "fix_complete" message back
    """
    
    def __init__(self, agent_id: str, tools: list, **kwargs):
        system_prompt = """You are a Code Fixer Agent.

Your job is to automatically fix code issues reported by the Reviewer Agent.

When you receive a fix request with issues:
1. Analyze each issue carefully
2. Use the appropriate tools to fix them
3. Verify the fix was successful
4. Report back with what you did

Available actions:
- write_file: Modify files to fix issues
- read_file: Read files to understand context
- run_linter: Verify fixes don't introduce new issues
- run_type_checker: Ensure type safety

You should:
- Fix issues automatically when straightforward
- Skip issues that require human judgment
- Report all actions taken
- Be conservative (don't break working code!)

When finished, respond with action: "send_message" to report back.

Example response:
{
    "action": "write_file",
    "input": {
        "file_path": "/path/to/file.py",
        "content": "fixed code here"
    }
}

Or when done:
{
    "action": "send_message",
    "input": {
        "to_agent": "reviewer",
        "content": {
            "status": "completed",
            "fixes_applied": ["Fixed unused import", "Added type hints"],
            "fixes_skipped": ["Complex refactoring needed"]
        }
    }
}
"""
        
        super().__init__(
            name=f"Fixer Agent ({agent_id})",
            tools=tools,
            system_prompt=system_prompt,
            **kwargs
        )
        
        self.agent_id = agent_id
        self.current_fix_request: Dict[str, Any] = {}
        
        # Subscribe to message bus
        message_bus.subscribe(agent_id, self._handle_message)
    
    async def _handle_message(self, message: Message):
        """
        Handle incoming messages from other agents.
        
        This is called when another agent sends us a message!
        """
        logger.info(
            "fixer_received_message",
            from_agent=message.from_agent,
            message_type=message.message_type
        )
        
        if message.message_type == "request":
            # It's a fix request!
            await self._handle_fix_request(message)
    
    async def _handle_fix_request(self, message: Message):
        """Handle a fix request from Reviewer."""
        self.current_fix_request = message.content
        
        # Extract issues to fix
        issues = message.content.get("issues", [])
        repo_path = message.content.get("repo_path", "")
        
        # Build task
        task = f"""Fix the following issues in {repo_path}:

Issues to fix:
{self._format_issues(issues)}

Apply fixes carefully and report back when done.
"""
        
        # Execute the fixing!
        result = await self.execute(task)
        
        # Send response back to reviewer
        response_message = Message(
            from_agent=self.agent_id,
            to_agent=message.from_agent,
            message_type="response",
            content={
                "status": "completed" if result.success else "failed",
                "fixes_applied": self._extract_fixes(result),
                "error": result.error
            },
            correlation_id=message.id
        )
        
        await message_bus.send(response_message)
    
    def _format_issues(self, issues: list) -> str:
        """Format issues for prompt."""
        formatted = []
        for i, issue in enumerate(issues, 1):
            formatted.append(f"{i}. {issue.get('description', 'Unknown issue')}")
            if 'file' in issue:
                formatted.append(f"   File: {issue['file']}")
            if 'line' in issue:
                formatted.append(f"   Line: {issue['line']}")
        return "\n".join(formatted)
    
    def _extract_fixes(self, result) -> list:
        """Extract what fixes were applied from result."""
        fixes = []
        for step in result.execution_steps:
            if step.action in ["write_file", "git_commit"]:
                fixes.append(f"Applied fix via {step.action}")
        return fixes
    
    async def send_message_to_agent(self, to_agent: str, content: dict):
        """Send a message to another agent."""
        message = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type="notification",
            content=content
        )
        await message_bus.send(message)


# Add "send_message" action to base agent
# This allows agents to communicate!
from tools.base import Tool

class SendMessageTool(Tool):
    """Tool for agents to send messages to each other."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    @property
    def name(self) -> str:
        return "send_message"
    
    @property
    def description(self) -> str:
        return "Send a message to another agent"
    
    @property
    def parameters(self) -> dict:
        return {
            "to_agent": "ID of the agent to send message to",
            "content": "Message content (dict)"
        }
    
    async def execute(self, to_agent: str, content: dict) -> str:
        """Send message via message bus."""
        message = Message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type="notification",
            content=content
        )
        await message_bus.send(message)
        return f"✅ Message sent to {to_agent}"
