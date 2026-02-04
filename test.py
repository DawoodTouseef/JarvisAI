# Default LLM configuration
DEFAULT_API_KEY = "sk-8b9514c137d742b48624ed6bb1b97087"
DEFAULT_BASE_URL = "http://localhost:8080"


from server.agents.orchestrator import CentralOrchestrator
import asyncio

async def main():
    orchestrator = CentralOrchestrator()
    r=await orchestrator.submit_task({"id": "1", "query": "open notepad and open a new page in the notpad and write a email to the HR  for asking leave from 24 feb to 28 feb 2026.",
    "base_url": DEFAULT_BASE_URL,
    "auth_token": DEFAULT_API_KEY
    })
    print(r['processing_result'])


if __name__ == "__main__":
    asyncio.run(main()) 