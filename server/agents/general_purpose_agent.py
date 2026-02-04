"""General-Purpose Agentic AI implementation for Jarvis"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Union

from pydantic import BaseModel, Field
from .base_agent import BaseAgent, Task, AgentResponse, AgentStatus
from .tools.tool_system import registry as tool_registry

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ReasoningStep(BaseModel):
    thought: str = Field(..., description="The internal reasoning/thought process of the agent")
    action: str = Field(..., description="The action to take: 'tool_call', 'wait', or 'final_response'")
    tool_name: Optional[str] = Field(None, description="Name of the tool to call")
    tool_input: Optional[Dict[str, Any]] = Field(None, description="Input parameters for the tool")
    response: Optional[str] = Field(None, description="Final response to the user")

class GeneralPurposeAgent(BaseAgent):
    """
    A unified autonomous agent capable of reasoning, planning, and tool use.
    Implements a 4-layer architecture: Perception, Reasoning, Execution, and Control.
    """

    def __init__(self):
        super().__init__(
            agent_id="general_purpose_agent_v1",
            name="General-Purpose Agent",
            description="Autonomous agent for planning, reasoning, and multi-step task execution."
        )
        self.state = AgentState.IDLE
        self.max_steps = 10
        self.max_execution_time = 300  # 5 minutes
        self._cancellation_requested = False

    def can_handle_task(self, task: Task) -> bool:
        # This agent is general purpose, so it can handle almost anything if routed here.
        # Orchestrator should decide when to use this vs specialized agents.
        return True

    async def process_task(self, task: Task) -> AgentResponse:
        """Main entry point for task processing"""
        self.status = AgentStatus.RUNNING
        self.state = AgentState.PLANNING
        self._cancellation_requested = False
        
        task_id = task.id
        user_query = task.metadata.get("query", "")
        context = task.metadata.get("context", [])
        
        # History for reasoning loop
        internal_history = []
        
        try:
            # Wrap entire loop in timeout for safety (Control Layer)
            async with asyncio.timeout(self.max_execution_time):
                for step_idx in range(self.max_steps):
                    # Check for cancellation (Control Layer)
                    if self._cancellation_requested:
                        self.state = AgentState.CANCELLED
                        return self._create_response(task, "Task cancelled by user", success=False)

                    # Context Summarization (Requirement 5)
                    if len(internal_history) > 5:
                        summary = await self._summarize_context(llm, internal_history[:-2])
                        internal_history = [{"thought": "Previous steps summary", "summary": summary}] + internal_history[-2:]

                    # 1. Perception Layer: Refine intent and context
                    intent_profile = self._perception_layer(user_query, context, internal_history)
                    
                    # Emit heartbeat/event
                    await self._emit_event(task_id, "step_started", {"step": step_idx, "state": self.state})

                    # 2. Reasoning Layer: Decide next action
                    llm = self.get_llm(task)
                    reasoning = await self._reasoning_layer(llm, intent_profile, internal_history)
                    
                    await self._emit_event(task_id, "plan_created", {"thought": reasoning.thought})

                    # 3. Execution Layer: Act on decision
                    if reasoning.action == "final_response":
                        self.state = AgentState.COMPLETED
                        return self._create_response(task, reasoning.response, success=True)
                    
                    elif reasoning.action == "tool_call":
                        tool_result = await self._execute_layer(reasoning.tool_name, reasoning.tool_input, task_id)
                        internal_history.append({
                            "thought": reasoning.thought,
                            "tool": reasoning.tool_name,
                            "input": reasoning.tool_input,
                            "output": tool_result
                        })
                        
                    elif reasoning.action == "wait":
                        # Handle long-running or external dependency if needed
                        self.state = AgentState.WAITING
                        await asyncio.sleep(2) # Placeholder
                        self.state = AgentState.EXECUTING
                        
                # If we hit max steps
                return self._create_response(task, "Max reasoning steps reached without final answer.", success=False)

        except asyncio.TimeoutError:
            self.state = AgentState.FAILED
            return self._create_response(task, "Task execution timed out.", success=False)
        except Exception as e:
            logger.exception("Error in GP Agent loop")
            self.state = AgentState.FAILED
            return self._create_response(task, f"Internal Error: {str(e)}", success=False)
        finally:
            self.status = AgentStatus.COMPLETED if self.state == AgentState.COMPLETED else AgentStatus.FAILED

    def _perception_layer(self, query: str, context: List[Dict], history: List[Dict]) -> Dict[str, Any]:
        """Filters and structures inputs (Control & Perception)"""
        return {
            "query": query,
            "context_summary": f"Context has {len(context)} items",
            "history_summary": f"Completed {len(history)} steps",
            "timestamp": datetime.now().isoformat()
        }

    async def _reasoning_layer(self, llm: Any, profile: Dict, history: List[Dict]) -> ReasoningStep:
        """Determines the next step using LLM"""
        tools_desc = json.dumps(tool_registry.get_tool_definitions(), indent=2)
        
        system_prompt = f"""
