"""Response Generation Agent - JARVIS-style unified response synthesizer"""

from typing import Optional
import json
from .base_agent import BaseAgent, Task, AgentResponse
from langchain_core.prompts import PromptTemplate
import requests

class ResponseGenerationAgent(BaseAgent):
    """Agent for synthesizing multi-agent results into a unified JARVIS-style response"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            agent_id="response_gen_agent_001",
            name="Response Generation Agent",
            description="Synthesizes multiple agent results into a single, cohesive JARVIS-style response"
        )
        self.llm = None 
        
    def can_handle_task(self, task) -> bool:

        return task == "response_generation"
        
    async def get_users(self,auth_token: str,base_url: str):
        try:
            response = requests.get(f"{base_url}/auths/", headers={"Authorization": f"Bearer {auth_token}"})
            result = response.json()
            
            user_info= f"Name: {result['name']}\nEmail: {result['email']}\n"
            return user_info
        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error=f"Failed to get users: {str(e)}"
            )
    async def process_task(self, task: Task) -> AgentResponse:
        """Synthesize results into a unified response"""
        try:
            task_id = task.metadata.get("parent_task_id") or task.id
            await self.emit_event("active_agent", task_id, {"agent": self.name})
            await self.emit_event("agent_state", task_id, {"state": "executing", "agent": self.name})
            await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Synthesizing response"})
            original_input = task.metadata.get("original_input", "")
            task_results = task.metadata.get("task_results", [])
            decomposed_tasks = task.metadata.get("decomposed_tasks", [])
            
            prompt = PromptTemplate(
                input_variables=["original_input", "task_results", "decomposed_tasks"],
                template="""
                You are J.A.R.V.I.S., an advanced, highly intelligent, and polite AI assistant.
                
                Your goal is to provide a single, unified response to the user's original request based on the results from various specialized agents that handled different parts of the request.
                
                Original User Request: "{original_input}"
                
                Decomposed Tasks and their respective Agents:
                {decomposed_tasks}
                
                Results from Agents:
                {task_results}
                
                User Information:
                {user_info}
                
                Instructions:
                1. Synthesize all the information into a single, cohesive narrative.
                2. Use a human-like, professional, yet slightly conversational tone (JARVIS style).
                3. Address the user politely (e.g., "Sir," "Madam," or just a respectful tone).
                4. Do not mention that multiple agents were used unless it is naturally relevant to the explanation.
                5. Ensure the response directly answers all parts of the original request.
                6. If any part of the request failed, acknowledge it gracefully and offer assistance.
                7. The response should feel like it's coming from one unified mind.
                8. Don't include any special character in it.
                Unified Response:
                """
            )
            
            llm = self.get_llm(task)

            chain = prompt | llm
            
            # Format task results and decomposed tasks for the prompt
            formatted_tasks = json.dumps(decomposed_tasks, indent=2)
            formatted_results = json.dumps(task_results, indent=2)
            user_info = await self.get_users(task.metadata.get("auth_token"), task.metadata.get("base_url"))
            
            response_msg = await chain.ainvoke({
                "original_input": original_input,
                "decomposed_tasks": formatted_tasks,
                "task_results": formatted_results,
                "user_info": user_info
            })
            
            unified_response_text = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
            
            return AgentResponse(
                agent_id=self.agent_id,
                success=True,
                result=unified_response_text
            )
            
        except Exception as e:
            await self.emit_event("error_event", task.metadata.get("parent_task_id") or task.id, {
                "source": "response_generation",
                "agent": self.name,
                "message": f"Response synthesis failed: {str(e)}"
            })
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error=f"Response synthesis failed: {str(e)}"
            )
