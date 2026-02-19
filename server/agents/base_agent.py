"""Base agent classes and enumerations"""

from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import asyncio
from server.services.chat_ai_server import ChatAIServer as ChatOpenAI

class AgentStatus(str, Enum):
    """Agent operational status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    """Deep Research Job Types"""
    CHAT = "chat"
    RESEARCH = "research"

class TaskPriority(int, Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

class Task(BaseModel):
    """Task model for agent operations"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 1
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    cancellable: bool = True
    function: Optional[Callable] = None

class Job(BaseModel):
    """High-level Job abstraction for tracking research/chat workflows"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType = JobType.CHAT
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    task_ids: List[str] = [] # Linkage to individual Task items
    metadata: Dict[str, Any] = {}

class AgentResponse(BaseModel):
    """Standard response format from agents"""
    agent_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    _default_event_callback: Optional[Callable] = None

    def __init__(self, name: str, description: str, agent_id: str = None):
        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.name = name
        self.description = description  
        self._event_callback: Optional[Callable] = BaseAgent._default_event_callback
        self.status = AgentStatus.PENDING
        
    @abstractmethod
    async def process_task(self, task: Task) -> AgentResponse:
        """Process a task asynchronously"""
        pass
    
    @abstractmethod
    def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle the given task"""
        pass

    def get_status_info(self) -> Dict[str, Any]:
        """Get agent status information"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "description": self.description,
        }

    def get_llm(self, task: Task) -> ChatOpenAI:
        """Get a configured LLM instance based on task metadata (auth_token, base_url)"""
        auth_token = task.metadata.get("auth_token")
        base_url = task.metadata.get("base_url")
        
        return ChatOpenAI(
            api_key=auth_token,
            server_url=base_url,
            model="qwen3:latest"
        )

    @classmethod
    def set_default_event_callback(cls, callback: Optional[Callable]) -> None:
        cls._default_event_callback = callback

    def set_event_callback(self, callback: Optional[Callable]) -> None:
        self._event_callback = callback

    async def emit_event(self, event_type: str, task_id: str, payload: Dict[str, Any]) -> None:
        if not self._event_callback:
            return
        try:
            result = self._event_callback(event_type, task_id, payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            # Avoid cascading failures on telemetry events.
            return
