"""
Backup scraper using Apify's Twitter scraper actor.
https://apify.com/apidojo/tweet-scraper

This is a paid service but highly reliable.
Falls back to this when twscrape fails.
"""

import asyncio
from typing import AsyncGenerator, Optional
from datetime import datetime
import logging

from .base import BaseScraper
from ..models import Tweet, TweetAuthor, TweetMedia, TweetMetrics

logger = logging.getLogger(__name__)


class ApifyTwitterClient(BaseScraper):
    """Backup scraper using Apify's Twitter scraper."""
    
    name = "apify"
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        actor_id: str = "apidojo/tweet-scraper"
    ):
        """
        Initialize ApifyTwitterClient.
        
        Args:
            api_token: Apify API token (can also be set via APIFY_API_TOKEN env var)
            actor_id: Apify actor ID to use for scraping
        """
        import os
        self.api_token = api_token or os.environ.get("APIFY_API_TOKEN")
        self.actor_id = actor_id
        self.client = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Apify client."""
        try:
            if not self.api_token:
                logger.warning("APIFY_API_TOKEN not set, Apify scraper unavailable")
                return False
            
            # Import here to avoid import errors if not installed
            from apify_client import ApifyClient
            
            self.client = ApifyClient(self.api_token)
            self._initialized = True
            logger.info("ApifyTwitterClient initialized")
            return True
            
        except ImportError:
            logger.error("apify-client not installed. Run: pip install apify-client")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize ApifyTwitterClient: {e}")
            return False
    
    async def search(
        self, 
        query: str, 
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> AsyncGenerator[Tweet, None]:
        """Search tweets using Apify."""
        if not self._initialized:
            if not await self.initialize():
                return
        
        if not self.client:
            logger.error("Apify client not initialized")
            return
        
        # Prepare input for Apify actor
        # Note: apidojo/tweet-scraper ignores maxTweets and fetches all available tweets
        # We limit results client-side
        run_input = {
            "searchTerms": [query],
            "maxTweets": min(limit, 500),  # Actor may ignore this but we try
            "sort": "Latest",
        }
        
        if since:
            run_input["startDate"] = since
        if until:
            run_input["endDate"] = until
        
        logger.info(f"Starting Apify search: '{query}' (limit: {limit})")
        
        try:
            # Run the actor with timeout
            # Actor tends to over-fetch, so we use a reasonable timeout
            timeout_secs = max(60, limit // 10 * 5)  # ~5 seconds per 10 tweets, min 60s
            
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.client.actor(self.actor_id).call(
                    run_input=run_input,
                    timeout_secs=timeout_secs
                )
            )
            
            # Get results with client-side limit
            count = 0
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                if count >= limit:
                    break
                tweet = self._parse_apify_tweet(item)
                if tweet:
                    count += 1
                    yield tweet
                    
        except Exception as e:
            logger.error(f"Apify search error: {e}")
            raise
    
    def _parse_apify_tweet(self, item: dict) -> Optional[Tweet]:
        """Parse Apify result to Tweet model."""
        try:
            # Skip non-tweet items or empty results
            if item.get("noResults") or item.get("type") not in ("tweet", None):
                return None
                
            author_data = item.get("author", {})
            
            author = TweetAuthor(
                id=str(author_data.get("id", "")),
                username=author_data.get("userName", "") or author_data.get("username", ""),
                name=author_data.get("name", "") or author_data.get("displayname", ""),
                followers_count=author_data.get("followers", 0) or author_data.get("followersCount", 0),
                following_count=author_data.get("following", 0) or author_data.get("friendsCount", 0),
                verified=author_data.get("isBlueVerified", False) or author_data.get("isVerified", False),
                profile_image_url=author_data.get("profilePicture"),
            )
            
            # Parse media
            media = []
            for m in item.get("media", []):
                media.append(TweetMedia(
                    type=m.get("type", "photo"),
                    url=m.get("url", "") or m.get("media_url_https", ""),
                ))
            
            # Parse dates - apidojo format: "Sun Jan 04 14:55:22 +0000 2026"
            created_at_str = item.get("createdAt", "")
            if created_at_str:
                try:
                    # Try Twitter's format first
                    created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                except ValueError:
                    try:
                        # Try ISO format
                        if created_at_str.endswith("Z"):
                            created_at_str = created_at_str.replace("Z", "+00:00")
                        created_at = datetime.fromisoformat(created_at_str)
                    except ValueError:
                        created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            # Extract hashtags from entities
            entities = item.get("entities", {})
            hashtags_data = entities.get("hashtags", [])
            hashtags = [h.get("text", "") for h in hashtags_data if isinstance(h, dict)]
            
            # Extract URLs from entities
            urls_data = entities.get("urls", [])
            urls = []
            for u in urls_data:
                if isinstance(u, dict):
                    urls.append(u.get("expanded_url") or u.get("url", ""))
                else:
                    urls.append(str(u))
            
            # Also check author description for URLs
            author_entities = author_data.get("entities", {})
            desc_urls = author_entities.get("description", {}).get("urls", [])
            for u in desc_urls:
                if isinstance(u, dict):
                    expanded = u.get("expanded_url") or u.get("url", "")
                    if expanded and expanded not in urls:
                        urls.append(expanded)
            
            metrics = TweetMetrics(
                like_count=item.get("likeCount", 0),
                retweet_count=item.get("retweetCount", 0),
                reply_count=item.get("replyCount", 0),
                quote_count=item.get("quoteCount", 0),
                impression_count=item.get("viewCount", 0) or 0
            )
            
            tweet = Tweet(
                id=str(item.get("id", "")),
                text=item.get("fullText", "") or item.get("text", ""),
                created_at=created_at,
                author=author,
                metrics=metrics,
                media=media,
                urls=urls,
                hashtags=hashtags,
                language=item.get("lang"),
                source=self.name,
                conversation_id=item.get("conversationId"),
                is_reply=item.get("isReply", False),
                is_retweet=item.get("isRetweet", False),
                is_quote=item.get("isQuote", False),
            )
            
            tweet.engagement_rate = tweet.calculate_engagement_rate()
            return tweet
            
        except Exception as e:
            logger.error(f"Error parsing Apify tweet: {e}")
            return None
    
    async def get_user_tweets(
        self, 
        username: str, 
        limit: int = 100
    ) -> AsyncGenerator[Tweet, None]:
        """Get user tweets via Apify."""
        if not self._initialized:
            if not await self.initialize():
                return
        
        if not self.client:
            return
        
        run_input = {
            "twitterHandles": [username],
            "maxTweets": limit,
        }
        
        logger.info(f"Fetching tweets for @{username} via Apify")
        
        try:
            loop = asyncio.get_event_loop()
            run = await loop.run_in_executor(
                None,
                lambda: self.client.actor(self.actor_id).call(run_input=run_input)
            )
            
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                tweet = self._parse_apify_tweet(item)
                if tweet:
                    yield tweet
                    
        except Exception as e:
            logger.error(f"Error fetching user tweets via Apify: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if Apify is available."""
        return self._initialized and self.client is not None
    
    async def close(self) -> None:
        """Cleanup resources."""
        self.client = None
        self._initialized = False
        logger.info("ApifyTwitterClient closed")
