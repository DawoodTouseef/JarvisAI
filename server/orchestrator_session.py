"""
OrchestratorSession - WebSocket Adapter for CentralOrchestrator

This module provides a thin adapter layer that wraps CentralOrchestrator
per WebSocket connection, translating orchestrator events into WebSocket
messages and vice versa.

CRITICAL: This adapter does NOT modify CentralOrchestrator itself.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime
from server.agents.orchestrator import CentralOrchestrator
from server.services.context.context_store import ContextStore

from server.agents.vision_agent import VisionAgent
from server.agents.system_context_agent import SystemContextAgent
from server.agents.knowledge_agent import KnowledgeAgent
from server.services.vision.screenshot_capture import capture_screenshot_bytes



logger = logging.getLogger(__name__)


class OrchestratorSession:
    """
    Per-WebSocket session wrapper for CentralOrchestrator.
    
    Responsibilities:
    - Create one CentralOrchestrator instance per WebSocket connection
    - Translate orchestrator events → WebSocket messages
    - Receive WebSocket messages → forward to orchestrator
    - Manage session lifecycle (connect/disconnect)
    """
    
    def __init__(self, session_id: str, websocket_send_callback: Callable):
        """
        Initialize a new orchestrator session.
        
        Args:
            session_id: Unique identifier for this session
            websocket_send_callback: Async function to send messages to WebSocket
                                    Signature: async def send(message: dict)
        """
        self.session_id = session_id
        self.websocket_send = websocket_send_callback
        self.orchestrator = CentralOrchestrator()
        self.active_task_id: Optional[str] = None
        self.is_connected = True
        self._send_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._send_task: Optional[asyncio.Task] = asyncio.create_task(self._send_loop())
        self._background_tasks: Set[asyncio.Task] = set()
        self._sent_final_for_task: Set[str] = set()
        self._last_auth_token: Optional[str] = None
        self._last_base_url: Optional[str] = None
        self._screenshot_task: Optional[asyncio.Task] = None
        
        # Set up event callback to translate orchestrator events
        self.orchestrator.set_event_callback(self._handle_orchestrator_event)
        self._register_module_agents()
        self._start_screenshot_loop()

        
        logger.info(f"OrchestratorSession {session_id} created")

    async def _send_loop(self):
        """Background send loop to keep websocket sends non-blocking for orchestrator."""
        try:
            while self.is_connected:
                message = await self._send_queue.get()
                if not self.is_connected:
                    break
                try:
                    if self.websocket_send:
                        await self.websocket_send(message)
                except Exception as e:
                    logger.error(f"Error sending message to WebSocket: {e}")
        except asyncio.CancelledError:
            return

    async def _enqueue_send(self, message: dict):
        """Queue a message for websocket delivery."""
        if not self.is_connected:
            return
        try:
            self._send_queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning(f"Send queue full for session {self.session_id}, dropping message")
    
    async def _handle_orchestrator_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        """
        Translate orchestrator events into WebSocket messages.
        
        This is the core translation layer that converts internal orchestrator
        events into the strict WebSocket protocol.
        """
        if not self.is_connected:
            logger.warning(f"Session {self.session_id} disconnected, ignoring event {event_type}")
            return
        
        try:
            # Map orchestrator events to WebSocket message types
            if event_type == "clarification_required":
                await self._send_clarification_required(task_id, payload)
            
            elif event_type == "system_permission_required":
                await self._send_permission_required(task_id, payload)
            
            elif event_type == "orchestrator_state_update":
                await self._send_state_update(task_id, payload)
            
            elif event_type == "assistant_text_chunk":
                await self._send_text_chunk(task_id, payload)
            
            elif event_type == "assistant_text_final":
                await self._send_assistant_response(task_id, payload)
            
            elif event_type == "orchestrator_error":
                await self._send_error(task_id, payload)

            elif event_type == "system_agent_state_update":
                await self._send_system_agent_state(task_id, payload)

            elif event_type == "system_agent_event":
                await self._send_system_agent_event(task_id, payload)

            elif event_type == "reminder_triggered":
                await self._send_reminder_triggered(task_id, payload)

            elif event_type == "alarm_triggered":
                await self._send_alarm_triggered(task_id, payload)

            elif event_type == "autonomous_task_started":
                await self._send_autonomous_task_started(task_id, payload)

            elif event_type == "autonomous_task_result":
                await self._send_autonomous_task_result(task_id, payload)

            elif event_type == "autonomous_task_notice":
                await self._send_autonomous_task_notice(task_id, payload)

            elif event_type == "autonomous_permission_required":
                await self._send_autonomous_permission_required(task_id, payload)
            
            else:
                # Unknown event type - log but don't fail
                logger.warning(f"Unknown orchestrator event type: {event_type}")
        
        except Exception as e:
            logger.exception(f"Error handling orchestrator event {event_type}: {e}")
    
    async def _send_clarification_required(self, task_id: str, payload: Dict[str, Any]):
        """Send clarification_required message to frontend."""
        message = {
            "type": "clarification_required",
            "task_id": task_id,
            "payload": {
                "question_text": payload.get("question_text", "")
            },
            "use_tts": True,
            "isListening": True,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)
    
    async def _send_permission_required(self, task_id: str, payload: Dict[str, Any]):
        """Send system_permission_required message to frontend."""
        message = {
            "type": "system_permission_required",
            "task_id": task_id,
            "payload": {
                "command_summary": payload.get("command_summary", ""),
                "exact_operation": payload.get("exact_operation", ""),
                "risk_level": payload.get("risk_level", "unknown")
            },
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)
    
    async def _send_state_update(self, task_id: str, payload: Dict[str, Any]):
        """Send orchestrator_state_update message to frontend."""
        message = {
            "type": "orchestrator_state_update",
            "task_id": task_id,
            "payload": {
                "state": payload.get("state", "idle")
            },
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)
    
    async def _send_text_chunk(self, task_id: str, payload: Dict[str, Any]):
        """Send assistant_text_chunk message to frontend (streaming)."""
        message = {
            "type": "assistant_text_chunk",
            "task_id": task_id,
            "payload": {
                "text": payload.get("text", "")
            },
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)
    
    async def _send_assistant_response(self, task_id: str, payload: Dict[str, Any]):
        """Send assistant_response message to frontend."""
        message = {
            "type": "assistant_response",
            "task_id": task_id,
            "payload": {
                "text": payload.get("text", "")
            },
            "use_tts": True,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)
        self._sent_final_for_task.add(task_id)
        try:
            from server.services.reminder_service import get_reminder_agent
            rem_agent = get_reminder_agent()
            await rem_agent.record_autonomous_completion(task_id, payload.get("text", ""))
        except Exception:
            pass
    
    async def _send_error(self, task_id: str, payload: Dict[str, Any]):
        """Send orchestrator_error message to frontend."""
        message = {
            "type": "orchestrator_error",
            "task_id": task_id,
            "payload": {
                "message": payload.get("message", "Unknown error")
            },
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_system_agent_state(self, task_id: str, payload: Dict[str, Any]):
        """Send system agent state updates to frontend."""
        message = {
            "type": "system_agent_state_update",
            "task_id": task_id,
            "payload": {
                "state": payload.get("state", "IDLE")
            },
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_system_agent_event(self, task_id: str, payload: Dict[str, Any]):
        """Send system agent events to frontend."""
        message = {
            "type": "system_agent_event",
            "task_id": task_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_reminder_triggered(self, task_id: str, payload: Dict[str, Any]):
        """Send reminder_triggered message to frontend."""
        message = {
            "type": "reminder_triggered",
            "task_id": task_id,
            "payload": payload,
            "use_tts": True,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_alarm_triggered(self, task_id: str, payload: Dict[str, Any]):
        """Send alarm_triggered message to frontend."""
        message = {
            "type": "alarm_triggered",
            "task_id": task_id,
            "payload": payload,
            "use_tts": True,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_autonomous_task_started(self, task_id: str, payload: Dict[str, Any]):
        """Send autonomous_task_started message to frontend."""
        message = {
            "type": "autonomous_task_started",
            "task_id": task_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_autonomous_task_result(self, task_id: str, payload: Dict[str, Any]):
        """Send autonomous_task_result message to frontend."""
        message = {
            "type": "autonomous_task_result",
            "task_id": task_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_autonomous_task_notice(self, task_id: str, payload: Dict[str, Any]):
        """Send autonomous_task_notice message to frontend."""
        message = {
            "type": "autonomous_task_notice",
            "task_id": task_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    async def _send_autonomous_permission_required(self, task_id: str, payload: Dict[str, Any]):
        """Send autonomous_permission_required message to frontend."""
        message = {
            "type": "autonomous_permission_required",
            "task_id": task_id,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        await self._enqueue_send(message)

    def _register_module_agents(self):
        """Register additional agents without modifying the CentralOrchestrator."""
        for agent in [VisionAgent(), SystemContextAgent(), KnowledgeAgent()]:
            if not any(a.name == agent.name for a in self.orchestrator.agents):
                self.orchestrator.agents.append(agent)

    def _start_screenshot_loop(self):
        """Always-on backend screenshot capture for vision."""
        if self._screenshot_task:
            return
        self._screenshot_task = asyncio.create_task(self._screenshot_loop())
        self._background_tasks.add(self._screenshot_task)
        self._screenshot_task.add_done_callback(lambda t: self._background_tasks.discard(t))

    async def _screenshot_loop(self):
        while self.is_connected:
            try:
                image_bytes = await asyncio.to_thread(capture_screenshot_bytes)
                if image_bytes:
                    ContextStore.set_screenshot_image(
                        self.session_id,
                        image_bytes,
                        {"source": "backend_screenshot", "timestamp": datetime.now().isoformat()},
                    )
            except Exception:
                pass
            await asyncio.sleep(1.0)
    
    async def handle_user_query(self, text: str, auth_token: str, base_url: str, request_id: Optional[str] = None, source: str = "user") -> str:
        """
        Handle a user query by submitting it to the orchestrator.
        
        Args:
            text: User's query text
            auth_token: Authentication token for LLM
            base_url: Base URL for LLM API
            request_id: Optional request ID for tracking
        
        Returns:
            task_id: ID of the created task
        """
        if self.active_task_id:
            await self.handle_interrupt(self.active_task_id)

        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.session_id}"
        self.active_task_id = task_id
        self._last_auth_token = auth_token
        self._last_base_url = base_url
        ContextStore.set_task_session(task_id, self.session_id)
        
        task_data = {
            "id": task_id,
            "query": text,
            "auth_token": auth_token,
            "base_url": base_url,
            "session_id": self.session_id,
        }
        
        logger.info(f"Session {self.session_id}: Submitting task {task_id}")
        
        # Submit task asynchronously - orchestrator will emit events via callback
        task = asyncio.create_task(self._execute_task(task_data))
        self._background_tasks.add(task)
        task.add_done_callback(lambda t: self._background_tasks.discard(t))

        if source == "user":
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                rem_agent.ensure_started()
                await rem_agent.record_user_query(text)
            except Exception:
                pass
        
        return task_id

    async def submit_autonomous_query(self, text: str) -> str:
        auth_token = self._last_auth_token or ""
        base_url = self._last_base_url or ""
        return await self.handle_user_query(text, auth_token, base_url, source="autonomous")
    
    async def _execute_task(self, task_data: Dict[str, Any]):
        """Execute task and handle completion/errors."""
        try:
            result = await self.orchestrator.submit_task(task_data)
            status = result.get('workflow_status')
            logger.info(f"Task {task_data['id']} completed with status: {status}")
            logger.info(f"Task {task_data['id']} result: \n{result['processing_result']}")
            # Send final response if available and not already emitted
            processing_result = result.get('processing_result')
            if processing_result and task_data['id'] not in self._sent_final_for_task:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                await rem_agent.record_assistant_query(processing_result)
                await self._send_assistant_response(task_data['id'], {"text": str(processing_result)})
                
        except Exception as e:
            logger.exception(f"Task {task_data['id']} failed: {e}")
            await self._send_error(task_data['id'], {"message": str(e)})
        finally:
            if self.active_task_id == task_data["id"]:
                self.active_task_id = None
            self._sent_final_for_task.discard(task_data["id"])
    
    async def handle_clarification_response(self, task_id: str, response_text: str):
        """
        Handle clarification response from frontend.
        
        Args:
            task_id: ID of the task waiting for clarification
            response_text: User's response text
        """
        logger.info(f"Session {self.session_id}: Resolving clarification for task {task_id}")
        success = self.orchestrator.resolve_clarification(task_id, response_text)
        
        if not success:
            logger.warning(f"Failed to resolve clarification for task {task_id}")
    
    async def handle_permission_response(self, task_id: str, approved: bool):
        """
        Handle permission response from frontend.
        
        Args:
            task_id: ID of the task waiting for permission
            approved: Whether user approved the action
        """
        logger.info(f"Session {self.session_id}: Resolving permission for task {task_id} - approved={approved}")
        success = self.orchestrator.resolve_permission(task_id, approved)
        
        if not success:
            logger.warning(f"Failed to resolve permission for task {task_id}")
    
    async def handle_interrupt(self, task_id: str):
        """
        Handle user interruption.
        
        Args:
            task_id: ID of the task to interrupt
        """
        logger.info(f"Session {self.session_id}: Interrupting task {task_id}")
        await self.orchestrator.handle_interrupt(task_id)
        try:
            from server.services.reminder_service import get_reminder_agent
            rem_agent = get_reminder_agent()
            await rem_agent.record_autonomous_result(task_id, accepted=False, reason="interrupted")
        except Exception:
            pass
        logger.info(f"Session {self.session_id}: Interrupt handled for task {task_id}")

    async def handle_external_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        """Allow external services (e.g., RemAgent) to emit events via this session."""
        await self._handle_orchestrator_event(event_type, task_id, payload)

    async def store_vision_input(self, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store latest vision input for this session."""
        return ContextStore.set_camera_image(self.session_id, image_bytes, metadata)
    
    async def handle_cancel_task(self, task_id: str):
        """
        Handle task cancellation.
        
        Args:
            task_id: ID of the task to cancel
        """
        logger.info(f"Session {self.session_id}: Cancelling task {task_id}")
        success = await self.orchestrator.cancel_task(task_id)
        
        if success:
            logger.info(f"Task {task_id} cancelled successfully")
            try:
                from server.services.reminder_service import get_reminder_agent
                rem_agent = get_reminder_agent()
                await rem_agent.record_autonomous_result(task_id, accepted=False, reason="cancelled")
            except Exception:
                pass
        else:
            logger.warning(f"Failed to cancel task {task_id}")
    
    async def disconnect(self):
        """Clean up session on disconnect."""
        logger.info(f"OrchestratorSession {self.session_id} disconnecting")
        self.is_connected = False
        ContextStore.evict(self.session_id)
        
        # Cancel active task if any
        if self.active_task_id:
            await self.handle_cancel_task(self.active_task_id)

        # Cancel background tasks
        for task in list(self._background_tasks):
            task.cancel()
        self._background_tasks.clear()

        # Stop send loop
        if self._send_task:
            self._send_task.cancel()
        if self._screenshot_task:
            self._screenshot_task.cancel()
        
        # Clear references
        self.orchestrator = None
        self.websocket_send = None


class SessionManager:
    """
    Manages multiple OrchestratorSession instances.
    
    One session per WebSocket connection.
    """
    
    def __init__(self):
        self.sessions: Dict[str, OrchestratorSession] = {}
        self._session_counter = 0
    
    def create_session(self, websocket_send_callback: Callable) -> OrchestratorSession:
        """
        Create a new session for a WebSocket connection.
        
        Args:
            websocket_send_callback: Async function to send messages to WebSocket
        
        Returns:
            OrchestratorSession instance
        """
        self._session_counter += 1
        session_id = f"session_{self._session_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = OrchestratorSession(session_id, websocket_send_callback)
        self.sessions[session_id] = session
        
        logger.info(f"Created session {session_id}. Total sessions: {len(self.sessions)}")
        return session
    
    async def remove_session(self, session_id: str):
        """
        Remove and clean up a session.
        
        Args:
            session_id: ID of the session to remove
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.disconnect()
            del self.sessions[session_id]
            logger.info(f"Removed session {session_id}. Total sessions: {len(self.sessions)}")
    
    def get_session(self, session_id: str) -> Optional[OrchestratorSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return len(self.sessions)
