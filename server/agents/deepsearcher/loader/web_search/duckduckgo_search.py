import asyncio
from typing import List, Dict
from duckduckgo_search import DDGS
from .base import BaseWebSearch

class DuckDuckGoSearch(BaseWebSearch):
    """
    Web search implementation using DuckDuckGo.
    """
    
    def __init__(self, **kwargs):
        self.ddgs = DDGS()
        
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        results = []
        for r in self.ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
        return results
        
    async def async_search(self, query: str, max_results: int = 10) -> List[Dict]:
        # DDGS.text is sync, so we run it in a thread
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, query, max_results)
