from agents.orchestrator import CentralOrchestrator
from agents.base_agent import Task


async def main():
    c= CentralOrchestrator()
    task = Task(
        metadata={
            "query":"",
            "auth_token":"",
            "base_url":""},
        id="1"
    )