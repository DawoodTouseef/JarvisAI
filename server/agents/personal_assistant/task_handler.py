from .base_handler import BaseHandler
from server.database.models import Task
from server.database.database import get_db
from datetime import datetime
from typing import Dict, Any

class TaskHandler(BaseHandler):
    async def handle(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        query = intent_data.get("original_query", "").lower()
        
        if "create" in query or "add" in query or "remind" in query:
            return await self.create_task(intent_data)
        elif "list" in query or "show" in query or "what" in query:
            return await self.list_tasks(intent_data)
        elif "complete" in query or "finish" in query or "done" in query:
            return await self.complete_task(intent_data)
        else:
            return {"success": False, "error": "Unknown task action"}

    async def create_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        entities = data.get("entities", {})
        title = entities.get("task_content") or data.get("original_query")
        priority = entities.get("priority", "medium")
        
        # Extract due date if possible (skipped for now, needs nlu entity extraction)
        
        try:
            db = next(get_db())
            new_task = Task(title=title, priority=priority, status="pending")
            db.add(new_task)
            db.commit()
            return {
                "success": True,
                "message": f"Added task: {title} ({priority})",
                "data": {"id": new_task.id, "title": new_task.title}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_tasks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db = next(get_db())
            tasks = db.query(Task).filter(Task.status != "completed").limit(10).all()
            task_list_str = ", ".join([t.title for t in tasks])
            return {
                "success": True,
                "message": f"You have {len(tasks)} pending tasks: {task_list_str}",
                "data": [{"id": t.id, "title": t.title, "priority": t.priority} for t in tasks]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def complete_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
         return {"success": False, "message": "Mark complete not implemented (needs ID context)"}
