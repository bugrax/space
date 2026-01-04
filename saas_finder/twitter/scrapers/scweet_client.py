"""
Fallback scraper using Scweet (Selenium-based).
https://github.com/Altimis/Scweet

This is the slowest option but most reliable as it uses
actual browser automation.
"""

import asyncio
from typing import AsyncGenerator, Optional, List
from datetime import datetime, timedelta
import logging
import os
import tempfile

from .base import BaseScraper
from ..models import Tweet, TweetAuthor, TweetMedia, TweetMetrics

logger = logging.getLogger(__name__)


class ScweetClient(BaseScraper):
    """Fallback scraper using Scweet (Selenium-based)."""
    
    name = "scweet"
    
    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None
    ):
        """
        Initialize ScweetClient.
        
        Args:
            headless: Run browser in headless mode
            proxy: Optional proxy URL
        """
        self.headless = headless
        self.proxy = proxy
        self._initialized = False
        self._scweet_available = False
    
    async def initialize(self) -> bool:
        """Initialize Scweet."""
        try:
            # Check if scweet is available
            from Scweet.scweet import scrape
            self._scweet_available = True
            self._initialized = True
            logger.info("ScweetClient initialized")
            return True
            
        except ImportError:
            logger.error("scweet not installed. Run: pip install scweet")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize ScweetClient: {e}")
            return False
    
    async def search(
        self, 
        query: str, 
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> AsyncGenerator[Tweet, None]:
        """
        Search tweets using Scweet (Selenium).
        
        Note: Scweet is synchronous, so we run it in a thread pool.
        """
        if not self._initialized:
            if not await self.initialize():
                return
        
        # Set default date range if not provided
        if not since:
            since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not until:
            until = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Starting Scweet search: '{query}' from {since} to {until}")
        
        try:
            # Run scweet in a thread since it's synchronous
            loop = asyncio.get_event_loop()
            tweets = await loop.run_in_executor(
                None,
                lambda: self._run_scweet_search(query, limit, since, until)
            )
            
            for tweet in tweets[:limit]:
                yield tweet
                
        except Exception as e:
            logger.error(f"Scweet search error: {e}")
            raise
    
    def _run_scweet_search(
        self, 
        query: str, 
        limit: int,
        since: str,
        until: str
    ) -> List[Tweet]:
        """Run Scweet search synchronously."""
        try:
            from Scweet.scweet import scrape
            import pandas as pd
            
            # Create temp dir for output
            with tempfile.TemporaryDirectory() as tmpdir:
                # Run scrape
                df = scrape(
                    words=[query],
                    since=since,
                    until=until,
                    from_account=None,
                    interval=1,
                    headless=self.headless,
                    display_type="Latest",
                    save_images=False,
                    save_dir=tmpdir,
                    proxy=self.proxy,
                    filter_replies=False,
                    proximity=False
                )
                
                if df is None or df.empty:
                    logger.warning("Scweet returned no results")
                    return []
                
                tweets = []
                for _, row in df.iterrows():
                    tweet = self._parse_scweet_row(row)
                    if tweet:
                        tweets.append(tweet)
                        if len(tweets) >= limit:
                            break
                
                return tweets
                
        except Exception as e:
            logger.error(f"Scweet execution error: {e}")
            return []
    
    def _parse_scweet_row(self, row) -> Optional[Tweet]:
        """Parse Scweet DataFrame row to Tweet model."""
        try:
            # Extract username from UserScreenName
            username = str(row.get("UserScreenName", ""))
            if username.startswith("@"):
                username = username[1:]
            
            # Parse date
            timestamp = row.get("Timestamp", "")
            if timestamp:
                try:
                    # Scweet returns various date formats
                    if "T" in str(timestamp):
                        created_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                    else:
                        created_at = datetime.strptime(str(timestamp), "%Y-%m-%d %H:%M:%S")
                except:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            author = TweetAuthor(
                id=str(row.get("UserId", "")),
                username=username,
                name=str(row.get("UserName", username)),
                followers_count=0,  # Scweet doesn't always get this
                following_count=0,
                verified=False
            )
            
            # Parse engagement metrics
            likes = self._parse_count(row.get("Likes", 0))
            retweets = self._parse_count(row.get("Retweets", 0))
            replies = self._parse_count(row.get("Replies", 0))
            
            metrics = TweetMetrics(
                like_count=likes,
                retweet_count=retweets,
                reply_count=replies,
            )
            
            # Extract URLs from text
            text = str(row.get("Text", ""))
            import re
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
            
            # Extract hashtags
            hashtags = re.findall(r'#(\w+)', text)
            
            # Check for media
            media = []
            embedded_text = str(row.get("EmbeddedText", ""))
            if "pic.twitter.com" in text or "pbs.twimg.com" in embedded_text:
                media.append(TweetMedia(
                    type="photo",
                    url=""
                ))
            
            tweet = Tweet(
                id=str(row.get("TweetId", "")),
                text=text,
                created_at=created_at,
                author=author,
                metrics=metrics,
                media=media,
                urls=urls,
                hashtags=hashtags,
                source=self.name
            )
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error parsing Scweet row: {e}")
            return None
    
    def _parse_count(self, value) -> int:
        """Parse engagement count from various formats."""
        if pd.isna(value) if 'pd' in dir() else value is None:
            return 0
        
        try:
            value_str = str(value).strip().upper()
            
            # Handle K, M suffixes
            if value_str.endswith("K"):
                return int(float(value_str[:-1]) * 1000)
            elif value_str.endswith("M"):
                return int(float(value_str[:-1]) * 1000000)
            else:
                return int(float(value_str.replace(",", "")))
        except:
            return 0
    
    async def get_user_tweets(
        self, 
        username: str, 
        limit: int = 100
    ) -> AsyncGenerator[Tweet, None]:
        """Get tweets from a specific user using Scweet."""
        if not self._initialized:
            if not await self.initialize():
                return
        
        logger.info(f"Fetching tweets for @{username} via Scweet")
        
        # Default date range
        since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        
        try:
            loop = asyncio.get_event_loop()
            tweets = await loop.run_in_executor(
                None,
                lambda: self._run_scweet_user(username, limit, since, until)
            )
            
            for tweet in tweets[:limit]:
                yield tweet
                
        except Exception as e:
            logger.error(f"Error fetching user tweets via Scweet: {e}")
            raise
    
    def _run_scweet_user(
        self,
        username: str,
        limit: int,
        since: str,
        until: str
    ) -> List[Tweet]:
        """Run Scweet for user timeline."""
        try:
            from Scweet.scweet import scrape
            
            with tempfile.TemporaryDirectory() as tmpdir:
                df = scrape(
                    from_account=username,
                    since=since,
                    until=until,
                    interval=1,
                    headless=self.headless,
                    display_type="Latest",
                    save_images=False,
                    save_dir=tmpdir,
                    proxy=self.proxy
                )
                
                if df is None or df.empty:
                    return []
                
                tweets = []
                for _, row in df.iterrows():
                    tweet = self._parse_scweet_row(row)
                    if tweet:
                        tweets.append(tweet)
                        if len(tweets) >= limit:
                            break
                
                return tweets
                
        except Exception as e:
            logger.error(f"Scweet user fetch error: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if Scweet is available."""
        return self._initialized and self._scweet_available
    
    async def close(self) -> None:
        """Cleanup resources."""
        self._initialized = False
        logger.info("ScweetClient closed")
