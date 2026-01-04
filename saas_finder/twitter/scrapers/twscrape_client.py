"""
Primary scraper using twscrape library.
https://github.com/vladkens/twscrape

twscrape is a fast, reliable Twitter scraper that uses 
Twitter's internal GraphQL API.
"""

import asyncio
from typing import AsyncGenerator, Optional
from datetime import datetime
from contextlib import asynccontextmanager
import logging
import os

from .base import BaseScraper
from ..models import Tweet, TweetAuthor, TweetMedia, TweetMetrics

logger = logging.getLogger(__name__)


class TwscrapeClient(BaseScraper):
    """Primary scraper using twscrape library."""
    
    name = "twscrape"
    
    def __init__(
        self, 
        db_path: str = "accounts.db",
        accounts_file: str = "accounts.txt",
        rate_limit_delay: float = 2.0
    ):
        """
        Initialize TwscrapeClient.
        
        Args:
            db_path: Path to accounts database
            accounts_file: Path to accounts.txt file
            rate_limit_delay: Delay between requests in seconds
        """
        self.db_path = db_path
        self.accounts_file = accounts_file
        self.rate_limit_delay = rate_limit_delay
        self.api = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize twscrape API and load accounts."""
        try:
            # Import here to avoid import errors if not installed
            from twscrape import API
            
            self.api = API(self.db_path)
            
            # Load accounts from file if exists
            await self._load_accounts_from_file(self.accounts_file)
            
            # Login all accounts
            await self.api.pool.login_all()
            
            # Check if we have active accounts
            accounts = await self.api.pool.accounts_info()
            active_count = sum(1 for acc in accounts if acc.active)
            
            if active_count == 0:
                logger.warning("No active Twitter accounts found for twscrape")
                return False
            
            self._initialized = True
            logger.info(f"TwscrapeClient initialized with {active_count} active accounts")
            return True
            
        except ImportError:
            logger.error("twscrape not installed. Run: pip install twscrape")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize TwscrapeClient: {e}")
            return False
    
    async def _load_accounts_from_file(self, filepath: str) -> None:
        """
        Load Twitter accounts from file.
        
        Format: username:password:email:email_password
        Or with cookies: username:password:email:email_password:cookies_json
        """
        if not os.path.exists(filepath):
            logger.warning(f"Accounts file not found: {filepath}")
            return
            
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 4:
                        username, password, email, email_pass = parts[:4]
                        cookies = parts[4] if len(parts) > 4 else None
                        
                        try:
                            await self.api.pool.add_account(
                                username=username,
                                password=password,
                                email=email,
                                email_password=email_pass,
                                cookies=cookies
                            )
                            logger.info(f"Added account: {username}")
                        except Exception as e:
                            logger.warning(f"Failed to add account {username}: {e}")
                    else:
                        logger.warning(f"Invalid format at line {line_num}: need at least 4 parts")
                        
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
    
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
        """
        if not self._initialized:
            if not await self.initialize():
                logger.error("Failed to initialize twscrape")
                return
        
        # Build full query with date filters
        full_query = query
        if since:
            full_query += f" since:{since}"
        if until:
            full_query += f" until:{until}"
        
        logger.info(f"Searching tweets: '{full_query}' (limit: {limit})")
        
        count = 0
        try:
            async for tweet in self.api.search(full_query, limit=limit):
                if count >= limit:
                    break
                
                parsed_tweet = self._parse_tweet(tweet)
                if parsed_tweet:
                    yield parsed_tweet
                    count += 1
                
                # Rate limiting
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
                    
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise
        
        logger.info(f"Search completed. Found {count} tweets.")
    
    async def get_user_tweets(
        self, 
        username: str, 
        limit: int = 100
    ) -> AsyncGenerator[Tweet, None]:
        """Get tweets from a specific user."""
        if not self._initialized:
            if not await self.initialize():
                return
        
        logger.info(f"Fetching tweets for user: @{username}")
        
        try:
            # First get user ID
            user = await self.api.user_by_login(username)
            if not user:
                logger.warning(f"User not found: {username}")
                return
            
            count = 0
            async for tweet in self.api.user_tweets(user.id, limit=limit):
                if count >= limit:
                    break
                
                parsed_tweet = self._parse_tweet(tweet)
                if parsed_tweet:
                    yield parsed_tweet
                    count += 1
                
                if self.rate_limit_delay > 0:
                    await asyncio.sleep(self.rate_limit_delay)
                    
        except Exception as e:
            logger.error(f"Error fetching user tweets: {e}")
            raise
    
    def _parse_tweet(self, raw_tweet) -> Optional[Tweet]:
        """Parse twscrape tweet object to our Tweet model."""
        try:
            # Parse author
            author = TweetAuthor(
                id=str(raw_tweet.user.id),
                username=raw_tweet.user.username,
                name=raw_tweet.user.displayname,
                followers_count=raw_tweet.user.followersCount or 0,
                following_count=raw_tweet.user.friendsCount or 0,
                tweet_count=raw_tweet.user.statusesCount or 0,
                verified=raw_tweet.user.verified or getattr(raw_tweet.user, 'blueVerified', False),
                profile_image_url=raw_tweet.user.profileImageUrl,
                description=raw_tweet.user.rawDescription,
                location=raw_tweet.user.location,
                created_at=raw_tweet.user.created
            )
            
            # Parse media
            media = []
            if raw_tweet.media:
                for m in raw_tweet.media:
                    media_type = getattr(m, 'type', 'photo')
                    media_url = getattr(m, 'url', None) or str(m)
                    media.append(TweetMedia(
                        media_key=str(getattr(m, 'id', '')),
                        type=media_type,
                        url=media_url,
                        preview_image_url=getattr(m, 'previewUrl', None)
                    ))
            
            # Extract hashtags, mentions, urls from tweet
            hashtags = [h.text for h in (raw_tweet.hashtags or [])] if hasattr(raw_tweet, 'hashtags') else []
            mentions = [m.username for m in (raw_tweet.mentionedUsers or [])] if hasattr(raw_tweet, 'mentionedUsers') else []
            urls = [u.url for u in (raw_tweet.links or [])] if hasattr(raw_tweet, 'links') else []
            
            # Create metrics
            metrics = TweetMetrics(
                like_count=raw_tweet.likeCount or 0,
                retweet_count=raw_tweet.retweetCount or 0,
                reply_count=raw_tweet.replyCount or 0,
                quote_count=raw_tweet.quoteCount or 0,
                impression_count=raw_tweet.viewCount or 0
            )
            
            tweet = Tweet(
                id=str(raw_tweet.id),
                text=raw_tweet.rawContent,
                created_at=raw_tweet.date,
                author=author,
                metrics=metrics,
                media=media,
                urls=urls,
                hashtags=hashtags,
                mentioned_users=mentions,
                language=raw_tweet.lang,
                source=self.name
            )
            
            # Calculate engagement rate
            tweet.engagement_rate = tweet.calculate_engagement_rate()
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error parsing tweet: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check if scraper is working by doing a simple search."""
        try:
            if not self._initialized:
                return False
            
            # Try a simple search
            count = 0
            async for _ in self.search("test", limit=1):
                count += 1
                break
            
            return count > 0
            
        except Exception:
            return False
    
    async def close(self) -> None:
        """Cleanup resources."""
        self._initialized = False
        self.api = None
        logger.info("TwscrapeClient closed")
