# Mock all external dependencies FIRST, before any other imports
import sys
from unittest.mock import MagicMock

# Mock ALL external dependencies before importing anything else
sys.modules['langchain'] = MagicMock()
sys.modules['langchain.prompts'] = MagicMock()
sys.modules['langchain.chains'] = MagicMock()
sys.modules['langchain.chains.llm'] = MagicMock()
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain_core'] = MagicMock()
sys.modules['langchain_core.prompts'] = MagicMock()
sys.modules['langchain_core.language_models'] = MagicMock()
sys.modules['langchain_core.tools'] = MagicMock()
sys.modules['langgraph'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()
sys.modules['langgraph.checkpoint'] = MagicMock()
sys.modules['langgraph.checkpoint.memory'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['mongita'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['duckduckgo_search'] = MagicMock()
sys.modules['autogen'] = MagicMock()
sys.modules['autogen.agentchat'] = MagicMock()
sys.modules['autogen.agents.experimental'] = MagicMock()
sys.modules['autogen.agents.experimental.deep_research'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['seaborn'] = MagicMock()
sys.modules['agents.SystemAgent.agent.planner'] = MagicMock()
sys.modules['agents.SystemAgent.agent.executor'] = MagicMock()
sys.modules['agents.SystemAgent.agent.schemas'] = MagicMock()
sys.modules['agents.SystemAgent.agent.synthesizer'] = MagicMock()
sys.modules['agents.SystemAgent.agent.orchestrator'] = MagicMock()
sys.modules['agents.SystemAgent.agent.active_memory'] = MagicMock()
sys.modules['agents.SystemAgent.agent.logger'] = MagicMock()
sys.modules['agents.SystemAgent.agent.learning'] = MagicMock()
sys.modules['agents.SystemAgent.agent.safety_guard'] = MagicMock()
sys.modules['agents.SystemAgent.agent.registry'] = MagicMock()
sys.modules['agents.codeinterpreterapi'] = MagicMock()
sys.modules['agents.codeinterpreterapi.session'] = MagicMock()
sys.modules['agents.codeinterpreterapi.chains'] = MagicMock()
sys.modules['agents.codeinterpreterapi.schema'] = MagicMock()
sys.modules['agents.codeinterpreterapi.config'] = MagicMock()
sys.modules['agents.tools.agent_utility'] = MagicMock()
sys.modules['agents.SystemAgent.memory.long_term'] = MagicMock()
sys.modules['agents.SystemAgent.memory.short_term'] = MagicMock()
sys.modules['agents.SystemAgent.utils.json_engine'] = MagicMock()
sys.modules['agents.SystemAgent.agent_config'] = MagicMock()
sys.modules['pocketsphinx'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['webrtcvad'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torch.nn'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()
sys.modules['langchain.agents'] = MagicMock()
sys.modules['langchain.agents.agent'] = MagicMock()
sys.modules['langchain.agents.agent.OutputParser'] = MagicMock()
sys.modules['codeboxapi'] = MagicMock()
sys.modules['codeboxapi.schema'] = MagicMock()
sys.modules['codeboxapi.local'] = MagicMock()
sys.modules['psutil'] = MagicMock()
sys.modules['pynvml'] = MagicMock()
sys.modules['langchain.agents.openai_functions_agent'] = MagicMock()
sys.modules['langchain.agents.openai_functions_agent.base'] = MagicMock()
sys.modules['codeboxapi.client'] = MagicMock()
sys.modules['codeboxapi.local_client'] = MagicMock()
sys.modules['langchain_core.agents'] = MagicMock()
sys.modules['langchain_core.agents.AgentAction'] = MagicMock()
sys.modules['langchain_core.agents.AgentActionMessageLog'] = MagicMock()
sys.modules['langchain_core.agents.AgentFinish'] = MagicMock()
sys.modules['langchain_core.exceptions'] = MagicMock()
sys.modules['langchain_core.exceptions.OutputParserException'] = MagicMock()
sys.modules['langchain_core.messages'] = MagicMock()
sys.modules['langchain_core.messages.AIMessage'] = MagicMock()
sys.modules['langchain_core.messages.BaseMessage'] = MagicMock()
sys.modules['langchain_core.outputs'] = MagicMock()
sys.modules['langchain_core.outputs.ChatGeneration'] = MagicMock()
sys.modules['langchain_core.outputs.Generation'] = MagicMock()
sys.modules['langchain_core.prompts.chat'] = MagicMock()
sys.modules['langchain_core.prompts.chat.ChatPromptTemplate'] = MagicMock()
sys.modules['langchain_core.prompts.chat.HumanMessagePromptTemplate'] = MagicMock()
sys.modules['codeboxapi.types'] = MagicMock()
sys.modules['codeboxapi.types.CodeBoxOutput'] = MagicMock()
sys.modules['langchain.callbacks'] = MagicMock()
sys.modules['langchain.callbacks.base'] = MagicMock()
sys.modules['langchain.callbacks.base.Callbacks'] = MagicMock()
sys.modules['langchain.chat_models'] = MagicMock()
sys.modules['langchain.chat_models.base'] = MagicMock()
sys.modules['langchain.chat_models.base.BaseChatModel'] = MagicMock()
sys.modules['langchain.memory'] = MagicMock()
sys.modules['langchain.memory.buffer'] = MagicMock()
sys.modules['langchain.memory.buffer.ConversationBufferMemory'] = MagicMock()
sys.modules['langchain_core.chat_history'] = MagicMock()
sys.modules['langchain_core.chat_history.InMemoryChatMessageHistory'] = MagicMock()
sys.modules['langchain_core._api'] = MagicMock()
sys.modules['langchain_core._api.deprecated'] = MagicMock()

# Now safe to import other modules
import unittest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime

from server.agents.base_agent import BaseAgent, Task, AgentResponse, AgentStatus
from server.agents.web_search_agent import WebSearchAgent
from server.agents.deep_search_agent import DeepSearchAgent
from server.agents.code_interpreter_agent import CodeInterpreterAgent
from server.agents.system_agent_wrapper import SystemAgentWrapper
from server.agents.response_generation_agent import ResponseGenerationAgent


class TestBaseAgent(unittest.TestCase):
    def test_abstract_methods(self):
        """Test that BaseAgent has abstract methods that must be implemented"""
        from abc import ABC
        
        # BaseAgent should be an abstract class
        self.assertTrue(issubclass(BaseAgent, ABC))
        
        # Instantiating BaseAgent directly should raise TypeError
        with self.assertRaises(TypeError):
            BaseAgent(name="Test", description="Test agent")

    def test_base_agent_initialization(self):
        """Test BaseAgent initialization"""
        class ConcreteAgent(BaseAgent):
            async def process_task(self, task: Task) -> AgentResponse:
                return AgentResponse(agent_id=self.agent_id, success=True, result={})
            
            def can_handle_task(self, task: Task) -> bool:
                return True
        
        agent = ConcreteAgent(name="Test Agent", description="A test agent", agent_id="test_123")
        
        self.assertEqual(agent.agent_id, "test_123")
        self.assertEqual(agent.name, "Test Agent")
        self.assertEqual(agent.description, "A test agent")
        self.assertEqual(agent.status, AgentStatus.PENDING)

    def test_get_status_info(self):
        """Test getting agent status information"""
        class ConcreteAgent(BaseAgent):
            async def process_task(self, task: Task) -> AgentResponse:
                return AgentResponse(agent_id=self.agent_id, success=True, result={})
            
            def can_handle_task(self, task: Task) -> bool:
                return True
        
        agent = ConcreteAgent(name="Test Agent", description="A test agent", agent_id="test_123")
        
        status_info = agent.get_status_info()
        
        self.assertEqual(status_info["agent_id"], "test_123")
        self.assertEqual(status_info["name"], "Test Agent")
        self.assertEqual(status_info["description"], "A test agent")
        self.assertEqual(status_info["status"], "pending")


class TestWebSearchAgent(unittest.TestCase):
    def setUp(self):
        self.agent = WebSearchAgent()

    def test_initialization(self):
        """Test WebSearchAgent initialization"""
        self.assertEqual(self.agent.name, "Web Search Agent")
        self.assertEqual(self.agent.description, "Performs web searches, gets current information, and retrieves general knowledge")
        self.assertEqual(self.agent.max_results, 5)

    def test_can_handle_task(self):
        """Test WebSearchAgent can_handle_task method"""
        # Task with web search type
        web_task = Task(metadata={"task_type": "web_search"})
        self.assertTrue(self.agent.can_handle_task(web_task))
        
        # Task with general type
        general_task = Task(metadata={"task_type": "general"})
        self.assertTrue(self.agent.can_handle_task(general_task))
        
        # Task with other type
        other_task = Task(metadata={"task_type": "code_interpretation"})
        self.assertFalse(self.agent.can_handle_task(other_task))
        
        # Task without type (should default to True for general capability)
        no_type_task = Task(metadata={})
        self.assertTrue(self.agent.can_handle_task(no_type_task))

    def test_process_task_success(self):
        """Test processing a successful web search task"""
        async def run_test():
            task = Task(metadata={
                "query": "test search query",
                "task_type": "web_search"
            })
            
            # Mock the search methods
            with patch.object(self.agent, '_search_web') as mock_search:
                mock_search.coro = AsyncMock(return_value=[
                    {"title": "Test Result", "url": "http://test.com", "snippet": "Test snippet"}
                ])
                
                response = await self.agent.process_task(task)
                
                self.assertTrue(response.success)
                self.assertIsNotNone(response.result)
                self.assertEqual(response.agent_id, self.agent.agent_id)
                
                result_data = response.result
                self.assertEqual(result_data["query"], "test search query")
                self.assertEqual(result_data["search_type"], "general")
                self.assertEqual(len(result_data["results"]), 1)
                self.assertEqual(result_data["result_count"], 1)
                self.assertIn("summary", result_data)
        
        asyncio.run(run_test())

    def test_process_task_missing_query(self):
        """Test processing a task without query"""
        async def run_test():
            task = Task(metadata={"task_type": "web_search"})  # No query
            
            response = await self.agent.process_task(task)
            
            self.assertFalse(response.success)
            self.assertIn("Query not provided", response.error)
        
        asyncio.run(run_test())

    def test_process_task_exception_handling(self):
        """Test processing a task that raises an exception"""
        async def run_test():
            task = Task(metadata={"query": "test query", "task_type": "web_search"})
            
            # Mock the search method to raise an exception
            with patch.object(self.agent, '_search_web') as mock_search:
                mock_search.coro = AsyncMock(side_effect=Exception("Search failed"))
                
                response = await self.agent.process_task(task)
                
                self.assertFalse(response.success)
                self.assertIn("Search failed", response.error)
        
        asyncio.run(run_test())


class TestDeepSearchAgent(unittest.TestCase):
    def setUp(self):
        self.agent = DeepSearchAgent()

    def test_initialization(self):
        """Test DeepSearchAgent initialization"""
        self.assertEqual(self.agent.name, "Deep Search Agent")
        self.assertEqual(self.agent.description, "Performs multi-step reasoning, complex research, and investigative analysis")
        self.assertEqual(self.agent.max_reasoning_steps, 5)

    def test_can_handle_task(self):
        """Test DeepSearchAgent can_handle_task method"""
        # Task with deep search type
        deep_search_task = Task(metadata={"task_type": "deep_search"})
        self.assertTrue(self.agent.can_handle_task(deep_search_task))
        
        # Task with investigative research type
        inv_task = Task(metadata={"task_type": "investigative_research"})
        self.assertTrue(self.agent.can_handle_task(inv_task))
        
        # Task with complex analysis type
        ca_task = Task(metadata={"task_type": "complex_analysis"})
        self.assertTrue(self.agent.can_handle_task(ca_task))
        
        # Task with other type
        other_task = Task(metadata={"task_type": "web_search"})
        self.assertFalse(self.agent.can_handle_task(other_task))

    @unittest.skip("Skipping deep search process_task test as it requires external dependencies")
    def test_process_task_success(self):
        """Test processing a successful deep search task (requires external dependencies)"""
        async def run_test():
            task = Task(metadata={
                "query": "complex research query",
                "task_type": "deep_search",
                "auth_token": "test_token",
                "base_url": "http://test.com"
            })
            
            response = await self.agent.process_task(task)
            
            # The actual result depends on external services
            self.assertIsNotNone(response)
            self.assertEqual(response.agent_id, self.agent.agent_id)
        
        asyncio.run(run_test())

    def test_process_task_missing_query(self):
        """Test processing a task without query"""
        async def run_test():
            task = Task(metadata={"task_type": "deep_search"})  # No query
            
            response = await self.agent.process_task(task)
            
            self.assertFalse(response.success)
            self.assertIn("Research query not provided", response.error)
        
        asyncio.run(run_test())


class TestCodeInterpreterAgent(unittest.TestCase):
    def setUp(self):
        self.agent = CodeInterpreterAgent()

    def test_initialization(self):
        """Test CodeInterpreterAgent initialization"""
        self.assertEqual(self.agent.name, "Code Interpreter Agent")
        self.assertEqual(self.agent.description, "Executes Python code for data analysis, math, and visualization")
        self.assertIsNone(self.agent.session)

    def test_can_handle_task(self):
        """Test CodeInterpreterAgent can_handle_task method"""
        # Task with Code agent
        code_task = Task(metadata={"agent": "Code"})
        self.assertTrue(self.agent.can_handle_task(code_task))
        
        # Task with code interpretation type
        ci_task = Task(metadata={"task_type": "code_interpretation"})
        self.assertTrue(self.agent.can_handle_task(ci_task))
        
        # Task with other agent
        other_task = Task(metadata={"agent": "Web"})
        self.assertFalse(self.agent.can_handle_task(other_task))

    @unittest.skip("Skipping code interpreter process_task test as it requires external dependencies")
    def test_process_task_success(self):
        """Test processing a successful code interpretation task (requires external dependencies)"""
        async def run_test():
            task = Task(metadata={
                "query": "calculate 2+2",
                "task_type": "code_interpretation"
            })
            
            response = await self.agent.process_task(task)
            
            # The actual result depends on external services
            self.assertIsNotNone(response)
            self.assertEqual(response.agent_id, self.agent.agent_id)
        
        asyncio.run(run_test())

    def test_process_task_missing_query(self):
        """Test processing a task without query"""
        async def run_test():
            task = Task(metadata={"task_type": "code_interpretation"})  # No query
            
            # Mock the internal methods to avoid external dependencies
            with patch.object(self.agent, '_get_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_session.agenerate_response.coro = AsyncMock(return_value=MagicMock(content="No query provided", files=[]))
                mock_get_session.coro = AsyncMock(return_value=mock_session)
                
                response = await self.agent.process_task(task)
                
                # Should still attempt to process with empty query
                self.assertIsNotNone(response)
                self.assertEqual(response.agent_id, self.agent.agent_id)
        
        asyncio.run(run_test())

    async def async_test_stop_method(self):
        """Test the stop method"""
        # Mock the session
        mock_session = AsyncMock()
        self.agent.session = mock_session
        
        await self.agent.stop()
        
        # Verify session was stopped
        mock_session.astop.assert_called_once()
        self.assertIsNone(self.agent.session)

    def test_stop_method(self):
        """Test the stop method"""
        async def run_test():
            await self.async_test_stop_method()
        asyncio.run(run_test())


class TestSystemAgentWrapper(unittest.TestCase):
    def setUp(self):
        self.agent = SystemAgentWrapper()

    def test_initialization(self):
        """Test SystemAgentWrapper initialization"""
        self.assertEqual(self.agent.name, "System Control Agent")
        self.assertEqual(self.agent.description, "Advanced OS control, file management, and system task automation")
        self.assertIsNone(self.agent.orchestrator)

    def test_can_handle_task(self):
        """Test SystemAgentWrapper can_handle_task method"""
        # Task with System agent
        sys_task = Task(metadata={"agent": "System"})
        self.assertTrue(self.agent.can_handle_task(sys_task))
        
        # Task with system control type
        sc_task = Task(metadata={"task_type": "system_control"})
        self.assertTrue(self.agent.can_handle_task(sc_task))
        
        # Task with other agent
        other_task = Task(metadata={"agent": "Web"})
        self.assertFalse(self.agent.can_handle_task(other_task))

    @unittest.skip("Skipping system agent process_task test as it requires external dependencies")
    def test_process_task_success(self):
        """Test processing a successful system control task (requires external dependencies)"""
        async def run_test():
            task = Task(metadata={
                "query": "perform system task",
                "agent": "System",
                "auth_token": "test_token",
                "base_url": "http://test.com"
            })
            
            response = await self.agent.process_task(task)
            
            # The actual result depends on external services
            self.assertIsNotNone(response)
            self.assertEqual(response.agent_id, self.agent.agent_id)
        
        asyncio.run(run_test())

    def test_process_task_no_orchestrator(self):
        """Test processing a task when orchestrator fails to initialize"""
        async def run_test():
            task = Task(metadata={
                "query": "test query",
                "agent": "System"
            })
            
            # Mock the initialization to return None (failure case)
            with patch.object(self.agent, '_initialize_system_orchestrator') as mock_init:
                mock_init.return_value = None
                
                response = await self.agent.process_task(task)
                
                self.assertFalse(response.success)
                self.assertIn("not initialized", response.error)
        
        asyncio.run(run_test())


class TestResponseGenerationAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ResponseGenerationAgent()

    def test_initialization(self):
        """Test ResponseGenerationAgent initialization"""
        self.assertEqual(self.agent.name, "Response Generation Agent")
        self.assertEqual(self.agent.description, "Synthesizes multiple agent results into a single, cohesive JARVIS-style response")
        self.assertIsNone(self.agent.llm)

    def test_can_handle_task(self):
        """Test ResponseGenerationAgent can_handle_task method"""
        # Task with response generation type
        rg_task = Task(metadata={"task_type": "response_generation"})
        self.assertTrue(self.agent.can_handle_task(rg_task))
        
        # Task with other type
        other_task = Task(metadata={"task_type": "web_search"})
        self.assertFalse(self.agent.can_handle_task(other_task))

    def test_process_task_success(self):
        """Test processing a successful response generation task"""
        async def run_test():
            task = Task(metadata={
                "task_type": "response_generation",
                "original_input": "What's the weather?",
                "task_results": [{"task": "weather search", "result": "sunny"}],
                "decomposed_tasks": [{"task_description": "search weather", "agent": "Web"}]
            })
            
            # Mock the LLM to avoid external dependencies
            with patch('agents.response_generation_agent.ChatOpenAI') as mock_llm_class, \
                 patch('agents.response_generation_agent.LLMChain') as mock_chain_class:
                
                mock_chain = AsyncMock()
                mock_chain.ainvoke.coro = AsyncMock(return_value="The weather is sunny today.")
                
                mock_chain_class.return_value = mock_chain
                
                response = await self.agent.process_task(task)
                
                self.assertTrue(response.success)
                self.assertEqual(response.agent_id, self.agent.agent_id)
                self.assertIn("sunny today", response.result)
        
        asyncio.run(run_test())

    def test_process_task_with_auth(self):
        """Test processing a task with authentication tokens"""
        async def run_test():
            task = Task(metadata={
                "task_type": "response_generation",
                "original_input": "Summarize the report",
                "task_results": [{"task": "analyze report", "result": "report content"}],
                "decomposed_tasks": [{"task_description": "analyze", "agent": "Analysis"}],
                "auth_token": "test_token",
                "base_url": "http://test.com"
            })
            
            # Mock the LLM to avoid external dependencies
            with patch('agents.response_generation_agent.ChatOpenAI') as mock_llm_class, \
                 patch('agents.response_generation_agent.LLMChain') as mock_chain_class:
                
                # Verify the get_llm method is called with the right parameters
                mock_llm_instance = MagicMock()
                mock_llm_class.return_value = mock_llm_instance
                
                mock_chain = AsyncMock()
                mock_chain.ainvoke.coro = AsyncMock(return_value="Summary of the report.")
                
                mock_chain_class.return_value = mock_chain
                
                response = await self.agent.process_task(task)
                
                # Verify that ChatOpenAI was called with the task's auth_token and base_url
                mock_llm_class.assert_called()
                self.assertTrue(response.success)
        
        asyncio.run(run_test())

    def test_process_task_failure(self):
        """Test processing a task that fails"""
        async def run_test():
            task = Task(metadata={
                "task_type": "response_generation",
                "original_input": "Test input",
                "task_results": [],
                "decomposed_tasks": []
            })
            
            # Mock the LLM to raise an exception
            with patch('agents.response_generation_agent.ChatOpenAI') as mock_llm_class:
                mock_llm_class.side_effect = Exception("LLM initialization failed")
                
                response = await self.agent.process_task(task)
                
                self.assertFalse(response.success)
                self.assertIn("Response synthesis failed", response.error)
        
        asyncio.run(run_test())


class TestAgentIntegration(unittest.TestCase):
    """Tests for how agents work together in the orchestration system"""
    
    def test_agent_capability_distinction(self):
        """Test that different agents have distinct capabilities"""
        web_agent = WebSearchAgent()
        code_agent = CodeInterpreterAgent()
        system_agent = SystemAgentWrapper()
        search_agent = DeepSearchAgent()
        response_agent = ResponseGenerationAgent()
        
        # Create tasks for different purposes
        web_task = Task(metadata={"task_type": "web_search", "query": "current news"})
        code_task = Task(metadata={"task_type": "code_interpretation", "query": "calculate sum"})
        system_task = Task(metadata={"task_type": "system_control", "query": "list files"})
        search_task = Task(metadata={"task_type": "deep_search", "query": "analyze market trends"})
        response_task = Task(metadata={"task_type": "response_generation", "original_input": "summarize"})
        
        # Each agent should only handle its designated tasks
        self.assertTrue(web_agent.can_handle_task(web_task))
        self.assertFalse(web_agent.can_handle_task(code_task))
        self.assertFalse(web_agent.can_handle_task(system_task))
        self.assertFalse(web_agent.can_handle_task(search_task))
        self.assertFalse(web_agent.can_handle_task(response_task))
        
        self.assertFalse(code_agent.can_handle_task(web_task))
        self.assertTrue(code_agent.can_handle_task(code_task))
        self.assertFalse(code_agent.can_handle_task(system_task))
        self.assertFalse(code_agent.can_handle_task(search_task))
        self.assertFalse(code_agent.can_handle_task(response_task))
        
        self.assertFalse(system_agent.can_handle_task(web_task))
        self.assertFalse(system_agent.can_handle_task(code_task))
        self.assertTrue(system_agent.can_handle_task(system_task))
        self.assertFalse(system_agent.can_handle_task(search_task))
        self.assertFalse(system_agent.can_handle_task(response_task))
        
        self.assertFalse(search_agent.can_handle_task(web_task))
        self.assertFalse(search_agent.can_handle_task(code_task))
        self.assertFalse(search_agent.can_handle_task(system_task))
        self.assertTrue(search_agent.can_handle_task(search_task))
        self.assertFalse(search_agent.can_handle_task(response_task))
        
        self.assertFalse(response_agent.can_handle_task(web_task))
        self.assertFalse(response_agent.can_handle_task(code_task))
        self.assertFalse(response_agent.can_handle_task(system_task))
        self.assertFalse(response_agent.can_handle_task(search_task))
        self.assertTrue(response_agent.can_handle_task(response_task))


if __name__ == '__main__':
    unittest.main()