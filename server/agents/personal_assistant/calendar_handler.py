from .base_handler import BaseHandler
from server.database.models import CalendarEvent
from server.database.database import get_db
from datetime import datetime, timedelta
from typing import Dict, Any

class CalendarHandler(BaseHandler):
    async def handle(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        query = intent_data.get("original_query", "").lower()
        
        if "schedule" in query or "create" in query or "meeting" in query:
            return await self.create_event(intent_data)
        elif "list" in query or "show" in query or "what" in query:
            return await self.list_events(intent_data)
        else:
            return {"success": False, "error": "Unknown calendar action"}

    async def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        entities = data.get("entities", {})
        title = entities.get("event_title") or "Meeting"
        
        # Determine start/end time. This requires strong NLU entity extraction (dateparser).
        # For prototype, default to tomorrow 9am if parsed failed or assume entities has ISO string
        start_time_str = entities.get("start_time")
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except:
                start_time = datetime.now() + timedelta(days=1)
        else:
             start_time = datetime.now() + timedelta(days=1) # Default tomorrow
             
        end_time = start_time + timedelta(hours=1)
        
        try:
            db = next(get_db())
            new_event = CalendarEvent(title=title, start_time=start_time, end_time=end_time)
            db.add(new_event)
            db.commit()
            return {
                "success": True,
                "message": f"Scheduled '{title}' for {start_time.strftime('%Y-%m-%d %H:%M')}",
                "data": {"id": new_event.id, "title": new_event.title}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_events(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db = next(get_db())
            events = db.query(CalendarEvent).order_by(CalendarEvent.start_time).limit(5).all()
            if not events:
                return {"success": True, "message": "No upcoming events found."}
                
            msg = ", ".join([f"{e.title} at {e.start_time.strftime('%H:%M')}" for e in events])
            return {
                "success": True,
                "message": f"Upcoming events: {msg}",
                "data": [{"id": e.id, "title": e.title, "start": e.start_time.isoformat()} for e in events]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
