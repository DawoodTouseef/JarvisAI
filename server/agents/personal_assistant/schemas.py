from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class Status(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class AgentResponse(BaseModel):
    status: Status
    data: Optional[Any] = None
    message: Optional[str] = None

# Task Schemas
class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskCreate(BaseModel):
    title: str = Field(..., description="The title of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Priority of the task")
    due_date: Optional[datetime] = Field(None, description="Due date for the task")

class TaskUpdate(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None

class TaskSchema(BaseModel):
    id: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

# Calendar Schemas
class CalendarEventCreate(BaseModel):
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_time: datetime = Field(..., description="Start time of the event")
    end_time: datetime = Field(..., description="End time of the event")
    location: Optional[str] = Field(None, description="Location of the event")

class CalendarEventUpdate(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None

class CalendarEventSchema(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    created_at: datetime
    updated_at: datetime

# Note Schemas
class NoteCreate(BaseModel):
    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content of the note")

class NoteUpdate(BaseModel):
    id: str
    title: Optional[str] = None
    content: Optional[str] = None

class NoteSchema(BaseModel):
    id: str
    title: str
    content: str
    files: Optional[str]
    created_at: datetime
    updated_at: datetime

# Memory Schemas
class ConversationTurnCreate(BaseModel):
    session_id: str = Field(..., description="The session identifier")
    role: str = Field(..., description="Role: user, assistant, or system")
    message: str = Field(..., description="The message content")
    metadata_json: Optional[str] = Field(None, description="Extra context in JSON string format")

class ConversationHistorySchema(BaseModel):
    id: int
    session_id: str
    role: str
    message: str
    timestamp: datetime
    metadata_json: Optional[str]
