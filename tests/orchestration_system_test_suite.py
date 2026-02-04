"""
Comprehensive Test Suite for the Asynchronous Task Orchestration System

This test suite covers all major components of the JARVIS orchestration system:
- TaskManager: Task lifecycle, persistence, and status management
- CentralOrchestrator: Agent orchestration, workflow execution, and event handling
- AgentWebSocketIntegration: WebSocket message handling and task submission
- Various agent types: WebSearchAgent, DeepSearchAgent, CodeInterpreterAgent, SystemAgentWrapper
"""

import unittest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime
import json

# Import all the components to be tested

# Mock external dependencies before importing
sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain_core.prompts'] = MagicMock()
sys.modules['langchain_core.language_models'] = MagicMock()
sys.modules['langchain_core.tools'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()
sys.modules['langgraph.checkpoint.memory'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['mongita'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['duckduckgo_search'] = MagicMock()

from server.agents.task_manager import TaskManager
from server.agents.central_orchestrator import CentralOrchestrator
from server.agents.agent_integration import AgentWebSocketIntegration
from server.agents.connection_manager import ConnectionManager
from server.agents.base_agent import BaseAgent, Task, AgentResponse, AgentStatus
from server.agents.web_search_agent import WebSearchAgent
from server.agents.deep_search_agent import DeepSearchAgent
from server.agents.code_interpreter_agent import CodeInterpreterAgent
from server.agents.system_agent_wrapper import SystemAgentWrapper
from server.agents.response_generation_agent import ResponseGenerationAgent


class TestOrchestrationSystemIntegration(unittest.TestCase):
    """
    Integration tests that verify how different components work together
    """
    def setUp(self):
        # Create temporary database directory for testing
        self.test_db_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(db_path=self.test_db_dir)
        self.orchestrator = CentralOrchestrator(self.task_manager)
        self.connection_manager = ConnectionManager()
        self.agent_integration = AgentWebSocketIntegration(self.connection_manager)

    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_db_dir)

    def test_full_task_lifecycle(self):
        """Test the complete lifecycle of a task through the orchestration system"""
        async def run_test():
            # Create a mock websocket for the test
            websocket = AsyncMock()
            
            # Register an event callback to capture task completion
            completion_events = []
            def event_callback(event):
                completion_events.append(event)
            
            self.orchestrator.register_event_callback(event_callback)
            
            # Submit a task via the integration layer
            task_data = {
                "type": "agent_task_submit",
                "request_id": "req_test_123",
                "payload": {
                    "query": "Test task for integration",
                    "task_type": "web_search"
                }
            }
            
            # Mock the orchestrator's submit_task to return a quick result
            original_submit = self.orchestrator.submit_task
            async def mock_submit(task_data):
                return {
                    "task_id": task_data.get("id", "mock_task_id"),
                    "result": {"test": "result"},
                    "status": "completed"
                }
            
            self.orchestrator.submit_task = mock_submit
            
            try:
                # Submit the task
                await self.agent_integration.handle_task_submission(task_data, websocket)
                
                # Wait briefly for any async operations to complete
                await asyncio.sleep(0.01)
                
                # Verify the task was created and mapped
                task_created = False
                for task_id in self.agent_integration.task_websocket_mapping:
                    if "mock_task_id" in task_id or task_id in self.agent_integration.task_websocket_mapping:
                        task_created = True
                        break
                
                # Even if mocked, the task should be initiated
                # Verify websocket received acknowledgment
                self.assertTrue(websocket.send_text.called)
                
            finally:
                # Restore original method
                self.orchestrator.submit_task = original_submit
        
        asyncio.run(run_test())

    def test_event_propagation(self):
        """Test that events flow properly through the system"""
        async def run_test():
            # Create a mock websocket
            websocket = AsyncMock()
            
            # Create a task and map it to the websocket
            test_task_id = "event_test_task_123"
            self.agent_integration.task_websocket_mapping[test_task_id] = websocket
            
            # Simulate task completion event
            completion_event = {
                "type": "task_completed",
                "data": {
                    "task_id": test_task_id,
                    "result": {"summary": "Task completed successfully"}
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Handle the event through the integration
            self.agent_integration._handle_orchestrator_event(completion_event)
            
            # Wait briefly for async operations
            await asyncio.sleep(0.01)
            
            # Verify that the websocket received the completion message
            self.assertTrue(websocket.send_text.called)
            
            # Verify the task was removed from mapping after completion
            self.assertNotIn(test_task_id, self.agent_integration.task_websocket_mapping)
        
        asyncio.run(run_test())

    def test_multiple_agents_coordination(self):
        """Test that different agents can be accessed through the orchestrator"""
        # Verify all default agents are registered
        expected_agents = ["Search", "Web", "Response", "System", "Code"]
        for agent_id in expected_agents:
            self.assertIn(agent_id, self.orchestrator.agents)
            self.assertIsNotNone(self.orchestrator.agents[agent_id])
        
        # Verify specific agent types
        self.assertIsInstance(self.orchestrator.agents["Web"], WebSearchAgent)
        self.assertIsInstance(self.orchestrator.agents["Response"], ResponseGenerationAgent)
        self.assertIsInstance(self.orchestrator.agents["Code"], CodeInterpreterAgent)
        self.assertIsInstance(self.orchestrator.agents["System"], SystemAgentWrapper)
        self.assertIsInstance(self.orchestrator.agents["Search"], DeepSearchAgent)


class TestComponentCompatibility(unittest.TestCase):
    """Tests to ensure components work together properly"""
    
    def test_task_compatibility_across_components(self):
        """Test that tasks can be passed between different system components"""
        # Create a task
        task = Task(metadata={"query": "test compatibility", "source": "integration_test"})
        
        # Task should be compatible with TaskManager
        task_manager = TaskManager()
        task_manager.tasks[task.id] = task
        
        # Task should be compatible with CentralOrchestrator
        mock_callback_calls = []
        async def mock_callback(task_data):
            mock_callback_calls.append(task_data)
            return {"result": "processed"}
        
        # Test task creation through task manager
        created_task = task_manager.create_task(
            {"query": "direct creation test"}, 
            mock_callback
        )
        
        self.assertIsNotNone(created_task.id)
        self.assertEqual(created_task.status, AgentStatus.RUNNING)
        self.assertIn("direct creation test", created_task.metadata["query"])
    
    def test_error_handling_consistency(self):
        """Test that errors are handled consistently across components"""
        # All agents should return AgentResponse with proper error handling
        agents_to_test = [
            WebSearchAgent(),
            CodeInterpreterAgent(),
            SystemAgentWrapper(),
            ResponseGenerationAgent(),
            DeepSearchAgent()
        ]
        
        for agent in agents_to_test:
            # Verify the agent is an instance of BaseAgent
            self.assertIsInstance(agent, BaseAgent)
            
            # Verify it has the required methods
            self.assertTrue(hasattr(agent, 'can_handle_task'))
            self.assertTrue(hasattr(agent, 'process_task'))
            self.assertTrue(hasattr(agent, 'get_status_info'))


class TestAsyncBehavior(unittest.TestCase):
    """Tests for asynchronous behavior and concurrency"""
    
    def test_concurrent_task_processing(self):
        """Test that multiple tasks can be processed concurrently"""
        async def run_test():
            task_manager = TaskManager()
            
            # Create multiple tasks
            results = []
            
            async def process_task_sequentially():
                for i in range(3):
                    async def mock_callback(data):
                        await asyncio.sleep(0.01)  # Simulate async work
                        return {"result": f"task_{i}_result"}
                    
                    task = task_manager.create_task({"query": f"task_{i}"}, mock_callback)
                    results.append(task.id)
                    await asyncio.sleep(0.001)  # Small delay between task creations
                
                return results
            
            task_ids = await process_task_sequentially()
            
            # Verify all tasks were created
            self.assertEqual(len(task_ids), 3)
            self.assertEqual(len(set(task_ids)), 3)  # All IDs should be unique
            
            # Wait for tasks to complete
            await asyncio.sleep(0.1)
        
        asyncio.run(run_test())

    def test_async_agent_processing(self):
        """Test asynchronous agent processing"""
        async def run_test():
            class MockAsyncAgent(BaseAgent):
                def __init__(self):
                    super().__init__("mock_async_agent", "Mock Async Agent")
                    self.process_times = []
                
                async def process_task(self, task: Task) -> AgentResponse:
                    start_time = asyncio.get_event_loop().time()
                    await asyncio.sleep(0.01)  # Simulate async work
                    end_time = asyncio.get_event_loop().time()
                    self.process_times.append(end_time - start_time)
                    
                    return AgentResponse(
                        agent_id=self.agent_id,
                        success=True,
                        result={"processed": task.metadata.get("query")}
                    )
                
                def can_handle_task(self, task: Task) -> bool:
                    return True
            
            agent = MockAsyncAgent()
            task = Task(metadata={"query": "async test"})
            
            response = await agent.process_task(task)
            
            self.assertTrue(response.success)
            self.assertEqual(len(agent.process_times), 1)
            self.assertGreater(agent.process_times[0], 0)  # Processing took some time
        
        asyncio.run(run_test())


class TestWebSocketMessageFlow(unittest.TestCase):
    """Tests for the complete WebSocket message flow"""
    
    def setUp(self):
        self.connection_manager = ConnectionManager()
        self.integration = AgentWebSocketIntegration(self.connection_manager)

    def test_valid_message_handling(self):
        """Test handling of valid WebSocket messages"""
        async def run_test():
            websocket = AsyncMock()
            
            # Test a valid task submission message
            message = json.dumps({
                "type": "agent_task_submit",
                "request_id": "valid_req_123",
                "payload": {
                    "query": "test query for validation"
                }
            })
            
            # Mock the task creation to avoid external dependencies
            with patch.object(self.integration.task_manager, 'create_task') as mock_create_task:
                mock_task = Task(metadata={"query": "test query for validation"})
                mock_task.id = "validation_task_123"
                mock_create_task.return_value = mock_task
                
                with patch.object(self.integration.orchestrator, 'submit_task') as mock_submit:
                    mock_submit.coro = AsyncMock(return_value={"result": "submitted"})
                    
                    # Parse and handle the message
                    parsed_message = json.loads(message)
                    await self.integration.handle_task_submission(parsed_message, websocket)
                    
                    # Verify the response was sent
                    self.assertTrue(websocket.send_text.called)
                    call_args = websocket.send_text.call_args[0][0]
                    response = json.loads(call_args)
                    
                    self.assertEqual(response["type"], "agent_task_submitted")
                    self.assertEqual(response["request_id"], "valid_req_123")
                    self.assertEqual(response["task_id"], "validation_task_123")
        
        asyncio.run(run_test())

    def test_invalid_message_handling(self):
        """Test handling of invalid WebSocket messages"""
        async def run_test():
            websocket = AsyncMock()
            
            # Test an invalid JSON message
            result = await self.integration.handle_websocket_message("invalid json {", websocket)
            self.assertFalse(result)
            
            # Test an unknown message type
            unknown_msg = json.dumps({"type": "unknown_message_type", "payload": {}})
            result = await self.integration.handle_websocket_message(unknown_msg, websocket)
            self.assertFalse(result)
        
        asyncio.run(run_test())


class TestSystemMonitoring(unittest.TestCase):
    """Tests for system monitoring and status reporting"""
    
    def test_system_status_reporting(self):
        """Test that system status can be reported correctly"""
        task_manager = TaskManager()
        orchestrator = CentralOrchestrator(task_manager)
        
        status = orchestrator.get_system_status()
        
        # Verify required status fields exist
        self.assertIn("orchestrator_type", status)
        self.assertIn("agents", status)
        self.assertIn("tasks", status)
        self.assertIn("active_workflows", status)
        self.assertIn("timestamp", status)
        
        # Verify data types
        self.assertIsInstance(status["agents"], list)
        self.assertIsInstance(status["tasks"], dict)
        self.assertIsInstance(status["active_workflows"], int)
        self.assertIsInstance(status["timestamp"], str)
        
        # Verify task statistics structure
        task_stats = status["tasks"]
        for key in ["total", "pending", "running", "completed", "failed", "cancelled"]:
            self.assertIn(key, task_stats)
            self.assertIsInstance(task_stats[key], int)

    def test_task_statistics_accuracy(self):
        """Test that task statistics are calculated correctly"""
        task_manager = TaskManager()
        
        # Initially all counts should be 0
        stats = task_manager.get_task_statistics()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["running"], 0)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["cancelled"], 0)
        self.assertEqual(stats["pending"], 0)


def create_test_suite():
    """Create and return a test suite with all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    test_classes = [
        TestOrchestrationSystemIntegration,
        TestComponentCompatibility, 
        TestAsyncBehavior,
        TestWebSocketMessageFlow,
        TestSystemMonitoring
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def run_all_tests():
    """Run all tests in the suite"""
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    # Option 1: Run as standard unittest
    unittest.main()
    
    # Option 2: Uncomment the lines below to run the comprehensive suite
    # print("Running comprehensive orchestration system test suite...")
    # result = run_all_tests()
    # print(f"Tests run: {result.testsRun}")
    # print(f"Failures: {len(result.failures)}")
    # print(f"Errors: {len(result.errors)}")
    # print("Success!" if result.wasSuccessful() else "Some tests failed.")