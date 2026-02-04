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

# Now safe to import other modules
import unittest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.agents.task_manager import TaskManager
from server.agents.base_agent import Task, AgentStatus


class TestTaskManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing database
        self.test_db_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(db_path=self.test_db_dir)

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_db_dir)

    def test_initialization(self):
        """Test TaskManager initialization"""
        self.assertEqual(len(self.task_manager.tasks), 0)
        self.assertEqual(len(self.task_manager.running_tasks), 0)
        self.assertEqual(self.task_manager.max_tasks, 50)

    def test_create_task_basic(self):
        """Test creating a basic task"""
        metadata = {"query": "test query"}
        
        # Mock orchestrator callback
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        import asyncio
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Verify task was created
            self.assertIsNotNone(task.id)
            self.assertEqual(task.status, AgentStatus.RUNNING)
            self.assertIsNotNone(task.created_at)
            self.assertIsNotNone(task.started_at)
            self.assertIsNone(task.completed_at)
            self.assertEqual(task.metadata, {"query": "test query", "id": task.id})
            
            # Verify task is tracked
            self.assertIn(task.id, self.task_manager.tasks)
            self.assertIn(task.id, self.task_manager.running_tasks)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_get_task(self):
        """Test getting a task by ID"""
        metadata = {"query": "test query"}
        
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            task = self.task_manager.create_task(metadata, sync_mock_callback)
            retrieved_task = self.task_manager.get_task(task.id)
            
            self.assertEqual(task.id, retrieved_task.id)
            self.assertEqual(task.metadata, retrieved_task.metadata)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_get_nonexistent_task(self):
        """Test getting a task that doesn't exist"""
        task = self.task_manager.get_task("nonexistent_id")
        self.assertIsNone(task)

    def test_get_tasks_by_status(self):
        """Test getting tasks by status"""
        # Create tasks with different statuses
        metadata = {"query": "test query"}
        
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Create a running task
            running_task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Create a completed task manually
            completed_task = Task(metadata={"query": "completed"})
            completed_task.status = AgentStatus.COMPLETED
            self.task_manager.tasks[completed_task.id] = completed_task
            
            # Get tasks by status
            running_tasks = self.task_manager.get_tasks_by_status("running")
            completed_tasks = self.task_manager.get_tasks_by_status("completed")
            
            self.assertIn(running_task, running_tasks)
            self.assertIn(completed_task, completed_tasks)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_update_task_status(self):
        """Test updating task status"""
        metadata = {"query": "test query"}
        
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Update status to completed
            result = self.task_manager.update_task_status(
                task.id, 
                "completed", 
                result="test result", 
                error=None
            )
            
            self.assertTrue(result)
            updated_task = self.task_manager.get_task(task.id)
            self.assertEqual(updated_task.status, AgentStatus.COMPLETED)
            self.assertEqual(updated_task.result, "test result")
            self.assertIsNone(updated_task.error)
            self.assertIsNotNone(updated_task.completed_at)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_stop_task(self):
        """Test stopping a running task"""
        # Create a task manually and add it to tasks
        task = Task(metadata={"query": "test query"})
        self.task_manager.tasks[task.id] = task
        
        # Create a mock asyncio task
        mock_asyncio_task = MagicMock()
        mock_asyncio_task.cancel = MagicMock()
        
        # Add to running tasks
        self.task_manager.running_tasks[task.id] = mock_asyncio_task
        
        # Update task status to running
        task.status = AgentStatus.RUNNING
        
        # Stop the task
        result = self.task_manager.stop_task(task.id)
        
        self.assertTrue(result)
        updated_task = self.task_manager.get_task(task.id)
        self.assertEqual(updated_task.status, "cancelled")
        self.assertEqual(updated_task.error, "Task stopped by user")
        self.assertNotIn(task.id, self.task_manager.running_tasks)
        # Verify the mock asyncio task was cancelled
        mock_asyncio_task.cancel.assert_called_once()

    def test_is_task_completed(self):
        """Test checking if a task is completed"""
        # Create a completed task
        completed_task = Task(metadata={"query": "completed"})
        completed_task.status = AgentStatus.COMPLETED
        self.task_manager.tasks[completed_task.id] = completed_task
        
        # Create a running task
        metadata = {"query": "test query"}
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            running_task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Test completed task
            self.assertTrue(self.task_manager.is_task_completed(completed_task.id))
            
            # Test running task
            self.assertFalse(self.task_manager.is_task_completed(running_task.id))
            
            # Test nonexistent task
            self.assertFalse(self.task_manager.is_task_completed("nonexistent"))
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_task_statistics(self):
        """Test getting task statistics"""
        # Create tasks with different statuses
        metadata = {"query": "test query"}
        
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Create a running task
            self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Create a completed task manually
            completed_task = Task(metadata={"query": "completed"})
            completed_task.status = AgentStatus.COMPLETED
            self.task_manager.tasks[completed_task.id] = completed_task
            
            # Create a failed task manually
            failed_task = Task(metadata={"query": "failed"})
            failed_task.status = AgentStatus.FAILED
            self.task_manager.tasks[failed_task.id] = failed_task
            
            # Get statistics
            stats = self.task_manager.get_task_statistics()
            
            self.assertGreaterEqual(stats["total"], 3)
            self.assertGreaterEqual(stats["running"], 1)
            self.assertGreaterEqual(stats["completed"], 1)
            self.assertGreaterEqual(stats["failed"], 1)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()

    def test_max_tasks_limit(self):
        """Test that max tasks limit is enforced"""
        # Temporarily reduce max tasks for testing
        original_max = self.task_manager.max_tasks
        self.task_manager.max_tasks = 1
        
        metadata = {"query": "test query"}
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            # Create first task
            first_task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Try to create second task - should raise exception
            with self.assertRaises(Exception) as context:
                self.task_manager.create_task(metadata, sync_mock_callback)
            
            self.assertIn("Maximum number of concurrent tasks reached", str(context.exception))
            
            # Restore original max
            self.task_manager.max_tasks = original_max
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called()

    def test_register_and_trigger_callbacks(self):
        """Test registering and triggering task callbacks"""
        metadata = {"query": "test query"}
        
        def sync_mock_callback(data):
            return {"result": "test result"}
        
        # Patch the async part for testing
        from unittest.mock import patch
        
        with patch('asyncio.create_task') as mock_create_task:
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task
            
            task = self.task_manager.create_task(metadata, sync_mock_callback)
            
            # Register a callback
            callback_mock = MagicMock()
            self.task_manager.register_callback(task.id, callback_mock)
            
            # Update task status to trigger callback
            self.task_manager.update_task_status(task.id, "completed", result="test result")
            
            # Verify callback was called
            self.assertEqual(callback_mock.call_count, 1)
            called_task = callback_mock.call_args[0][0]
            self.assertEqual(called_task.id, task.id)
            
            # Verify asyncio.create_task was called
            mock_create_task.assert_called_once()


