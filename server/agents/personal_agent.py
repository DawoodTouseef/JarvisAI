from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
import json
import logging
import traceback

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc
from sqlalchemy.exc import SQLAlchemyError

from .base_agent import BaseAgent, AgentResponse as BaseAgentResponse, Task as BaseTask
from .personal_assistant.schemas import (
    AgentResponse, Status, TaskCreate, TaskUpdate, TaskSchema,
    CalendarEventCreate, CalendarEventUpdate, CalendarEventSchema,
    NoteCreate, NoteUpdate, NoteSchema,
    ConversationTurnCreate, ConversationHistorySchema
)
from .personal_assistant.extended_schemas import (
    TimerCreate, TimerSchema,
    ReminderCreate, ReminderUpdate,
    ShoppingListCreate, ShoppingItemCreate, ShoppingListSchema, ShoppingItemSchema,
    HealthRecordCreate, HealthRecordSchema,
    UserPreferenceCreate, UserPreferenceSchema
)
from .personal_assistant.productivity_tools import calculate, convert_units, parse_duration, format_duration
from server.database.models import (
    Task, CalendarEvent, Note, ConversationHistory,
    Timer, ShoppingList, ShoppingItem, HealthRecord, UserPreference
)
from server.database.async_database import get_async_db
from server.services.jarvis_pydantic_model import JarvisPydanticModel
from .role_context import AgentDeps, requires_permission, RiskTolerance, RoleContext

logger = logging.getLogger(__name__)

