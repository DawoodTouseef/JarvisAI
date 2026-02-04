import aiohttp
import asyncio
from typing import List, Dict
from .base import BaseWebSearch
import requests

class SearXNGSearch(BaseWebSearch):
    """
    Web search implementation using SearXNG.
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", **kwargs):
        self.base_url = base_url.rstrip('/')
        
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "number_of_results": max_results
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for r in data.get("results", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")
            })
        return results
        
    async def async_search(self, query: str, max_results: int = 10) -> List[Dict]:
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "number_of_results": max_results
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                results = []
                for r in data.get("results", [])[:max_results]:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", "")
                    })
                return results
