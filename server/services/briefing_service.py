from datetime import datetime, timedelta
from database.database import get_db
from database.models import Task, CalendarEvent
from .llm_client import llm_client
import sqlalchemy

class BriefingService:
    def __init__(self):
        self.llm = llm_client

    async def generate_briefing(self) -> str:
        """
        Aggregates today's events and pending tasks to generate a natural language summary.
        """
        try:
            db = next(get_db())
            
            # 1. Get Today's Events
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            events = db.query(CalendarEvent).filter(
                CalendarEvent.start_time >= today,
                CalendarEvent.start_time < tomorrow
            ).order_by(CalendarEvent.start_time).all()
            
            # 2. Get Pending Tasks (High Priority first)
            tasks = db.query(Task).filter(
                Task.status != "completed"
            ).order_by(
                sqlalchemy.case(
                    (Task.priority == 'urgent', 1),
                    (Task.priority == 'high', 2),
                    (Task.priority == 'medium', 3),
                    else_=4
                )
            ).all()

            # 3. Format Data for LLM
            events_text = "No events scheduled for today."
            if events:
                events_text = "\n".join([f"- {e.title} at {e.start_time.strftime('%I:%M %p')}" for e in events])
            
            tasks_text = "No pending tasks."
            if tasks:
                tasks_text = "\n".join([f"- {t.title} ({t.priority})" for t in tasks[:10]]) # Limit to top 10

            prompt = f"""
            You are Jarvis, a personal assistant. Generate a concise, natural morning briefing for the user based on the following data:
            
            Current Date/Time: {datetime.now().strftime('%A, %B %d, %I:%M %p')}
            
            Calendar Events Today:
            {events_text}
            
            Pending Tasks:
            {tasks_text}
            
            Style: Professional, helpful, slightly witty. Keep it under 150 words.
            """
            
            messages = [{"role": "user", "content": prompt}]
            summary = await self.llm.get_response(messages, temperature=0.7)
            return summary

        except Exception as e:
            return f"I encountered an error generating your briefing: {str(e)}"

briefing_service = BriefingService()
