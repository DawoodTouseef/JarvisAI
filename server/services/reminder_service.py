from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from server.agents.reminder_agent import RemAgent

_reminder_agent: Optional[RemAgent] = None


def get_reminder_agent() -> RemAgent:
    global _reminder_agent
    if _reminder_agent is None:
        from server.agents.reminder_agent import RemAgent
        _reminder_agent = RemAgent()
    return _reminder_agent
