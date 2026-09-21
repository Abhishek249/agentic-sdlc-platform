"""Messaging package - Agent communication infrastructure."""

from messaging.message_bus import MessageBus, Message, message_bus

__all__ = ["MessageBus", "Message", "message_bus"]