You are the Jarvis General-Purpose Agent. You solve complex tasks by reasoning and using tools.

AVAILABLE TOOLS:
{tools_desc}

GUIDELINES:
1. Reason step-by-step.
2. Use tools when you need external data or computation.
3. If you have enough info, provide a final_response.
4. Keep your thoughts clear and concise.

RETURN JSON ONLY in this format:
{{
  "thought": "description of your reasoning",
  "action": "tool_call|final_response|wait",
  "tool_name": "optional name of tool",
  "tool_input": {{ "param": "value" }},
  "response": "optional final answer string"
}}
"""
        
        # Build prompt from history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {profile['query']}"}
        ]
        
        for h in history:
            messages.append({"role": "assistant", "content": f"Thought: {h['thought']}\nTool: {h['tool']}\nInput: {json.dumps(h['input'])}"})
            messages.append({"role": "user", "content": f"Tool Output: {json.dumps(h['output'])}"})
            
        try:
            # response = await llm.ainvoke(messages)
            # Simplified for development; ensuring JSON structure
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return ReasoningStep.parse_raw(match.group(0))
            else:
                raise ValueError("LLM failed to return structured JSON reasoning.")
                
        except Exception as e:
            logger.error(f"Reasoning layer error: {e}")
            return ReasoningStep(thought="Error in reasoning", action="final_response", response="I encountered an error while thinking about this task.")

    async def _execute_layer(self, tool_name: str, tool_input: Dict, task_id: str) -> Any:
        """Executes the chosen tool safely"""
        self.state = AgentState.EXECUTING
        tool = tool_registry.get_tool(tool_name)
        
        if not tool:
            return {"error": f"Tool '{tool_name}' not found."}
            
        await self._emit_event(task_id, "tool_called", {"tool": tool_name, "input": tool_input})
        
        try:
            # Tools should already be async and non-blocking (using to_thread internally where needed)
            result = await tool.run(**tool_input)
            await self._emit_event(task_id, "step_completed", {"tool": tool_name, "success": True})
            return result
        except Exception as e:
            await self._emit_event(task_id, "step_completed", {"tool": tool_name, "success": False, "error": str(e)})
            return {"error": str(e)}

    async def _summarize_context(self, llm: Any, history: List[Dict]) -> str:
        """Summarizes past steps to prevent context bloat"""
        prompt = f"Summarize the following agent execution steps concisely, preserving key facts and tool results:\n{json.dumps(history, indent=2)}"
        try:
            response = await llm.ainvoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return "Error summarizing history."

    async def _emit_event(self, task_id: str, event_type: str, data: Dict):
        """Emits structured events for observability and streaming"""
        event = {
            "type": event_type,
            "task_id": task_id,
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        logger.info(f"Agent Event: {event_type} - {data}")
        # Integration with ConnectionManager/WebSocket would go here
        # For now, it's a log. Orchestrator or Integration layer will catch these.

    def _create_response(self, task: Task, result: Any, success: bool = True) -> AgentResponse:
        return AgentResponse(
            agent_id=self.agent_id,
            success=success,
            result=result,
            error=None if success else str(result)
        )

    async def cancel(self):
        """Request immediate cancellation of the task"""
        self._cancellation_requested = True
        self.state = AgentState.CANCELLED
        logger.info("Cancellation requested for General-Purpose Agent")