class PersonalAgent(BaseAgent):
    def __init__(self,auth_token:str=None,server_url:str=None):
        super().__init__(
            agent_id="personal_agent",
            name="personal_agent",
            description="Manages personal organization: tasks, calendar, notes, and memory."
        )

        model = JarvisPydanticModel(model_name="qwen3:latest",auth_token=auth_token,server_url=server_url)
        
        self.agent = Agent(
            model, 
            deps_type=AgentDeps,
            output_type=str,
            system_prompt=(
                "You are an Advanced Personal Assistant for the Jarvis AI system with comprehensive capabilities. "
                "You can help with:\n"
                "1. Task Management: Create, update, complete, and delete tasks\n"
                "2. Calendar: Schedule events, manage appointments\n"
                "3. Notes: Create and organize notes\n"
                "4. Reminders & Alarms: Set reminders/alarms with custom labels and recurrence\n"
                "5. Shopping Lists: Create lists and manage shopping items\n"
                "6. Health Tracking: Log medication, exercise, sleep, water intake\n"
                "7. Productivity: Calculate expressions, convert units (length, weight, temperature, volume, time)\n"
                "8. User Preferences: Store and retrieve user preferences\n"
                "9. Conversation Memory: Store and retrieve conversation context\n\n"
                "Always use the appropriate tools for each task. Be helpful, accurate, and efficient. "
                "When setting timers, reminders, or alarms, confirm the details with the user. "
                "For calculations and conversions, show your work clearly."
            )
        )
        self._register_tools()

    def _register_tools(self):
        # Task Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Create Task")
        async def create_task(ctx: RunContext[AgentDeps], task_data: TaskCreate) -> Dict[str, Any]:
            """Create a new task."""
            try:
                # Add role context to metadata if available
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()

                new_task = Task(**task_data.model_dump(), metadata_json=metadata_json)
                ctx.deps.session.add(new_task)
                await ctx.deps.session.commit()
                await ctx.deps.session.refresh(new_task)
                return {"status": "success", "data": {"id": new_task.id, "title": new_task.title}}
            except Exception as e:
                logger.error(f"Error creating task: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Tasks")
        async def list_tasks(ctx: RunContext[AgentDeps], status: Optional[str] = None) -> Dict[str, Any]:
            """List tasks, optionally filtered by status."""
            try:
                query = select(Task)
                if status:
                    query = query.where(Task.status == status)
                result = await ctx.deps.session.execute(query)
                tasks = result.scalars().all()
                return {"status": "success", "data": [TaskSchema.model_validate(t, from_attributes=True).model_dump() for t in tasks]}
            except Exception as e:
                logger.error(f"Error listing tasks: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Update Task")
        async def update_task(ctx: RunContext[AgentDeps], task_update: TaskUpdate) -> Dict[str, Any]:
            """Update an existing task."""
            try:
                stmt = update(Task).where(Task.id == task_update.id).values(
                    **{k: v for k, v in task_update.model_dump(exclude_unset=True).items() if k != 'id'}
                )
                await ctx.deps.session.execute(stmt)
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Task updated"}
            except Exception as e:
                logger.error(f"Error updating task: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Complete Task")
        async def complete_task(ctx: RunContext[AgentDeps], task_id: str) -> Dict[str, Any]:
            """Mark a task as completed."""
            return await update_task(ctx, TaskUpdate(id=task_id, status="completed"))

        @self.agent.tool
        @requires_permission(RiskTolerance.HIGH, "Delete Task")
        async def delete_task(ctx: RunContext[AgentDeps], task_id: str) -> Dict[str, Any]:
            """Delete a task (Note: No soft delete column found, doing hard delete)."""
            try:
                await ctx.deps.session.execute(delete(Task).where(Task.id == task_id))
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Task deleted"}
            except Exception as e:
                logger.error(f"Error deleting task: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        # Calendar Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Create Event")
        async def create_event(ctx: RunContext[AgentDeps], event_data: CalendarEventCreate) -> Dict[str, Any]:
            """Create a new calendar event."""
            try:
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()

                new_event = CalendarEvent(**event_data.model_dump(), metadata_json=metadata_json)
                ctx.deps.session.add(new_event)
                await ctx.deps.session.commit()
                await ctx.deps.session.refresh(new_event)
                return {"status": "success", "data": {"id": new_event.id, "title": new_event.title}}
            except Exception as e:
                logger.error(f"Error creating event: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Events")
        async def list_events(ctx: RunContext[AgentDeps], start_date: Optional[datetime] = None) -> Dict[str, Any]:
            """List calendar events."""
            try:
                query = select(CalendarEvent)
                if start_date:
                    query = query.where(CalendarEvent.start_time >= start_date)
                result = await ctx.deps.session.execute(query)
                events = result.scalars().all()
                return {"status": "success", "data": [CalendarEventSchema.model_validate(e, from_attributes=True).model_dump() for e in events]}
            except Exception as e:
                logger.error(f"Error listing events: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        # Note Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Create Note")
        async def create_note(ctx: RunContext[AgentDeps], note_data: NoteCreate) -> Dict[str, Any]:
            """Create a new note."""
            try:
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()

                new_note = Note(**note_data.model_dump(), metadata_json=metadata_json)
                ctx.deps.session.add(new_note)
                await ctx.deps.session.commit()
                await ctx.deps.session.refresh(new_note)
                return {"status": "success", "data": {"id": new_note.id, "title": new_note.title}}
            except Exception as e:
                logger.error(f"Error creating note: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Notes")
        async def list_notes(ctx: RunContext[AgentDeps]) -> Dict[str, Any]:
            """List all notes."""
            try:
                result = await ctx.deps.session.execute(select(Note))
                notes = result.scalars().all()
                return {"status": "success", "data": [NoteSchema.model_validate(n, from_attributes=True).model_dump() for n in notes]}
            except Exception as e:
                logger.error(f"Error listing notes: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        # Memory Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Store Conversation Turn")
        async def store_conversation_turn(ctx: RunContext[AgentDeps], turn: ConversationTurnCreate) -> Dict[str, Any]:
            """Store a conversation turn for memory."""
            try:
                new_turn = ConversationHistory(**turn.model_dump())
                ctx.deps.session.add(new_turn)
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Turn stored"}
            except Exception as e:
                logger.error(f"Error storing conversation: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Retrieve Recent Context")
        async def retrieve_recent_context(ctx: RunContext[AgentDeps], session_id: str, limit: int = 5) -> Dict[str, Any]:
            """Retrieve the most recent conversation turns for context."""
            try:
                query = select(ConversationHistory).where(ConversationHistory.session_id == session_id).order_by(desc(ConversationHistory.timestamp)).limit(limit)
                result = await ctx.deps.session.execute(query)
                turns = result.scalars().all()
                return {"status": "success", "data": [ConversationHistorySchema.model_validate(t, from_attributes=True).model_dump() for t in reversed(turns)]}
            except Exception as e:
                logger.error(f"Error retrieving context: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # Productivity Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Calculate Expression")
        async def calculate_expression(ctx: RunContext[AgentDeps], expression: str) -> Dict[str, Any]:
            """Calculate a mathematical expression."""
            return calculate(expression)
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Convert Units")
        async def convert_unit(ctx: RunContext[AgentDeps], value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
            """Convert between units (length, weight, temperature, volume, time)."""
            return convert_units(value, from_unit, to_unit)
        
        # Timer Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Set Timer")
        async def set_timer(ctx: RunContext[AgentDeps], duration: str, name: Optional[str] = None) -> Dict[str, Any]:
            """Set a timer with a duration (e.g., '5 minutes', '1 hour 30 minutes')."""
            try:
                duration_seconds = parse_duration(duration)
                now = datetime.now()
                ends_at = now + timedelta(seconds=duration_seconds)
                
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()
                
                new_timer = Timer(
                    name=name,
                    duration_seconds=duration_seconds,
                    started_at=now,
                    ends_at=ends_at,
                    status="running",
                    metadata_json=metadata_json
                )
                ctx.deps.session.add(new_timer)
                await ctx.deps.session.commit()
                await ctx.deps.session.refresh(new_timer)
                
                return {
                    "status": "success",
                    "message": f"Timer set for {format_duration(duration_seconds)}",
                    "data": {"id": new_timer.id, "ends_at": ends_at.isoformat()}
                }
            except Exception as e:
                logger.error(f"Error setting timer: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Timers")
        async def list_timers(ctx: RunContext[AgentDeps], active_only: bool = True) -> Dict[str, Any]:
            """List all timers."""
            try:
                query = select(Timer)
                if active_only:
                    query = query.where(Timer.status == "running")
                result = await ctx.deps.session.execute(query)
                timers = result.scalars().all()
                return {
                    "status": "success",
                    "data": [TimerSchema.model_validate(t, from_attributes=True).model_dump() for t in timers]
                }
            except Exception as e:
                logger.error(f"Error listing timers: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Cancel Timer")
        async def cancel_timer(ctx: RunContext[AgentDeps], timer_id: str) -> Dict[str, Any]:
            """Cancel a running timer."""
            try:
                stmt = update(Timer).where(Timer.id == timer_id).values(status="cancelled")
                await ctx.deps.session.execute(stmt)
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Timer cancelled"}
            except Exception as e:
                logger.error(f"Error cancelling timer: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # Reminder Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Set Reminder")
        async def set_reminder(ctx: RunContext[AgentDeps], reminder: ReminderCreate) -> Dict[str, Any]:
            """Set a reminder at a specific datetime."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                rem_agent.ensure_started()
                result = await rem_agent.add_reminder(
                    text=reminder.text,
                    trigger_at=reminder.trigger_at,
                    label=reminder.label,
                    recurrence=reminder.recurrence.model_dump() if reminder.recurrence else None,
                )
                return result
            except Exception as e:
                logger.error(f"Error setting reminder: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Reminders")
        async def list_reminders(ctx: RunContext[AgentDeps]) -> Dict[str, Any]:
            """List all reminders."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                items = await rem_agent.list_items(kind="reminder")
                return {"status": "success", "data": items}
            except Exception as e:
                logger.error(f"Error listing reminders: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Update Reminder")
        async def update_reminder(ctx: RunContext[AgentDeps], reminder: ReminderUpdate) -> Dict[str, Any]:
            """Update an existing reminder."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                result = await rem_agent.update_item(
                    reminder.id,
                    text=reminder.text,
                    label=reminder.label,
                    trigger_at=reminder.trigger_at,
                    recurrence=reminder.recurrence.model_dump() if reminder.recurrence else None,
                )
                return result
            except Exception as e:
                logger.error(f"Error updating reminder: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Cancel Reminder")
        async def cancel_reminder(ctx: RunContext[AgentDeps], reminder_id: str) -> Dict[str, Any]:
            """Cancel a reminder."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                return await rem_agent.cancel_item(reminder_id)
            except Exception as e:
                logger.error(f"Error cancelling reminder: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Snooze Reminder")
        async def snooze_reminder(ctx: RunContext[AgentDeps], reminder_id: str, minutes: int = 5) -> Dict[str, Any]:
            """Snooze a reminder by a number of minutes."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                return await rem_agent.snooze_item(reminder_id, minutes=minutes)
            except Exception as e:
                logger.error(f"Error snoozing reminder: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}

        # Alarm Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Set Alarm")
        async def set_alarm(ctx: RunContext[AgentDeps], time: str, label: Optional[str] = None, days: Optional[List[str]] = None) -> Dict[str, Any]:
            """Set an alarm at a specific time (HH:MM format, 24-hour). Optionally repeat on specific days."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                rem_agent.ensure_started()
                return await rem_agent.add_alarm(time_str=time, label=label, days_of_week=days)
            except Exception as e:
                logger.error(f"Error setting alarm: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Alarms")
        async def list_alarms(ctx: RunContext[AgentDeps]) -> Dict[str, Any]:
            """List all alarms."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                items = await rem_agent.list_items(kind="alarm")
                return {"status": "success", "data": items}
            except Exception as e:
                logger.error(f"Error listing alarms: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.MEDIUM, "Delete Alarm")
        async def delete_alarm(ctx: RunContext[AgentDeps], alarm_id: str) -> Dict[str, Any]:
            """Delete an alarm."""
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                return await rem_agent.cancel_item(alarm_id)
            except Exception as e:
                logger.error(f"Error deleting alarm: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # Shopping List Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Create Shopping List")
        async def create_shopping_list(ctx: RunContext[AgentDeps], name: str) -> Dict[str, Any]:
            """Create a new shopping list."""
            try:
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()
                
                new_list = ShoppingList(name=name, metadata_json=metadata_json)
                ctx.deps.session.add(new_list)
                await ctx.deps.session.commit()
                await ctx.deps.session.refresh(new_list)
                
                return {
                    "status": "success",
                    "message": f"Shopping list '{name}' created",
                    "data": {"id": new_list.id}
                }
            except Exception as e:
                logger.error(f"Error creating shopping list: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Add Item to Shopping List")
        async def add_shopping_item(ctx: RunContext[AgentDeps], list_id: str, item_name: str, quantity: Optional[str] = None) -> Dict[str, Any]:
            """Add an item to a shopping list."""
            try:
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()
                
                new_item = ShoppingItem(
                    list_id=list_id,
                    item_name=item_name,
                    quantity=quantity,
                    metadata_json=metadata_json
                )
                ctx.deps.session.add(new_item)
                await ctx.deps.session.commit()
                
                return {
                    "status": "success",
                    "message": f"Added '{item_name}' to shopping list"
                }
            except Exception as e:
                logger.error(f"Error adding shopping item: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "List Shopping Lists")
        async def list_shopping_lists(ctx: RunContext[AgentDeps]) -> Dict[str, Any]:
            """List all shopping lists."""
            try:
                result = await ctx.deps.session.execute(select(ShoppingList))
                lists = result.scalars().all()
                return {
                    "status": "success",
                    "data": [ShoppingListSchema.model_validate(l, from_attributes=True).model_dump() for l in lists]
                }
            except Exception as e:
                logger.error(f"Error listing shopping lists: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Get Shopping List Items")
        async def get_shopping_list_items(ctx: RunContext[AgentDeps], list_id: str) -> Dict[str, Any]:
            """Get all items in a shopping list."""
            try:
                query = select(ShoppingItem).where(ShoppingItem.list_id == list_id)
                result = await ctx.deps.session.execute(query)
                items = result.scalars().all()
                return {
                    "status": "success",
                    "data": [ShoppingItemSchema.model_validate(i, from_attributes=True).model_dump() for i in items]
                }
            except Exception as e:
                logger.error(f"Error getting shopping items: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Check Shopping Item")
        async def check_shopping_item(ctx: RunContext[AgentDeps], item_id: str, checked: bool = True) -> Dict[str, Any]:
            """Mark a shopping item as checked/unchecked."""
            try:
                stmt = update(ShoppingItem).where(ShoppingItem.id == item_id).values(checked=checked)
                await ctx.deps.session.execute(stmt)
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Item updated"}
            except Exception as e:
                logger.error(f"Error checking item: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # Health Tracking Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Log Health Record")
        async def log_health_record(ctx: RunContext[AgentDeps], record_type: str, value: str) -> Dict[str, Any]:
            """Log a health record (medication, exercise, sleep, water)."""
            try:
                metadata_json = None
                if ctx.deps.role_context:
                    metadata_json = ctx.deps.role_context.model_dump_json()
                
                new_record = HealthRecord(
                    record_type=record_type,
                    value=value,
                    metadata_json=metadata_json
                )
                ctx.deps.session.add(new_record)
                await ctx.deps.session.commit()
                
                return {
                    "status": "success",
                    "message": f"Logged {record_type} record"
                }
            except Exception as e:
                logger.error(f"Error logging health record: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Get Health Records")
        async def get_health_records(ctx: RunContext[AgentDeps], record_type: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
            """Get health records, optionally filtered by type."""
            try:
                query = select(HealthRecord).order_by(desc(HealthRecord.timestamp)).limit(limit)
                if record_type:
                    query = query.where(HealthRecord.record_type == record_type)
                result = await ctx.deps.session.execute(query)
                records = result.scalars().all()
                return {
                    "status": "success",
                    "data": [HealthRecordSchema.model_validate(r, from_attributes=True).model_dump() for r in records]
                }
            except Exception as e:
                logger.error(f"Error getting health records: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        # User Preference Tools
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Set User Preference")
        async def set_preference(ctx: RunContext[AgentDeps], category: str, key: str, value: str) -> Dict[str, Any]:
            """Set a user preference."""
            try:
                # Check if preference exists
                query = select(UserPreference).where(
                    UserPreference.category == category,
                    UserPreference.key == key
                )
                result = await ctx.deps.session.execute(query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    stmt = update(UserPreference).where(UserPreference.id == existing.id).values(value=value)
                    await ctx.deps.session.execute(stmt)
                else:
                    new_pref = UserPreference(category=category, key=key, value=value)
                    ctx.deps.session.add(new_pref)
                
                await ctx.deps.session.commit()
                return {"status": "success", "message": "Preference saved"}
            except Exception as e:
                logger.error(f"Error setting preference: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
        
        @self.agent.tool
        @requires_permission(RiskTolerance.LOW, "Get User Preference")
        async def get_preference(ctx: RunContext[AgentDeps], category: str, key: str) -> Dict[str, Any]:
            """Get a user preference."""
            try:
                query = select(UserPreference).where(
                    UserPreference.category == category,
                    UserPreference.key == key
                )
                result = await ctx.deps.session.execute(query)
                pref = result.scalar_one_or_none()
                
                if pref:
                    return {
                        "status": "success",
                        "data": UserPreferenceSchema.model_validate(pref, from_attributes=True).model_dump()
                    }
                return {"status": "error", "message": "Preference not found"}
            except Exception as e:
                logger.error(f"Error getting preference: {traceback.format_exc()}")
                return {"status": "error", "message": str(e)}
    def can_handle_task(self, task: BaseTask) -> bool:
        """Check if the agent can handle the task."""
        return True
    
    async def process_task(self, task: BaseTask) -> BaseAgentResponse:
        """EntryPoint for the Central Orchestrator."""
        query = task.metadata.get("query")
        if not query:
            return BaseAgentResponse(agent_id=self.agent_id, success=False, error="No query provided")

        async for db in get_async_db():
            try:
                # Setup AgentDeps
                role_dict = task.metadata.get("role_context")
                role_context = RoleContext(**role_dict) if role_dict else None
                permission_callback = task.metadata.get("permission_callback")
                
                deps = AgentDeps(session=db, role_context=role_context, permission_callback=permission_callback)
                
                # Inject current datetime for context-aware scheduling
                from datetime import datetime
                current_time = datetime.now()
                enhanced_query = f"Current Date and Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (24-hour format)\n\nUser Query: {query}"
                
                # We use the agent to decide which tool to call
                result = await self.agent.run(enhanced_query, deps=deps)
                return BaseAgentResponse(agent_id=self.agent_id, success=True, result=result.output)
            except Exception as e:
                logger.error(f"PersonalAgent processing error: {traceback.format_exc()}")
                return BaseAgentResponse(agent_id=self.agent_id, success=False, error=str(e))
