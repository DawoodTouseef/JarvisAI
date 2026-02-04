from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class AgentState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class PermissionLevel(str, Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    BLOCKED = "BLOCKED"

class ActionIntent(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str
    permission_level: PermissionLevel = PermissionLevel.SAFE

class ExecutionPlan(BaseModel):
    steps: List[ActionIntent]
    total_steps: int
    estimated_time: float

class AgentEvent(BaseModel):
    event_type: str
    task_id:str
    payload: Dict[str, Any]
    timestamp: float = Field(default_factory=lambda: __import__('time').time())
