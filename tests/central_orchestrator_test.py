import unittest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Mock external dependencies before importing
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain_core.prompts'] = MagicMock()
sys.modules['langchain_core.language_models'] = MagicMock()
sys.modules['langchain_core.tools'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()
sys.modules['langgraph.checkpoint.memory'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['mongita'] = MagicMock()

from server.agents.central_orchestrator import CentralOrchestrator
from server.agents.task_manager import TaskManager
from server.agents.base_agent import BaseAgent, Task, AgentResponse
from server.agents.web_search_agent import WebSearchAgent
from server.agents.response_generation_agent import ResponseGenerationAgent
from server.agents.code_interpreter_agent import CodeInterpreterAgent
from server.agents.system_agent_wrapper import SystemAgentWrapper
from server.agents.deep_search_agent import DeepSearchAgent


class MockAgent(BaseAgent):
    """Mock agent for testing"""
    def __init__(self, agent_id: str, name: str, can_handle: bool = True):
        super().__init__(agent_id=agent_id, name=name, description=f"Mock {name}")
        self.can_handle_result = can_handle
        self.processed_tasks = []
        self.process_task_result = AgentResponse(
            agent_id=agent_id,
            success=True,
            result={"mock": "result"}
        )

    async def process_task(self, task: Task) -> AgentResponse:
        self.processed_tasks.append(task)
        return self.process_task_result

    def can_handle_task(self, task: Task) -> bool:
        return self.can_handle_result


class TestCentralOrchestrator(unittest.TestCase):
    def setUp(self):
        self.task_manager = TaskManager()
        self.orchestrator = CentralOrchestrator(self.task_manager)

    def test_initialization(self):
        """Test CentralOrchestrator initialization"""
        self.assertIsNotNone(self.orchestrator.task_manager)
        self.assertIsNotNone(self.orchestrator.agents)
        self.assertIsNotNone(self.orchestrator.event_callbacks)
        self.assertIsNotNone(self.orchestrator.clarification_futures)
        self.assertIsNotNone(self.orchestrator.utility_tool)
        
        # Check default agents are registered
        expected_agents = ["Search", "Web", "Response", "System", "Code", "General"]
        for agent_id in expected_agents:
            self.assertIn(agent_id, self.orchestrator.agents)

    def test_register_agent(self):
        """Test registering a new agent"""
        mock_agent = MockAgent("test_agent", "Test Agent")
        self.orchestrator.register_agent("TestAgent", mock_agent)
        
        self.assertIn("TestAgent", self.orchestrator.agents)
        self.assertEqual(self.orchestrator.agents["TestAgent"], mock_agent)

    def test_get_agent(self):
        """Test getting an agent by ID"""
        mock_agent = MockAgent("test_agent", "Test Agent")
        self.orchestrator.register_agent("TestAgent", mock_agent)
        
        retrieved_agent = self.orchestrator.get_agent("TestAgent")
        self.assertEqual(retrieved_agent, mock_agent)
        
        # Test getting non-existent agent
        non_existent = self.orchestrator.get_agent("NonExistent")
        self.assertIsNone(non_existent)

    def test_register_event_callback(self):
        """Test registering event callbacks"""
        callback = MagicMock()
        self.orchestrator.register_event_callback(callback)
        
        self.assertIn(callback, self.orchestrator.event_callbacks)
        self.assertEqual(len(self.orchestrator.event_callbacks), 1)

    def test_emit_event(self):
        """Test emitting events to registered callbacks"""
        callback = MagicMock()
        self.orchestrator.register_event_callback(callback)
        
        # Emit an event
        self.orchestrator._emit_event("test_event", {"data": "test"})
        
        # Verify callback was called
        self.assertEqual(callback.call_count, 1)
        call_args = callback.call_args[0][0]
        self.assertEqual(call_args["type"], "test_event")
        self.assertEqual(call_args["data"], {"data": "test"})

    def test_emit_event_with_exception(self):
        """Test that event emission continues despite callback exceptions"""
        def raising_callback(event):
            raise Exception("Test exception")
        
        callback = MagicMock(side_effect=raising_callback)
        self.orchestrator.register_event_callback(callback)
        
        # This should not raise an exception despite the callback failing
        try:
            self.orchestrator._emit_event("test_event", {"data": "test"})
        except Exception:
            self.fail("emit_event should not propagate callback exceptions")
        
        # Verify callback was still called
        self.assertEqual(callback.call_count, 1)

    def test_get_system_status(self):
        """Test getting system status"""
        status = self.orchestrator.get_system_status()
        
        self.assertIn("orchestrator_type", status)
        self.assertIn("agents", status)
        self.assertIn("tasks", status)
        self.assertIn("active_workflows", status)
        self.assertIn("timestamp", status)
        
        self.assertEqual(status["orchestrator_type"], "Central LangGraph Orchestrator")
        self.assertIsInstance(status["agents"], list)
        self.assertIsInstance(status["tasks"], dict)

    def test_request_clarification(self):
        """Test requesting clarification from user"""
        async def run_test():
            # Request clarification
            question = "Do you want to proceed?"
            task_id = "test_task_123"
            
            # This will create a future and emit an event
            response_task = asyncio.create_task(
                self.orchestrator.request_clarification(task_id, question)
            )
            
            # Verify the future was created
            self.assertIn(task_id, self.orchestrator.clarification_futures)
            
            # Resolve the future
            self.orchestrator.resolve_clarification(task_id, "Yes, proceed")
            
            # Get the response
            response = await response_task
            
            self.assertEqual(response, "Yes, proceed")
            self.assertNotIn(task_id, self.orchestrator.clarification_futures)
        
        asyncio.run(run_test())

    def test_resolve_clarification_nonexistent(self):
        """Test resolving clarification for non-existent task"""
        result = self.orchestrator.resolve_clarification("nonexistent", "response")
        self.assertFalse(result)

    def test_resolve_clarification_already_resolved(self):
        """Test resolving clarification that's already resolved"""
        async def run_test():
            task_id = "test_task_456"
            
            # Request clarification
            response_task = asyncio.create_task(
                self.orchestrator.request_clarification(task_id, "Question?")
            )
            
            # Resolve it once
            result1 = self.orchestrator.resolve_clarification(task_id, "First response")
            self.assertTrue(result1)
            
            # Try to resolve it again (should fail since it's already done)
            result2 = self.orchestrator.resolve_clarification(task_id, "Second response")
            self.assertFalse(result2)
            
            # Get the actual response (should be the first one)
            response = await response_task
            self.assertEqual(response, "First response")
        
        asyncio.run(run_test())

    def test_cancel_task_not_found(self):
        """Test cancelling a non-existent task"""
        async def run_test():
            result = await self.orchestrator.cancel_task("nonexistent_task")
            self.assertFalse(result)
        
        asyncio.run(run_test())

    def test_cancel_task_not_running(self):
        """Test cancelling a task that is not running"""
        # Create a completed task manually
        completed_task = Task(metadata={"query": "completed"})
        completed_task.status = "completed"
        self.task_manager.tasks[completed_task.id] = completed_task
        
        async def run_test():
            result = await self.orchestrator.cancel_task(completed_task.id)
            self.assertFalse(result)
        
        asyncio.run(run_test())


class TestCentralOrchestratorWithRealAgents(unittest.TestCase):
    def setUp(self):
        self.task_manager = TaskManager()
        self.orchestrator = CentralOrchestrator(self.task_manager)

    def test_default_agents_registered(self):
        """Test that default agents are properly registered"""
        # Check that all default agents are instances of BaseAgent
        for agent_id, agent in self.orchestrator.agents.items():
            if agent is not None:  # "General" agent is None initially
                self.assertIsInstance(agent, BaseAgent)
        
        # Check specific agents exist
        self.assertIsInstance(self.orchestrator.agents["Web"], WebSearchAgent)
        self.assertIsInstance(self.orchestrator.agents["Response"], ResponseGenerationAgent)
        self.assertIsInstance(self.orchestrator.agents["Code"], CodeInterpreterAgent)
        self.assertIsInstance(self.orchestrator.agents["System"], SystemAgentWrapper)
        self.assertIsInstance(self.orchestrator.agents["Search"], DeepSearchAgent)

    @unittest.skip("Skipping submit_task test as it requires external dependencies")
    def test_submit_task_basic(self):
        """Test submitting a basic task (requires external dependencies)"""
        async def run_test():
            task_data = {
                "query": "Test query",
                "id": "test_task_789"
            }
            
            result = await self.orchestrator.submit_task(task_data)
            
            # Result should contain task_id and either completed or failed status
            self.assertIn("task_id", result)
            self.assertIn("status", result)
            self.assertIn(result["status"], ["completed", "failed"])
        
        asyncio.run(run_test())


class TestCentralOrchestratorWorkflows(unittest.TestCase):
    def setUp(self):
        self.task_manager = TaskManager()
        self.orchestrator = CentralOrchestrator(self.task_manager)
        
        # Mock the LLM to avoid external dependencies
        self.original_get_llm = None

    def test_decompose_node(self):
        """Test the decomposition node functionality"""
        async def run_test():
            from agents.central_orchestrator import AgentWorkflowState
            
            # Create initial state
            initial_state = AgentWorkflowState({
                "original_input": "Search for weather in New York",
                "decomposed_tasks": [],
                "task_results": [],
                "assigned_agent": None,
                "processing_result": None,
                "workflow_status": "started",
                "errors": [],
                "execution_log": [],
                "auth_token": None,
                "base_url": None,
                "task_id": "test_task"
            })
            
            # Mock the LLM response to return a predictable JSON
            with patch('agents.central_orchestrator.ChatOpenAI') as mock_llm_class, \
                 patch('agents.central_orchestrator.LLMChain') as mock_chain_class:
                
                # Create a mock chain instance
                mock_chain = AsyncMock()
                mock_chain.ainvoke.return_value = '[{"task_description": "Search for weather", "agent": "Web"}]'
                
                mock_chain_class.return_value = mock_chain
                
                # Call the decompose node
                result_state = await self.orchestrator._decompose_node(initial_state)
                
                # Verify the state was updated
                self.assertEqual(len(result_state["decomposed_tasks"]), 1)
                self.assertEqual(result_state["decomposed_tasks"][0]["task_description"], "Search for weather")
                self.assertEqual(result_state["decomposed_tasks"][0]["agent"], "Web")
                self.assertIn("Decomposing query", result_state["execution_log"][0])
        
        asyncio.run(run_test())

    def test_synthesize_node(self):
        """Test the synthesis node functionality"""
        async def run_test():
            from agents.central_orchestrator import AgentWorkflowState
            
            # Create state with task results
            initial_state = AgentWorkflowState({
                "original_input": "What's the weather?",
                "decomposed_tasks": [{"task_description": "Search for weather", "agent": "Web"}],
                "task_results": [{"task": "Search for weather", "agent": "Web", "success": True, "result": "Weather is sunny"}],
                "assigned_agent": None,
                "processing_result": None,
                "workflow_status": "started",
                "errors": [],
                "execution_log": [],
                "auth_token": None,
                "base_url": None,
                "task_id": "test_task"
            })
            
            # Mock the LLM response
            with patch('agents.central_orchestrator.ChatOpenAI') as mock_llm_class, \
                 patch('agents.central_orchestrator.LLMChain') as mock_chain_class:
                
                mock_chain = AsyncMock()
                mock_chain.ainvoke.return_value = "The weather is sunny today."
                
                mock_chain_class.return_value = mock_chain
                
                # Call the synthesize node
                result_state = await self.orchestrator._synthesize_node(initial_state)
                
                # Verify the state was updated
                self.assertEqual(result_state["processing_result"], "The weather is sunny today.")
                self.assertEqual(result_state["workflow_status"], "processed")
                self.assertIn("Synthesizing final response", result_state["execution_log"])
        
        asyncio.run(run_test())

    def test_execute_tasks_node(self):
        """Test the execute tasks node functionality"""
        async def run_test():
            from agents.central_orchestrator import AgentWorkflowState
            
            # Create state with tasks to execute
            initial_state = AgentWorkflowState({
                "original_input": "Test execution",
                "decomposed_tasks": [{"task_description": "Test task", "agent": "Web"}],
                "task_results": [],
                "assigned_agent": None,
                "processing_result": None,
                "workflow_status": "started",
                "errors": [],
                "execution_log": [],
                "auth_token": None,
                "base_url": None,
                "task_id": "test_task"
            })
            
            # Mock a web agent to return a result
            mock_web_agent = MockAgent("web_mock", "Web Mock")
            mock_web_agent.process_task_result = AgentResponse(
                agent_id="web_mock",
                success=True,
                result="Mock web result"
            )
            
            # Replace the web agent temporarily
            original_web_agent = self.orchestrator.agents["Web"]
            self.orchestrator.agents["Web"] = mock_web_agent
            
            try:
                # Call the execute tasks node
                result_state = await self.orchestrator._execute_tasks_node(initial_state)
                
                # Verify the state was updated
                self.assertEqual(len(result_state["task_results"]), 1)
                result = result_state["task_results"][0]
                self.assertEqual(result["task"], "Test task")
                self.assertEqual(result["agent"], "Web Mock")
                self.assertTrue(result["success"])
                self.assertEqual(result["result"], "Mock web result")
                self.assertIn("All tasks executed", result_state["execution_log"])
            finally:
                # Restore original agent
                self.orchestrator.agents["Web"] = original_web_agent
        
        asyncio.run(run_test())

    def test_execute_tasks_node_failed_workflow(self):
        """Test execute tasks node when workflow is already failed"""
        async def run_test():
            from agents.central_orchestrator import AgentWorkflowState
            
            # Create state with failed workflow status
            initial_state = AgentWorkflowState({
                "original_input": "Test execution",
                "decomposed_tasks": [{"task_description": "Test task", "agent": "Web"}],
                "task_results": [],
                "assigned_agent": None,
                "processing_result": None,
                "workflow_status": "failed",  # Already failed
                "errors": ["Previous error"],
                "execution_log": [],
                "auth_token": None,
                "base_url": None,
                "task_id": "test_task"
            })
            
            # Call the execute tasks node - should return early
            result_state = await self.orchestrator._execute_tasks_node(initial_state)
            
            # State should be unchanged since workflow was already failed
            self.assertEqual(result_state["workflow_status"], "failed")
            self.assertEqual(result_state["task_results"], [])
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()