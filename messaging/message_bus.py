"""
Message Bus - Central communication hub for agent-to-agent messaging.

This is the "nervous system" of the multi-agent system!
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import uuid
import structlog

logger = structlog.get_logger()


@dataclass
class Message:
    """A message passed between agents."""
    
    from_agent: str
    to_agent: str
    message_type: str  # "request", "response", "broadcast", "notification"
    content: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None  # Link request/response
    
    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id
        }


class MessageBus:
    """
    Central message bus for agent communication.
    
    Think of this as a post office:
    - Agents send messages through the bus
    - Bus routes messages to recipients
    - Observers can watch all traffic (for dashboard!)
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}  # agent_id -> [handlers]
        self.observers: List[Callable] = []  # Dashboard listeners
        self.message_history: List[Message] = []
        self.max_history = 1000
        
    async def send(self, message: Message):
        """
        Send a message from one agent to another.
        
        This is like putting a letter in the mailbox!
        """
        logger.info(
            "message_sent",
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            message_type=message.message_type
        )
        
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Notify observers (dashboard!)
        await self._notify_observers(message)
        
        # Deliver to recipient
        if message.to_agent in self.subscribers:
            for handler in self.subscribers[message.to_agent]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(
                        "message_delivery_failed",
                        error=str(e),
                        message_id=message.id
                    )
    
    def subscribe(self, agent_id: str, handler: Callable):
        """
        Subscribe an agent to receive messages.
        
        Like giving the post office your address!
        """
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)
        
        logger.info("agent_subscribed", agent_id=agent_id)
    
    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent from messages."""
        if agent_id in self.subscribers:
            del self.subscribers[agent_id]
            logger.info("agent_unsubscribed", agent_id=agent_id)
    
    def add_observer(self, observer: Callable):
        """
        Add an observer (like the dashboard) that watches all messages.
        
        Like a security camera watching all the mail!
        """
        self.observers.append(observer)
    
    def remove_observer(self, observer: Callable):
        """Remove an observer."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    async def _notify_observers(self, message: Message):
        """Notify all observers about a message."""
        for observer in self.observers:
            try:
                await observer(message)
            except Exception as e:
                logger.error("observer_notification_failed", error=str(e))
    
    async def broadcast(self, from_agent: str, content: Dict[str, Any]):
        """
        Broadcast a message to all subscribed agents.
        
        Like shouting in a room!
        """
        message = Message(
            from_agent=from_agent,
            to_agent="*",  # Broadcast
            message_type="broadcast",
            content=content
        )
        
        # Send to all subscribers
        for agent_id in self.subscribers.keys():
            if agent_id != from_agent:  # Don't send to self
                message.to_agent = agent_id
                await self.send(message)
    
    def get_conversation(
        self,
        agent1: str,
        agent2: str,
        limit: int = 50
    ) -> List[Message]:
        """
        Get message history between two agents.
        
        Like reading old letters!
        """
        messages = [
            msg for msg in self.message_history
            if (msg.from_agent == agent1 and msg.to_agent == agent2)
            or (msg.from_agent == agent2 and msg.to_agent == agent1)
        ]
        return messages[-limit:]
    
    def get_all_messages(self, limit: int = 100) -> List[Message]:
        """Get recent message history."""
        return self.message_history[-limit:]


# Global message bus instance
# (In production, you'd inject this via dependency injection)
message_bus = MessageBus()
