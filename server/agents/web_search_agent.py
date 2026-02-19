"""Web Search Agent powered by browser-use for advanced web automation and information retrieval"""

from typing import List, Dict, Any, Optional
import warnings
import logging
import os
import asyncio

from browser_use import Agent, Browser, ChatOpenAI
from .base_agent import BaseAgent, Task, AgentResponse, AgentStatus
from .secure_credential_store import SecureCredentialStore
from .universal_browser_tools import UniversalBrowserTools

# Suppress warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


class WebSearchAgent(BaseAgent):
    """Agent specialized in web search, information retrieval, and universal browser automation"""
    
    def __init__(self,auth_token:str,server_url:str):
        super().__init__(
            agent_id="web_search_agent_001",
            name="Web Search Agent",
            description="Performs live web searches, retrieves structured information, and executes browser automation tasks using AI-powered control"
        )
        self.logger = logging.getLogger(__name__)
        self.browser = Browser()
        
        # Initialize LLM for natural language element selection
        base = server_url
        base = base.rstrip("/")
        self.llm = ChatOpenAI(
            model="qwen3:latest",
            api_key=auth_token,
            base_url=f"{base}/api/v1" if base else None
        )
        
        # Initialize credential store and browser tools
        self.credential_store = SecureCredentialStore()
        self.browser_tools = UniversalBrowserTools(
            credential_store=self.credential_store,
            browser=self.browser,
            llm=self.llm
        )
        
        self.logger.info("Web Search Agent initialized with universal browser automation")

    def can_handle_task(self, task: Task) -> bool:
        """Check if this agent can handle the task"""
        task_type = task.metadata.get("task_type", "")
        
        # Supported task types
        supported_types = [
            "web_search",
            "information_retrieval",
            "research",
            "browser_automation",
            "social_media",
            "file_upload",
            "file_download",
            "media_control",
            "data_extraction",
            "web_login",
            "form_filling"
        ]
        
        return task_type in supported_types

    async def process_task(self, task: Task) -> AgentResponse:
        """Process task using browser-use Agent with universal automation tools"""
        try:
            query = task.metadata.get("query", "") if isinstance(task, Task) else str(task)
            if not query:
                return AgentResponse(
                    agent_id=self.agent_id,
                    success=False,
                    error="Query not provided"
                )

            # Get LLM configuration
            llm = self.llm
            
            # Get browser tools
            tools = self.browser_tools.get_tools()
            # Build detailed system instructions
            system_message = """You are an expert web automation assistant. Your goal is to complete the user's task EXACTLY as requested.

CRITICAL RULES:
1. Do NOT perform any actions the user did not explicitly ask for
2. Only open new tabs if the user requests it
3. Complete the task efficiently without unnecessary steps
4. If a task requires login, use the 'secure_login' or 'social_login' tool with the appropriate website/platform
5. Always navigate to the required website first using 'navigate_to_url' if not already there
6. Use natural language tools to interact with page elements
7. Stop once the task is complete - do not continue with additional actions
8. Report success when the requested task is finished
9. Open a new tab and search "https://search.brave.com/" .
TASK COMPLETION:
- Login task: Complete when successfully authenticated
- Navigation task: Complete when on the correct page
- Content task: Complete when content is submitted/posted
- Information task: Complete when data is extracted and reported"""
            
            # Create browser agent with tools
            browser_agent = Agent(
                task=str(query),
                llm=llm,
                browser=self.browser,
                tools=tools,
                extend_system_message=system_message,
                max_failures=2,
                max_actions_per_step=4,
                max_history_items=7,
                source="https://search.brave.com/",
                sensitive_data=self.credential_store.get_credential(),
                
                
            )

            self.logger.info(f"Processing task: {query}")
            browser_agent.browser_session.navigate_to("https://www.brave.com",new_tab=False)
            # Run the agent
            history = await browser_agent.run()
            
            # Extract final result from history
            final_result = history.final_result() if hasattr(history, 'final_result') else str(history)

            return AgentResponse(
                agent_id=self.agent_id,
                success=True,
                result={
                    "query": query,
                    "answer": final_result,
                    "history_length": len(history.history) if hasattr(history, 'history') else 0,
                    "task_type": "browser_automation"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing task {self.agent_id}: {e}", exc_info=True)
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error=f"Browser automation failed: {str(e)}"
            )

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    

    # ==================== CREDENTIAL MANAGEMENT METHODS ====================
    # Interactive CLI methods removed for production safety and cleanup.
    # Credentials should be managed via secure API endpoints or pre-configuration.


