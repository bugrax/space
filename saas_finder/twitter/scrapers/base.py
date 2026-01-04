"""
Abstract base class for all Twitter scrapers.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from ..models import Tweet


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    name: str = "base"
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the scraper (login, setup, etc.).
        
        Returns:
            bool: True if initialization was successful
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> AsyncGenerator[Tweet, None]:
        """
        Search tweets by query.
        
        Args:
            query: Search query (supports Twitter search operators)
            limit: Maximum number of tweets to return
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            
        Yields:
            Tweet: Parsed tweet objects
        """
        pass
    
    @abstractmethod
    async def get_user_tweets(
        self, 
        username: str, 
        limit: int = 100
    ) -> AsyncGenerator[Tweet, None]:
        """
        Get tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            limit: Maximum number of tweets to return
            
        Yields:
            Tweet: Parsed tweet objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if scraper is working.
        
        Returns:
            bool: True if scraper is healthy
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
