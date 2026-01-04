"""
Scraper Manager - Orchestrates multiple scrapers with automatic fallback.

Priority order:
1. twscrape (primary) - Fast, free, uses Twitter's internal API
2. apify (backup) - Paid service, very reliable
3. scweet (fallback) - Selenium-based, slowest but most reliable
"""

import asyncio
from typing import AsyncGenerator, Optional, List, Set
import logging

from .base import BaseScraper
from .twscrape_client import TwscrapeClient
from .apify_client import ApifyTwitterClient
from .scweet_client import ScweetClient
from ..models import Tweet

logger = logging.getLogger(__name__)


class ScraperManager:
    """
    Manages multiple scrapers with automatic fallback.
    
    Priority: twscrape -> apify -> scweet
    
    Usage:
        manager = ScraperManager()
        await manager.initialize()
        
        async for tweet in manager.search("#buildinpublic MRR"):
            print(tweet.text)
    """
    
    def __init__(
        self,
        accounts_file: str = "accounts.txt",
        apify_token: Optional[str] = None,
        enable_scweet: bool = True,
        rate_limit_delay: float = 2.0
    ):
        """
        Initialize ScraperManager.
        
        Args:
            accounts_file: Path to Twitter accounts file for twscrape
            apify_token: Apify API token (optional)
            enable_scweet: Whether to enable Selenium fallback
            rate_limit_delay: Delay between requests
        """
        self.accounts_file = accounts_file
        self.apify_token = apify_token
        self.enable_scweet = enable_scweet
        self.rate_limit_delay = rate_limit_delay
        
        self.scrapers: List[BaseScraper] = []
        self.active_scraper: Optional[BaseScraper] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize scrapers in priority order.
        
        Returns:
            bool: True if at least one scraper was initialized
        """
        logger.info("Initializing ScraperManager...")
        
        # Priority order of scrapers
        scrapers_to_try = [
            ("twscrape", lambda: TwscrapeClient(
                accounts_file=self.accounts_file,
                rate_limit_delay=self.rate_limit_delay
            )),
            ("apify", lambda: ApifyTwitterClient(
                api_token=self.apify_token
            )),
        ]
        
        # Only add Scweet if enabled
        if self.enable_scweet:
            scrapers_to_try.append(
                ("scweet", lambda: ScweetClient(headless=True))
            )
        
        for name, create_scraper in scrapers_to_try:
            try:
                scraper = create_scraper()
                if await scraper.initialize():
                    self.scrapers.append(scraper)
                    logger.info(f"✓ Initialized scraper: {name}")
                else:
                    logger.warning(f"✗ Failed to initialize: {name}")
            except Exception as e:
                logger.warning(f"✗ Error initializing {name}: {e}")
        
        if self.scrapers:
            self.active_scraper = self.scrapers[0]
            self._initialized = True
            logger.info(f"Active scraper: {self.active_scraper.name}")
            logger.info(f"Total available scrapers: {len(self.scrapers)}")
            return True
        
        logger.error("No scrapers could be initialized!")
        return False
    
    async def search(
        self, 
        query: str, 
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> AsyncGenerator[Tweet, None]:
        """
        Search with automatic fallback on failure.
        
        Tries each scraper in order until one succeeds.
        
        Args:
            query: Search query
            limit: Maximum tweets to return
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            
        Yields:
            Tweet: Matching tweets
        """
        if not self._initialized:
            if not await self.initialize():
                logger.error("Failed to initialize any scraper")
                return
        
        last_error = None
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Trying scraper: {scraper.name}")
                tweet_count = 0
                
                async for tweet in scraper.search(
                    query, 
                    limit=limit, 
                    since=since, 
                    until=until
                ):
                    yield tweet
                    tweet_count += 1
                
                # Success - update active scraper
                self.active_scraper = scraper
                logger.info(f"Search completed with {scraper.name}: {tweet_count} tweets")
                return
                
            except Exception as e:
                logger.warning(f"Scraper {scraper.name} failed: {e}")
                last_error = e
                continue
        
        # All scrapers failed
        logger.error(f"All scrapers failed! Last error: {last_error}")
        if last_error:
            raise last_error
    
    async def search_multiple_queries(
        self, 
        queries: List[str], 
        limit_per_query: int = 50,
        deduplicate: bool = True
    ) -> AsyncGenerator[Tweet, None]:
        """
        Search multiple queries and yield unique tweets.
        
        Args:
            queries: List of search queries
            limit_per_query: Max tweets per query
            deduplicate: Remove duplicate tweets across queries
            
        Yields:
            Tweet: Unique tweets matching any query
        """
        seen_ids: Set[str] = set()
        total_found = 0
        
        for query in queries:
            logger.info(f"Searching query: '{query}'")
            query_count = 0
            
            try:
                async for tweet in self.search(query, limit=limit_per_query):
                    if deduplicate:
                        if tweet.id not in seen_ids:
                            seen_ids.add(tweet.id)
                            yield tweet
                            query_count += 1
                            total_found += 1
                    else:
                        yield tweet
                        query_count += 1
                        total_found += 1
                        
                logger.info(f"Query '{query[:30]}...': {query_count} unique tweets")
                        
            except Exception as e:
                logger.error(f"Error searching '{query}': {e}")
                continue
        
        logger.info(f"Total unique tweets found: {total_found}")
    
    async def get_user_tweets(
        self,
        username: str,
        limit: int = 100
    ) -> AsyncGenerator[Tweet, None]:
        """
        Get tweets from a specific user with fallback.
        
        Args:
            username: Twitter username (without @)
            limit: Maximum tweets to return
            
        Yields:
            Tweet: User's tweets
        """
        if not self._initialized:
            if not await self.initialize():
                return
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Fetching @{username} tweets with {scraper.name}")
                
                async for tweet in scraper.get_user_tweets(username, limit=limit):
                    yield tweet
                
                self.active_scraper = scraper
                return
                
            except Exception as e:
                logger.warning(f"Scraper {scraper.name} failed for user tweets: {e}")
                continue
        
        logger.error("All scrapers failed to get user tweets")
    
    async def get_status(self) -> dict:
        """
        Get status of all scrapers.
        
        Returns:
            dict: Status information including active scraper and health
        """
        status = {
            "active_scraper": self.active_scraper.name if self.active_scraper else None,
            "initialized": self._initialized,
            "scrapers": []
        }
        
        for scraper in self.scrapers:
            try:
                health = await scraper.health_check()
            except:
                health = False
                
            status["scrapers"].append({
                "name": scraper.name,
                "healthy": health,
                "active": scraper == self.active_scraper
            })
        
        return status
    
    async def close(self) -> None:
        """Close all scrapers and cleanup resources."""
        logger.info("Closing ScraperManager...")
        
        for scraper in self.scrapers:
            try:
                await scraper.close()
            except Exception as e:
                logger.warning(f"Error closing {scraper.name}: {e}")
        
        self.scrapers = []
        self.active_scraper = None
        self._initialized = False
        logger.info("ScraperManager closed")
    
    def __repr__(self) -> str:
        active = self.active_scraper.name if self.active_scraper else "None"
        count = len(self.scrapers)
        return f"<ScraperManager active={active} scrapers={count}>"


# Convenience function for simple usage
async def create_scraper_manager(
    accounts_file: str = "accounts.txt",
    apify_token: Optional[str] = None
) -> ScraperManager:
    """
    Create and initialize a ScraperManager.
    
    Example:
        manager = await create_scraper_manager()
        async for tweet in manager.search("#buildinpublic"):
            print(tweet.text)
    """
    manager = ScraperManager(
        accounts_file=accounts_file,
        apify_token=apify_token
    )
    await manager.initialize()
    return manager
