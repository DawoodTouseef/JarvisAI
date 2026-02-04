"""
AgentClarification Tool - Allows agents to request user clarification during task execution

This tool enables bidirectional communication between agents and users:
1. Agent calls tool with a clarification question
2. Tool sends question to frontend via WebSocket
3. Frontend triggers speech recognition (isListening = true)
4. User speaks their response
5. Frontend sends transcription back
6. Tool returns transcription to the requesting agent
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class AgentClarificationTool:
    """Tool for agents to request user clarification"""
    
    def __init__(self):
        """Initialize the clarification tool"""
        # Store pending clarification requests with their futures
        self.pending_clarifications: Dict[str, asyncio.Future] = {}
        
        # Callback to send clarification request to frontend
        self.on_clarification_needed = None
    
    def set_websocket_callback(self, callback):
        """
        Set the callback function to send clarification requests to frontend
        
        Args:
            callback: async function that takes (question, task_id) and sends to frontend
        """
        self.on_clarification_needed = callback
    
    async def request_clarification(
        self,
        question: str,
        task_id: str,
        timeout: int = 300
    ) -> Optional[str]:
        """
        Request clarification from the user
        
        Args:
            question: The clarification question to ask the user
            task_id: The ID of the task requesting clarification
            timeout: Timeout in seconds to wait for user response (default: 5 minutes)
        
        Returns:
            The user's response as transcribed text, or None if timeout/error
        
        Example:
            >>> tool = AgentClarificationTool()
            >>> response = await tool.request_clarification(
            ...     "What is your preferred programming language?",
            ...     task_id="task-123"
            ... )
            >>> print(f"User said: {response}")
        """
        try:
            # Create a future for this clarification request
            future = asyncio.Future()
            self.pending_clarifications[task_id] = future
            
            # Notify frontend to send clarification request
            if self.on_clarification_needed:
                await self.on_clarification_needed(question, task_id)
                print(f"[Clarification] Sent question for task {task_id}: {question}")
            else:
                print(f"[Clarification] No WebSocket callback set for task {task_id}")
                return None
            
            # Wait for user response with timeout
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                print(f"[Clarification] Received response for task {task_id}: {response}")
                return response
            except asyncio.TimeoutError:
                print(f"[Clarification] Timeout waiting for response to task {task_id}")
                return None
            
        except Exception as e:
            print(f"[Clarification] Error requesting clarification: {e}")
            return None
        finally:
            # Clean up the future
            self.pending_clarifications.pop(task_id, None)
    
    def resolve_clarification(self, task_id: str, response: str) -> bool:
        """
        Resolve a pending clarification request with user's response
        
        Args:
            task_id: The ID of the task that requested clarification
            response: The user's response (typically from transcription)
        
        Returns:
            True if clarification was resolved, False if task_id not found
        """
        future = self.pending_clarifications.get(task_id)
        if future and not future.done():
            future.set_result(response)
            print(f"[Clarification] Resolved clarification for task {task_id}")
            return True
        else:
            print(f"[Clarification] No pending clarification for task {task_id}")
            return False
    
    def get_pending_count(self) -> int:
        """Get count of pending clarification requests"""
        return len(self.pending_clarifications)
    
    def get_pending_tasks(self) -> list:
        """Get list of task IDs with pending clarifications"""
        return list(self.pending_clarifications.keys())
    
    def cancel_clarification(self, task_id: str) -> bool:
        """
        Cancel a pending clarification request
        
        Args:
            task_id: The ID of the task to cancel clarification for
        
        Returns:
            True if cancelled, False if task_id not found
        """
        future = self.pending_clarifications.get(task_id)
        if future and not future.done():
            future.set_exception(Exception(f"Clarification cancelled for task {task_id}"))
            print(f"[Clarification] Cancelled clarification for task {task_id}")
            return True
        return False


# Create a global instance
agent_clarification_tool = AgentClarificationTool()
