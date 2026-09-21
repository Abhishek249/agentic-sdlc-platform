"""Base tool interface that all tools must implement."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""
    
    type: str = Field(..., description="Parameter type: string, integer, boolean, object, array")
    description: str = Field(..., description="What this parameter does")
    required: bool = Field(default=True, description="Whether parameter is required")
    enum: list[str] | None = Field(default=None, description="Allowed values if constrained")


class Tool(ABC):
    """
    Base class for all agent tools.
    
    Tools are functions that agents can call to interact with the world.
    Each tool must define:
    - name: Unique identifier
    - description: What it does (LLM reads this to decide when to use it)
    - parameters: What inputs it needs
    - execute(): What it actually does
    """
    
    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.parameters: Dict[str, ToolParameter] = {}
        self.is_deterministic: bool = True  # Can we cache results?
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        This is what actually runs when the agent calls the tool.
        Must be async for non-blocking I/O.
        """
        raise NotImplementedError
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        
        This is what we send to the LLM so it knows:
        - What tools are available
        - What each tool does
        - What parameters each tool needs
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param_name: {
                            "type": param.type,
                            "description": param.description,
                            **({"enum": param.enum} if param.enum else {})
                        }
                        for param_name, param in self.parameters.items()
                    },
                    "required": [
                        param_name 
                        for param_name, param in self.parameters.items() 
                        if param.required
                    ]
                }
            }
        }
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute."""
    
    def __init__(self, tool_name: str, error: str):
        self.tool_name = tool_name
        self.error = error
        super().__init__(f"Tool '{tool_name}' failed: {error}")