class TestTaskManagerAsync(unittest.TestCase):
    def setUp(self):
        self.test_db_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(db_path=self.test_db_dir)

    def tearDown(self):
        shutil.rmtree(self.test_db_dir)

    async def async_test_create_task_completion(self):
        """Test task completion flow with async callback"""
        completed_results = []
        
        async def mock_callback(data):
            await asyncio.sleep(0.01)  # Small delay to simulate async work
            return {"result": "completed successfully"}
        
        task = self.task_manager.create_task({"query": "test"}, mock_callback)
        
        # Wait a bit for the task to complete
        await asyncio.sleep(0.1)
        
        # Check that the task is completed
        updated_task = self.task_manager.get_task(task.id)
        self.assertEqual(updated_task.status, AgentStatus.COMPLETED)
        self.assertEqual(updated_task.result, {"result": "completed successfully"})
        self.assertNotIn(task.id, self.task_manager.running_tasks)

    def test_create_task_completion(self):
        """Test task completion flow"""
        async def run_test():
            await self.async_test_create_task_completion()
        asyncio.run(run_test())

    async def async_test_create_task_failure(self):
        """Test task failure flow with async callback"""
        
        async def failing_callback(data):
            await asyncio.sleep(0.01)  # Small delay
            raise Exception("Test error")
        
        task = self.task_manager.create_task({"query": "test"}, failing_callback)
        
        # Wait a bit for the task to fail
        await asyncio.sleep(0.1)
        
        # Check that the task is marked as failed
        updated_task = self.task_manager.get_task(task.id)
        self.assertEqual(updated_task.status, AgentStatus.FAILED)
        self.assertIn("Test error", updated_task.error)
        self.assertNotIn(task.id, self.task_manager.running_tasks)

    def test_create_task_failure(self):
        """Test task failure flow"""
        async def run_test():
            await self.async_test_create_task_failure()
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()