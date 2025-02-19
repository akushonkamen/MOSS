"""事件系统包"""

from .event_bus import event_bus, EventType, Event

__all__ = ['event_bus', 'EventType', 'Event']
