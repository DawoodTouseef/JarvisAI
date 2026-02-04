# central_orchestrator.py

from typing import Dict, List, Optional, Any, Set
from typing_extensions import TypedDict
from datetime import datetime
import json
import re
import asyncio
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class OrchestratorState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    STREAMING = "streaming"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    COMPLETED = "completed"


from server.services.chat_ai_server import ChatAIServer as ChatOpenAI
from langchain_core.prompts import PromptTemplate

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .deep_search_agent import DeepSearchAgent
from .response_generation_agent import ResponseGenerationAgent
from .general_purpose_agent import GeneralPurposeAgent
from .base_agent import BaseAgent, Task
from .tools.agent_clarification import agent_clarification_tool
from .local_execution_agent import LocalExecutionChatbotAgent


from .system_agent_wrapper import SystemAgentWrapper


class AgentWorkflowState(TypedDict):
    original_input: str
    decomposed_tasks: List[Dict[str, Any]]
    task_results: List[Dict[str, Any]]
    processing_result: Optional[Any]
    workflow_status: str
    errors: List[str]
    execution_log: List[str]
    auth_token: Optional[str]
    base_url: Optional[str]
    task_id: str
    orchestrator_state: str
    role_context: Optional[Dict[str, Any]]


class CentralOrchestrator:
    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.checkpointer = MemorySaver()
        self.clarification_futures: Dict[str, asyncio.Future] = {}
        self.permission_futures: Dict[str, asyncio.Future] = {}
        self.event_callback: Optional[Any] = None
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.cancelled_tasks: Set[str] = set()
        self.running_agents: Dict[str, BaseAgent] = {}
        
        self._register_default_agents()
        self._setup_workflow()
        self._setup_clarification_callback()

    def set_event_callback(self, callback):
        """Set the callback for sending events to the frontend"""
        self.event_callback = callback

    async def _emit_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        """Helper to emit events via the callback"""
        if self.event_callback:
            if task_id in self.cancelled_tasks and event_type in {"assistant_text_chunk", "assistant_text_final"}:
                return None
            return await self.event_callback(event_type, task_id, payload)

    async def _update_state(self, task_id: str, state: OrchestratorState):
        """Update and broadcast orchestrator state"""
        await self._emit_event("orchestrator_state_update", task_id, {"state": state.value})

    def _register_default_agents(self):
        system=SystemAgentWrapper()
        system.set_event_callback(self._emit_event)
        self.agents = [
            DeepSearchAgent(),
            ResponseGenerationAgent(),
            GeneralPurposeAgent(),
            system,
        ]


    def _setup_workflow(self):
        graph = StateGraph(AgentWorkflowState)

        graph.add_node("decomposer", self._decompose_node)
        graph.add_node("executor", self._execute_tasks_node)
        graph.add_node("synthesizer", self._synthesize_node)
        graph.add_node("finalizer", self._finalize_node)

        graph.add_edge("decomposer", "executor")
        graph.add_edge("executor", "synthesizer")
        graph.add_edge("synthesizer", "finalizer")
        graph.add_edge("finalizer", END)

        graph.set_entry_point("decomposer")
        self.workflow = graph.compile(checkpointer=self.checkpointer)

    def _setup_clarification_callback(self):
        """Setup the callback for clarification requests"""
        # This will be set by agent_integration when WebSocket is available
        pass

    async def submit_task(self, task_data: Dict[str, Any]) -> AgentWorkflowState:
        task_id = task_data["id"]
        from .personal_agent import PersonalAgent
        os.environ['OPENAI_API_KEY'] = task_data.get("auth_token")
        os.environ['OPENAI_API_BASE'] = task_data.get("base_url")
        self.agents.append(PersonalAgent(auth_token=task_data.get("auth_token"),server_url=task_data.get("base_url")))


        try:
            local_agent = LocalExecutionChatbotAgent()
            local_agent.set_event_callback(self._emit_event)
            self.agents.append(local_agent)
        except Exception as exc:
            logger.exception("Failed to register Local Execution Chatbot Agent: %s", exc)

        state: AgentWorkflowState = {
            "original_input": task_data["query"],
            "decomposed_tasks": [],
            "task_results": [],
            "processing_result": None,
            "workflow_status": "running",
            "errors": [],
            "execution_log": [f"Workflow started at {datetime.now()}"],
            "auth_token": task_data.get("auth_token"),
            "base_url": task_data.get("base_url"),
            "task_id": task_id,
            "orchestrator_state": OrchestratorState.THINKING.value,
            "role_context": task_data.get("role_context")
        }
        
        config = {"configurable": {"thread_id": task_id}}
        
        await self._update_state(task_id, OrchestratorState.THINKING)
        
        # Run workflow as a background task to allow for interruptions
        execution_task = asyncio.create_task(self.workflow.ainvoke(state, config))
        self.active_tasks[task_id] = execution_task
        
        try:
            final_state = await execution_task
            return final_state
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
            state["workflow_status"] = "cancelled"
            await self._update_state(task_id, OrchestratorState.CANCELLED)
            return state
        finally:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            if task_id in self.cancelled_tasks:
                self.cancelled_tasks.discard(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            self.cancelled_tasks.add(task_id)
            clarification = self.clarification_futures.pop(task_id, None)
            if clarification and not clarification.done():
                clarification.cancel()
            permission = self.permission_futures.pop(task_id, None)
            if permission and not permission.done():
                permission.set_result(False)
            await self._update_state(task_id, OrchestratorState.CANCELLED)
            return True
        return False

    async def handle_interrupt(self, task_id: str):
        """Handle user interruption"""
        agent = self.running_agents.get(task_id)
        if agent:
            interrupt = getattr(agent, "interrupt_task", None)
            if interrupt and asyncio.iscoroutinefunction(interrupt):
                await interrupt(task_id)
            else:
                cancel_task = getattr(agent, "cancel_task", None)
                if callable(cancel_task):
                    cancel_task()

        await self.cancel_task(task_id)
        await self._update_state(task_id, OrchestratorState.INTERRUPTED)
        await self._emit_event("orchestrator_error", task_id, {"message": "Interrupted by user"})

    async def _decompose_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        try:
            prompt = PromptTemplate(
                input_variables=["query", "agents", "role_info"],
                template="""
Decompose the user request into a list of tasks.
Return JSON only.

Available agents: 
{agents}

Format:
[
  {{"task_description": "...", "agent": "...","task_id": "...","dep": dependency_task_id}}
]

Search Request: {query}
Current Role: {role_info}
"""
            )
            llm = ChatOpenAI(
                model="qwen3:latest",
                api_key=state["auth_token"] or os.getenv("OPENAI_API_KEY"),
                base_url=state["base_url"] or os.getenv("OPENAI_API_BASE"),
            )
            chain = prompt | llm 
            agents_str = "\n".join([f"- {agent.name}: {agent.description}" for agent in self.agents])
            
            # Format role info
            role_dict = state.get("role_context")
            role_info = f"Role: {role_dict['role_name']}, Goals: {role_dict['behavioral_goals']}" if role_dict else "Standard Assistant"

            response = await chain.ainvoke({"query": state["original_input"], "agents": agents_str, "role_info": role_info})
            text = response.content if hasattr(response, 'content') else str(response)
            match = re.search(r"\[.*\]", text, re.DOTALL)
            state["decomposed_tasks"] = json.loads(match.group(0)) if match else []
            state["execution_log"].append("Decomposition completed")
        except Exception as e:
            state['workflow_status'] = "failed"
            state['errors'].append(f"Decomposition error: {str(e)}")
            state["execution_log"].append(f"Decomposition failed: {str(e)}")

        return state

    async def _execute_tasks_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        if state["workflow_status"] == "failed":
            return state

        results = []

        for item in state["decomposed_tasks"]:
            agent = next((agent for agent in self.agents if agent.name == item.get("agent")), None)
            if not agent:
                state["workflow_status"] = "failed"
                error_msg = f"Unknown agent requested: {item.get('agent')}"
                state["errors"].append(error_msg)
                state["execution_log"].append(error_msg)
                break
            task = Task(
                metadata={
                    "query": item["task_description"],
                    "parent_task_id": item.get("dep") or item.get("task_id"),
                    "auth_token": state.get("auth_token"),
                    "base_url": state.get("base_url"),
                    "role_context": state.get("role_context"),
                    "permission_callback": lambda desc, op, risk: self.request_permission(state["task_id"], desc, op, risk)
                }
            )

            self.running_agents[state["task_id"]] = agent
            await self._update_state(state["task_id"], OrchestratorState.RUNNING)
            response = await agent.process_task(task)
            results.append({
                    "task": item["task_description"],
                    "agent": agent.name,
                    "success": response.success,
                    "result": response.result,
                    "error": response.error,
            })
            if state["task_id"] in self.running_agents:
                del self.running_agents[state["task_id"]]
            

        state["task_results"] = results
        state["execution_log"].append("Execution completed")
        return state

    async def _synthesize_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        if state["workflow_status"] == "failed":
            return state
        if state["task_id"] in self.cancelled_tasks:
            state["workflow_status"] = "cancelled"
            return state

        agent = ResponseGenerationAgent()
        task = Task(
            metadata={
                "original_input": state["original_input"],
                "task_results": state["task_results"],
                "decomposed_tasks": state.get("decomposed_tasks", []),
                "auth_token": state.get("auth_token"),
                "base_url": state.get("base_url"),
            }
        )

        response = await agent.process_task(task)
        
        if response.success:
            state["processing_result"] = response.result
            state["workflow_status"] = "processed"
            
            # Emit the final response in chunks for the frontend TTS
            await self._update_state(state["task_id"], OrchestratorState.STREAMING)
            
            full_text = response.result
            # Simulate streaming chunks (in a real scenario, the agent would yield chunks)
            chunks = re.split(r'(\s+)', full_text)
            for chunk in chunks:
                if state["task_id"] in self.cancelled_tasks:
                    break
                if chunk.strip():
                    await self._emit_event("assistant_text_chunk", state["task_id"], {"text": chunk})
                    await asyncio.sleep(0.02) # Small delay for smoother perceived streaming
            
            if state["task_id"] not in self.cancelled_tasks:
                await self._emit_event("assistant_text_final", state["task_id"], {"text": full_text})
        else:
            state["errors"].append(response.error)
            state["workflow_status"] = "failed"
            logger.error(f"Execution error: {response.error}")
            await self._emit_event("orchestrator_error", state["task_id"], {"message": response.error})

        return state

    async def _finalize_node(self, state: AgentWorkflowState) -> AgentWorkflowState:
        if state["workflow_status"] == "processed":
            state["workflow_status"] = "completed"
            state["execution_log"].append("Workflow completed successfully")
            await self._update_state(state["task_id"], OrchestratorState.COMPLETED)
        else:
            state["execution_log"].append("Workflow failed")
            logger.error(f"Workflow failed: {state['errors']}")
            await self._update_state(state["task_id"], OrchestratorState.FAILED)

        return state


    async def request_clarification(self, task_id: str, question: str) -> str:
        """Request clarification from the user and pause until response"""
        if task_id not in self.clarification_futures:
            self.clarification_futures[task_id] = asyncio.Future()
        
        await self._update_state(task_id, OrchestratorState.PAUSED)
        await self._emit_event("clarification_required", task_id, {"question_text": question})
        
        try:
            response = await self.clarification_futures[task_id]
            await self._update_state(task_id, OrchestratorState.THINKING)
            return response
        finally:
            if task_id in self.clarification_futures:
                del self.clarification_futures[task_id]

    async def request_permission(self, task_id: str, command_summary: str, exact_operation: str, risk_level: str) -> bool:
        """Request permission for a system action and pause until response"""
        if task_id not in self.permission_futures:
            self.permission_futures[task_id] = asyncio.Future()
            
        await self._update_state(task_id, OrchestratorState.PAUSED)
        await self._emit_event("system_permission_required", task_id, {
            "command_summary": command_summary,
            "exact_operation": exact_operation,
            "risk_level": risk_level
        })
        
        try:
            approved = await self.permission_futures[task_id]
            await self._update_state(task_id, OrchestratorState.THINKING)
            return approved
        finally:
            if task_id in self.permission_futures:
                del self.permission_futures[task_id]

    def resolve_clarification(self, task_id: str, response: str) -> bool:
        """Resolve a pending clarification request"""
        if task_id in self.clarification_futures:
            self.clarification_futures[task_id].set_result(response)
            return True
        return agent_clarification_tool.resolve_clarification(task_id, response)
    
    def resolve_permission(self, task_id: str, approved: bool) -> bool:
        """Resolve a pending permission request"""
        if task_id in self.permission_futures:
            self.permission_futures[task_id].set_result(approved)
            return True
        return False
    
    def set_clarification_websocket_callback(self, callback):
        """
        Set the WebSocket callback for sending clarification requests to frontend
        
        Args:
            callback: async function(question, task_id) that sends to frontend
        """
        agent_clarification_tool.set_websocket_callback(callback)
