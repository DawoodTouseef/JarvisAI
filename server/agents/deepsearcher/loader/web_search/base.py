from abc import ABC, abstractmethod
from typing import List, Dict

class BaseWebSearch(ABC):
    """
    Abstract base class for web search engines.
    """
    
    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search the web for the given query.
        
        Args:
            query: The search query.
            max_results: Maximum number of results to return.
            
        Returns:
            A list of dictionaries, each containing 'title', 'url', and 'snippet'.
        """
        pass
        
    @abstractmethod
    async def async_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Asynchronously search the web for the given query.
        """
        pass
