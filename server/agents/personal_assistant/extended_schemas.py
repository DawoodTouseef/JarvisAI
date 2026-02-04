"""
Extended schemas for enhanced personal assistant features
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Timer Schemas
class TimerCreate(BaseModel):
    name: Optional[str] = Field(None, description="Name/label for the timer")
    duration_seconds: int = Field(..., description="Duration in seconds")

class TimerSchema(BaseModel):
    id: str
    name: Optional[str]
    duration_seconds: int
    started_at: datetime
    ends_at: datetime
    status: str
    created_at: datetime

# Alarm Schemas
class AlarmCreate(BaseModel):
    time: str = Field(..., description="Time in HH:MM format (24-hour)")
    days_of_week: Optional[List[str]] = Field(None, description="Days when alarm repeats")
    label: Optional[str] = Field(None, description="Label for the alarm")

class AlarmUpdate(BaseModel):
    id: str
    time: Optional[str] = None
    days_of_week: Optional[List[str]] = None
    label: Optional[str] = None
    enabled: Optional[bool] = None

class AlarmSchema(BaseModel):
    id: str
    time: str
    days_of_week: Optional[str]
    label: Optional[str]
    enabled: bool
    created_at: datetime

# Reminder Schemas
class RecurrenceRule(BaseModel):
    type: str = Field("none", description="none, daily, weekly")
    interval: int = Field(1, description="Interval for recurrence")
    days_of_week: Optional[List[str]] = Field(None, description="Days for weekly recurrence")

class ReminderCreate(BaseModel):
    text: str = Field(..., description="Reminder text")
    trigger_at: datetime = Field(..., description="When to trigger the reminder (ISO datetime)")
    label: Optional[str] = Field(None, description="Optional label for the reminder")
    recurrence: Optional[RecurrenceRule] = Field(None, description="Optional recurrence rule")

class ReminderUpdate(BaseModel):
    id: str = Field(..., description="Reminder ID")
    text: Optional[str] = None
    trigger_at: Optional[datetime] = None
    label: Optional[str] = None
    recurrence: Optional[RecurrenceRule] = None

# Shopping List Schemas
class ShoppingListCreate(BaseModel):
    name: str = Field(..., description="Name of the shopping list")

class ShoppingItemCreate(BaseModel):
    list_id: str = Field(..., description="ID of the shopping list")
    item_name: str = Field(..., description="Name of the item")
    quantity: Optional[str] = Field(None, description="Quantity")

class ShoppingListSchema(BaseModel):
    id: str
    name: str
    created_at: datetime

class ShoppingItemSchema(BaseModel):
    id: str
    list_id: str
    item_name: str
    quantity: Optional[str]
    checked: bool
    created_at: datetime

# Health Record Schemas
class HealthRecordCreate(BaseModel):
    record_type: str = Field(..., description="Type: medication, exercise, sleep, water")
    value: str = Field(..., description="JSON string with type-specific data")

class HealthRecordSchema(BaseModel):
    id: str
    record_type: str
    value: str
    timestamp: datetime

# User Preference Schemas
class UserPreferenceCreate(BaseModel):
    category: str = Field(..., description="Category of preference")
    key: str = Field(..., description="Preference key")
    value: str = Field(..., description="Preference value")

class UserPreferenceSchema(BaseModel):
    id: str
    category: str
    key: str
    value: str
    created_at: datetime
    updated_at: datetime
