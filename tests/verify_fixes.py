import asyncio
import os
import sys
import logging

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.agents.orchestrator import CentralOrchestrator, OrchestratorState
from server.agents.base_agent import BaseAgent, Task, AgentResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

class SlowAgent(BaseAgent):
    def __init__(self, name="SlowAgent"):
        super().__init__(name=name, description="An agent that takes time to process")
        self.process_count = 0

    async def process_task(self, task: Task) -> AgentResponse:
        self.process_count += 1
        logger.info(f"[{self.name}] Starting task {task.metadata.get('query')}")
        try:
            await asyncio.sleep(2)
            logger.info(f"[{self.name}] Finished task {task.metadata.get('query')}")
            return AgentResponse(success=True, result=f"Done with {task.metadata.get('query')}")
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] Task {task.metadata.get('query')} was CANCELLED internally")
            raise

    def can_handle_task(self, task: Task) -> bool:
        return True

async def verify_agent_accumulation():
    logger.info("--- Verifying Agent Accumulation Fix ---")
    orchestrator = CentralOrchestrator()
    initial_agent_count = len(orchestrator.agents)
    
    task_data = {"id": "test_1", "query": "test", "auth_token": "mock", "base_url": "mock"}
    
    # We need to mock workflow.ainvoke to avoid actual LLM calls
    async def mock_ainvoke(*args, **kwargs):
        return {"workflow_status": "completed", "processing_result": "done"}
    
    orchestrator.workflow.ainvoke = mock_ainvoke
    
    await orchestrator.submit_task(task_data)
    
    # Check if global agents list grew
    current_agent_count = len(orchestrator.agents)
    logger.info(f"Initial agents: {initial_agent_count}, Current agents: {current_agent_count}")
    
    if current_agent_count == initial_agent_count:
        logger.info("PASS: Agents did not accumulate in global list.")
    else:
        logger.error("FAIL: Agents accumulated in global list.")

async def verify_concurrency_and_cancellation():
    logger.info("--- Verifying Concurrency and Cancellation ---")
    orchestrator = CentralOrchestrator()
    orchestrator.concurrency_semaphore = asyncio.Semaphore(2) # Limit to 2 for test
    
    slow_agent = SlowAgent()
    orchestrator.agents.append(slow_agent)
    
    # Mock workflow to just run the slow agent if it encounters it
    # Since we can't easily mock the whole langgraph without complexity, 
    # we'll test the cancel_task and active_tasks management directly.
    
    async def mock_workflow_run(state, config):
        logger.info(f"Workflow started for {state['task_id']}")
        # Simulate agent execution
        task = Task(metadata={"query": state["original_input"]})
        await slow_agent.process_task(task)
        return {"workflow_status": "completed"}

    orchestrator.workflow.ainvoke = mock_workflow_run
    
    # Start task 1
    t1_data = {"id": "task_1", "query": "long_task_1", "auth_token": "m", "base_url": "b"}
    logger.info("Submitting task 1...")
    task1_coro = orchestrator.submit_task(t1_data)
    fut1 = asyncio.ensure_future(task1_coro)
    
    await asyncio.sleep(0.5)
    logger.info(f"Active tasks: {list(orchestrator.active_tasks.keys())}")
    
    # Verify task 1 is in active_tasks
    if "task_1" in orchestrator.active_tasks:
        logger.info("PASS: Task 1 is tracked in active_tasks.")
    else:
        logger.error("FAIL: Task 1 is NOT tracked.")

    # Cancel task 1
    logger.info("Cancelling task 1...")
    await orchestrator.cancel_task("task_1")
    
    await asyncio.sleep(0.5)
    
    if "task_1" not in orchestrator.active_tasks:
        logger.info("PASS: Task 1 removed from active_tasks after cancel.")
    else:
        logger.error("FAIL: Task 1 still in active_tasks.")
        
    try:
        res = await fut1
        if res["workflow_status"] == "cancelled":
            logger.info("PASS: Workflow returned cancelled status.")
        else:
            logger.info(f"Workflow returned status: {res['workflow_status']}")
    except Exception as e:
        logger.error(f"Workflow raised exception: {e}")

async def main():
    try:
        await verify_agent_accumulation()
        await verify_concurrency_and_cancellation()
    except Exception as e:
        logger.exception(f"Verification failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
