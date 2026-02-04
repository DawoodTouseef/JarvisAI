from typing import List, Dict, Optional
from datetime import datetime
from database.database import get_db
from database.models import ConversationHistory
from .llm_client import llm_client
import json

class ContextManager:
    def __init__(self):
        self._in_memory_cache: Dict[str, List[Dict]] = {} # session_id -> history
        
    def add_message(self, session_id: str, role: str, message: str, metadata: Optional[Dict] = None):
        """Add a message to history (memory + db)"""
        # Memory
        if session_id not in self._in_memory_cache:
            self._in_memory_cache[session_id] = []
        
        entry = {
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        self._in_memory_cache[session_id].append(entry)
        
        # Database
        try:
            db = next(get_db())
            db_entry = ConversationHistory(
                session_id=session_id,
                role=role,
                message=message,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            db.add(db_entry)
            db.commit()
        except Exception as e:
            print(f"Failed to save context to DB: {e}")

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        # Return from memory if available
        if session_id in self._in_memory_cache:
            return self._in_memory_cache[session_id][-limit:]
            
        # Fallback to DB (load into memory)
        try:
            db = next(get_db())
            records = db.query(ConversationHistory).filter(
                ConversationHistory.session_id == session_id
            ).order_by(ConversationHistory.timestamp.desc()).limit(limit).all()
            
            history = []
            for r in reversed(records):
                history.append({
                    "role": r.role,
                    "content": r.message,
                    "timestamp": r.timestamp.isoformat()
                })
            
            self._in_memory_cache[session_id] = history
            return history
        except Exception as e:
            print(f"Failed to load context from DB: {e}")
            return []

    def clear_context(self, session_id: str):
        """Clear context for a session"""
        if session_id in self._in_memory_cache:
            del self._in_memory_cache[session_id]

context_manager = ContextManager()
