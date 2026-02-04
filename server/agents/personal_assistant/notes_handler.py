from .base_handler import BaseHandler
from server.database.models import Note
from server.database.database import get_db
from server.services.llm_client import llm_client
from datetime import datetime
from typing import Dict, Any, List
import json

class NotesHandler(BaseHandler):
    async def handle(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for note-related intents.
        intent_data comes from the IntentRouter.
        """
        # Determine specific action (create, list, delete) using LLM or heuristic
        # For simplicity, we assume the specific action is passed or derived
        
        query = intent_data.get("original_query", "")
        # Heuristic for now, or use LLM to refine "action"
        if "create" in query.lower() or "add" in query.lower() or "take a note" in query.lower():
            return await self.create_note(intent_data)
        elif "list" in query.lower() or "read" in query.lower() or "show" in query.lower():
            return await self.list_notes(intent_data)
        elif "delete" in query.lower() or "remove" in query.lower():
            return await self.delete_note(intent_data)
        else:
            return {"success": False, "error": "Unknown note action"}

    async def create_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        entities = data.get("entities", {})
        # If entities are missing content, use the whole query minus command words?
        # Or better, rely on LLM entity extraction in IntentRouter.
        
        # If no content extracted, ask LLM to extract cleanly
        content = entities.get("content") or data.get("original_query")
        title = entities.get("title", f"Note {datetime.now().strftime('%m-%d %H:%M')}")
        
        try:
            db = next(get_db())
            new_note = Note(title=title, content=content)
            db.add(new_note)
            db.commit()
            return {
                "success": True, 
                "message": f"Created note: {title}", 
                "data": {"id": new_note.id, "title": new_note.title}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_notes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            db = next(get_db())
            notes = db.query(Note).order_by(Note.updated_at.desc()).limit(10).all()
            return {
                "success": True,
                "message": f"Found {len(notes)} recent notes.",
                "data": [{"id": n.id, "title": n.title, "content": n.content} for n in notes]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Need an ID or title to delete
        # This is where context is important, "delete THAT note"
        return {"success": False, "message": "Delete not fully implemented without context ID"}
