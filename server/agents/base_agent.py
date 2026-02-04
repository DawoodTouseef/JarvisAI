"""Base agent classes and enumerations"""

from enum import Enum
from typing import Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from server.services.chat_ai_server import ChatAIServer as ChatOpenAI

class AgentStatus(str, Enum):
    """Agent operational status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(int, Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class Task(BaseModel):
    """Task model for agent operations"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 1 # Added for backward compatibility/priority support
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    cancellable: bool = True
    function: Optional[Callable] = None

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
    
    def __init__(self, name: str, description: str,agent_id: str=None):
        self.agent_id = agent_id if agent_id else str(uuid.uuid4())
        self.name = name
        self.description = description  
        
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
