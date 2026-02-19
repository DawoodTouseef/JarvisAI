import asyncio
import os
import sys
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.orchestrator_session import OrchestratorSession
from server.agents.base_agent import JobType, AgentStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeepResearchVerification")

async def mock_send(message):
    logger.info(f"[WS SEND] {message.get('type')} - {message.get('task_id')}")

async def run_verification():
    session = OrchestratorSession(session_id="test_session", websocket_send_callback=mock_send)
    
    # Mock orchestrator.submit_task to simulate slow research
    async def mock_submit_task(task_data):
        job_type = task_data.get("job_type", JobType.CHAT)
        task_id = task_data["id"]
        logger.info(f"[ORCH SUBMIT] {job_type} - {task_id}")
        
        if job_type == JobType.RESEARCH:
            await asyncio.sleep(3) # Slow research
            return {"workflow_status": "completed", "processing_result": "Deep research result concluded."}
        else:
            await asyncio.sleep(0.5) # Fast chat
            return {"workflow_status": "completed", "processing_result": f"Answer to {task_data['query']}"}

    session.orchestrator.submit_task = mock_submit_task
    
    # 1. Start Deep Research
    logger.info("--- Step 1: Starting Deep Research ---")
    research_query = "Please research the history of AI."
    research_task_id = await session.handle_user_query(research_query, "token", "url")
    
    # Verify research job created
    research_job_id = f"job_{research_task_id}"
    if research_job_id in session.active_jobs and session.active_jobs[research_job_id].type == JobType.RESEARCH:
        logger.info(f"PASS: Research job {research_job_id} initiated.")
    else:
        logger.error("FAIL: Research job not initiated correctly.")

    await asyncio.sleep(0.5)

    # 2. Ask multiple chat questions while research is running
    logger.info("--- Step 2: Asking CHAT questions in parallel ---")
    chat_queries = ["What is 2+2?", "Tell me a joke.", "What time is it?"]
    chat_task_ids = []
    
    for q in chat_queries:
        logger.info(f"Asking: {q}")
        t_id = await session.handle_user_query(q, "token", "url")
        chat_task_ids.append(t_id)
        await asyncio.sleep(0.2) # Small gap between queries

    # 3. Wait for chat questions to finish (they should finish BEFORE research)
    logger.info("--- Step 3: Waiting for CHAT responses ---")
    await asyncio.sleep(1.5)
    
    # 4. Final wait for research
    logger.info("--- Step 4: Waiting for RESEARCH response ---")
    await asyncio.sleep(2)
    
    # 5. Verify all jobs finished
    logger.info("--- Phase 5: Verification ---")
    for job in session.active_jobs.values():
        logger.info(f"Job {job.id} ({job.type}): Status={job.status}")
        
    is_success = all(j.status == AgentStatus.COMPLETED for j in session.active_jobs.values())
    if is_success:
        logger.info("FINAL RESULT: PASS - Parallel research and chat worked correctly.")
    else:
        logger.error("FINAL RESULT: FAIL - Some jobs did not complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
