"""
Twitter API client for fetching tweets.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import tweepy
from rich.console import Console

from ..config import config
from .models import Tweet, TweetAuthor, TweetMedia, TweetMetrics

console = Console()


class TwitterClient:
    """Client for interacting with Twitter API v2."""
    
    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize the Twitter client.
        
        Args:
            bearer_token: Twitter API bearer token. Uses config if not provided.
        """
        self.bearer_token = bearer_token or config.twitter.bearer_token
        
        if not self.bearer_token:
            raise ValueError(
                "Twitter bearer token not found. "
                "Set TWITTER_BEARER_TOKEN environment variable or pass it directly."
            )
        
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            wait_on_rate_limit=True
        )
        
        # Fields to request from Twitter API
        self.tweet_fields = [
            "id", "text", "created_at", "author_id",
            "public_metrics", "entities", "attachments",
            "conversation_id", "in_reply_to_user_id", "lang"
        ]
        
        self.user_fields = [
            "id", "name", "username", "description",
            "public_metrics", "verified", "profile_image_url"
        ]
        
        self.media_fields = [
            "media_key", "type", "url", "preview_image_url",
            "alt_text", "width", "height"
        ]
        
        self.expansions = [
            "author_id",
            "attachments.media_keys",
            "entities.mentions.username"
        ]
    
    def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> list[Tweet]:
        """
        Search for tweets matching a query.
        
        Args:
            query: Twitter search query (can include operators)
            max_results: Maximum number of tweets to return (max 100 per request)
            start_time: Start of time range (default: 7 days ago)
            end_time: End of time range (default: now)
        
        Returns:
            List of Tweet objects
        """
        # Default time range: last 7 days
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(days=7)
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                start_time=start_time,
                end_time=end_time,
                tweet_fields=self.tweet_fields,
                user_fields=self.user_fields,
                media_fields=self.media_fields,
                expansions=self.expansions
            )
            
            if not response.data:
                return []
            
            # Build lookup dictionaries for includes
            users_lookup = {}
            media_lookup = {}
            
            if response.includes:
                if "users" in response.includes:
                    users_lookup = {
                        user.id: user for user in response.includes["users"]
                    }
                if "media" in response.includes:
                    media_lookup = {
                        media.media_key: media for media in response.includes["media"]
                    }
            
            # Convert to our models
            tweets = []
            for tweet_data in response.data:
                tweet = self._parse_tweet(tweet_data, users_lookup, media_lookup)
                tweets.append(tweet)
            
            return tweets
            
        except tweepy.errors.TweepyException as e:
            console.print(f"[red]Twitter API error: {e}[/red]")
            return []
    
    def search_by_hashtags(
        self,
        hashtags: list[str],
        max_results: int = 100,
        days: int = 7,
        require_image: bool = False
    ) -> list[Tweet]:
        """
        Search tweets by hashtags.
        
        Args:
            hashtags: List of hashtags to search (without #)
            max_results: Maximum number of tweets to return
            days: Number of days to look back
            require_image: Only return tweets with images
        
        Returns:
            List of Tweet objects
        """
        # Build query with OR between hashtags
        hashtag_query = " OR ".join(f"#{tag}" for tag in hashtags)
        
        # Add filters
        query_parts = [f"({hashtag_query})"]
        
        # Exclude retweets for cleaner results
        query_parts.append("-is:retweet")
        
        # Only English tweets (optional, can be parameterized)
        query_parts.append("lang:en")
        
        # Require image attachment
        if require_image:
            query_parts.append("has:images")
        
        query = " ".join(query_parts)
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self.search_tweets(
            query=query,
            max_results=max_results,
            start_time=start_time
        )
    
    def search_by_keywords(
        self,
        keywords: list[str],
        max_results: int = 100,
        days: int = 7
    ) -> list[Tweet]:
        """
        Search tweets by keywords (for MRR/revenue mentions).
        
        Args:
            keywords: List of keywords to search
            max_results: Maximum number of tweets to return
            days: Number of days to look back
        
        Returns:
            List of Tweet objects
        """
        # Build query with OR between keywords
        keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
        
        # Add filters
        query_parts = [f"({keyword_query})"]
        query_parts.append("-is:retweet")
        query_parts.append("lang:en")
        
        query = " ".join(query_parts)
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self.search_tweets(
            query=query,
            max_results=max_results,
            start_time=start_time
        )
    
    def search_revenue_tweets(
        self,
        hashtags: Optional[list[str]] = None,
        min_mrr_mention: bool = True,
        require_image: bool = False,
        max_results: int = 100,
        days: int = 7
    ) -> list[Tweet]:
        """
        Search for tweets mentioning revenue/MRR with optional hashtag filter.
        
        Args:
            hashtags: Optional list of hashtags to filter by
            min_mrr_mention: Require tweet to mention MRR/ARR/revenue
            require_image: Only return tweets with images
            max_results: Maximum number of tweets to return
            days: Number of days to look back
        
        Returns:
            List of Tweet objects
        """
        query_parts = []
        
        # Hashtag filter
        if hashtags:
            hashtag_query = " OR ".join(f"#{tag}" for tag in hashtags)
            query_parts.append(f"({hashtag_query})")
        
        # Revenue-related keywords
        if min_mrr_mention:
            # Use $ with context to avoid random $ mentions
            revenue_query = '("MRR" OR "ARR" OR "revenue" OR "per month" OR "/month" OR "paying customers")'
            query_parts.append(revenue_query)
        
        # Standard filters
        query_parts.append("-is:retweet")
        query_parts.append("lang:en")
        
        if require_image:
            query_parts.append("has:images")
        
        query = " ".join(query_parts)
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self.search_tweets(
            query=query,
            max_results=max_results,
            start_time=start_time
        )
    
    def _parse_tweet(
        self,
        tweet_data,
        users_lookup: dict,
        media_lookup: dict
    ) -> Tweet:
        """
        Parse raw Twitter API response into our Tweet model.
        
        Args:
            tweet_data: Raw tweet data from API
            users_lookup: Dictionary of user_id -> user data
            media_lookup: Dictionary of media_key -> media data
        
        Returns:
            Tweet object
        """
        # Parse author
        author = None
        if tweet_data.author_id and tweet_data.author_id in users_lookup:
            user_data = users_lookup[tweet_data.author_id]
            author = TweetAuthor(
                id=str(user_data.id),
                username=user_data.username,
                name=user_data.name,
                followers_count=getattr(user_data, "public_metrics", {}).get("followers_count", 0) if hasattr(user_data, "public_metrics") else 0,
                following_count=getattr(user_data, "public_metrics", {}).get("following_count", 0) if hasattr(user_data, "public_metrics") else 0,
                tweet_count=getattr(user_data, "public_metrics", {}).get("tweet_count", 0) if hasattr(user_data, "public_metrics") else 0,
                verified=getattr(user_data, "verified", False),
                description=getattr(user_data, "description", None),
                profile_image_url=getattr(user_data, "profile_image_url", None)
            )
        
        # Parse metrics
        metrics = TweetMetrics()
        if hasattr(tweet_data, "public_metrics") and tweet_data.public_metrics:
            pm = tweet_data.public_metrics
            metrics = TweetMetrics(
                like_count=pm.get("like_count", 0),
                retweet_count=pm.get("retweet_count", 0),
                reply_count=pm.get("reply_count", 0),
                quote_count=pm.get("quote_count", 0),
                impression_count=pm.get("impression_count", 0),
                bookmark_count=pm.get("bookmark_count", 0)
            )
        
        # Parse media
        media_list = []
        if hasattr(tweet_data, "attachments") and tweet_data.attachments:
            media_keys = tweet_data.attachments.get("media_keys", [])
            for key in media_keys:
                if key in media_lookup:
                    m = media_lookup[key]
                    media_list.append(TweetMedia(
                        media_key=m.media_key,
                        type=m.type,
                        url=getattr(m, "url", None),
                        preview_image_url=getattr(m, "preview_image_url", None),
                        alt_text=getattr(m, "alt_text", None),
                        width=getattr(m, "width", None),
                        height=getattr(m, "height", None)
                    ))
        
        # Parse entities (URLs, hashtags, mentions)
        urls = []
        hashtags = []
        mentions = []
        
        if hasattr(tweet_data, "entities") and tweet_data.entities:
            entities = tweet_data.entities
            
            # URLs
            if "urls" in entities:
                for url_entity in entities["urls"]:
                    expanded_url = url_entity.get("expanded_url", url_entity.get("url", ""))
                    if expanded_url:
                        urls.append(expanded_url)
            
            # Hashtags
            if "hashtags" in entities:
                for ht in entities["hashtags"]:
                    hashtags.append(ht.get("tag", ""))
            
            # Mentions
            if "mentions" in entities:
                for mention in entities["mentions"]:
                    mentions.append(mention.get("username", ""))
        
        return Tweet(
            id=str(tweet_data.id),
            text=tweet_data.text,
            created_at=tweet_data.created_at,
            author=author,
            metrics=metrics,
            media=media_list,
            urls=urls,
            hashtags=hashtags,
            mentioned_users=mentions,
            language=getattr(tweet_data, "lang", None),
            conversation_id=str(tweet_data.conversation_id) if hasattr(tweet_data, "conversation_id") and tweet_data.conversation_id else None,
            in_reply_to_user_id=str(tweet_data.in_reply_to_user_id) if hasattr(tweet_data, "in_reply_to_user_id") and tweet_data.in_reply_to_user_id else None
        )


