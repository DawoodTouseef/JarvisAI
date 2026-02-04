from .llm_client import llm_client
from typing import Dict, Any

class IntentRouter:
    def __init__(self):
        self.llm = llm_client

    async def route(self, query: str) -> Dict[str, Any]:
        """
        Analyze the query and return the classification result.
        """
        classification = await self.llm.classify_intent(query)
        print(f"Intent classified: {classification.get('intent')} for query: '{query}'")
        return classification

intent_router = IntentRouter()
