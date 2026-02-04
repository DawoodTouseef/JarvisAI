from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from .database import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(String)
    priority = Column(String, default="medium")  # low, medium, high, urgent
    status = Column(String, default="pending")   # pending, in_progress, completed
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    content = Column(Text)
    files = Column(String) # JSON string of file paths if needed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String) # user, assistant, system
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True) # Store extra context

class Timer(Base):
    __tablename__ = "timers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String)
    duration_seconds = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    status = Column(String, default="running")  # running, paused, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(String, primary_key=True, default=generate_uuid)
    time = Column(String, nullable=False)  # HH:MM format
    days_of_week = Column(String)  # JSON array: ["Mon", "Tue", ...]
    label = Column(String)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    list_id = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(String)
    checked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    record_type = Column(String, nullable=False)  # medication, exercise, sleep, water
    value = Column(Text)  # JSON string with type-specific data
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    category = Column(String, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)