class MockTwitterClient:
    """
    Mock Twitter client for testing without API credentials.
    Returns sample data that mimics real Twitter responses.
    """
    
    def __init__(self, bearer_token: Optional[str] = None):  # noqa: ARG002
        """Initialize mock client."""
    
    def search_tweets(self, *_args, **_kwargs) -> list[Tweet]:
        """Return sample tweets."""
        return self._get_sample_tweets()
    
    def search_by_hashtags(self, *_args, **_kwargs) -> list[Tweet]:
        """Return sample tweets."""
        return self._get_sample_tweets()
    
    def search_by_keywords(self, *_args, **_kwargs) -> list[Tweet]:
        """Return sample tweets."""
        return self._get_sample_tweets()
    
    def search_revenue_tweets(self, *_args, **_kwargs) -> list[Tweet]:
        """Return sample tweets."""
        return self._get_sample_tweets()
    
    def _get_sample_tweets(self) -> list[Tweet]:
        """Generate sample tweets for testing."""
        return [
            Tweet(
                id="1234567890",
                text="🚀 Just hit $10,000 MRR with my SaaS! Building in public really works. Check it out: https://example-saas.com #buildinpublic #indiehackers",
                created_at=datetime.now(timezone.utc) - timedelta(hours=5),
                author=TweetAuthor(
                    id="user123",
                    username="indiehacker1",
                    name="Indie Hacker",
                    followers_count=12500,
                    verified=False
                ),
                metrics=TweetMetrics(
                    like_count=245,
                    retweet_count=42,
                    reply_count=18,
                    impression_count=15000
                ),
                media=[TweetMedia(media_key="img1", type="photo", url="https://example.com/stripe-screenshot.png")],
                urls=["https://example-saas.com"],
                hashtags=["buildinpublic", "indiehackers"]
            ),
            Tweet(
                id="1234567891",
                text="Month 6 of my side project: $5K/month revenue, 200 paying customers. The journey from $0 to here was tough but worth it! https://another-tool.io #saas #mrr",
                created_at=datetime.now(timezone.utc) - timedelta(days=2),
                author=TweetAuthor(
                    id="user456",
                    username="saasentrepreneur",
                    name="SaaS Builder",
                    followers_count=8200,
                    verified=False
                ),
                metrics=TweetMetrics(
                    like_count=189,
                    retweet_count=31,
                    reply_count=24,
                    impression_count=12000
                ),
                media=[],
                urls=["https://another-tool.io"],
                hashtags=["saas", "mrr"]
            ),
            Tweet(
                id="1234567892",
                text="Crossed $20K ARR with my AI writing tool! 🎉 Mostly organic traffic from SEO. Happy to share what worked! https://ai-writer-pro.com #buildinpublic #solopreneur",
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
                author=TweetAuthor(
                    id="user789",
                    username="aibuilder",
                    name="AI Entrepreneur",
                    followers_count=25000,
                    verified=True
                ),
                metrics=TweetMetrics(
                    like_count=567,
                    retweet_count=89,
                    reply_count=45,
                    impression_count=45000
                ),
                media=[TweetMedia(media_key="img2", type="photo", url="https://example.com/revenue-chart.png")],
                urls=["https://ai-writer-pro.com"],
                hashtags=["buildinpublic", "solopreneur"]
            )
        ]


def get_twitter_client(use_mock: bool = False, use_nitter: bool = True) -> TwitterClient | MockTwitterClient:
    """
    Factory function to get appropriate Twitter client.
    
    Args:
        use_mock: If True, return mock client for testing
        use_nitter: If True, use Nitter scraper instead of Twitter API (default)
    
    Returns:
        Twitter client instance
    """
    if use_mock:
        return MockTwitterClient()
    
    if use_nitter:
        from .nitter_scraper import NitterClient
        return NitterClient()
    
    if not config.twitter.bearer_token:
        console.print("[yellow]No Twitter API token, using Nitter scraper[/yellow]")
        from .nitter_scraper import NitterClient
        return NitterClient()
    
    return TwitterClient()
