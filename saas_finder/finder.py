"""
Main SaaS Idea Finder - Orchestrates all components.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import re

from .twitter.client import get_twitter_client, MockTwitterClient
from .twitter.nitter_scraper import NitterClient
from .twitter.scrapers.scraper_manager import ScraperManager
from .parsers.mrr import MRRParser
from .parsers.url import URLExtractor
from .extractors.revenue import RevenueExtractor
from .extractors.urls import URLExtractor as ProductURLExtractor
from .scoring.scorer import IdeaScorer, SaaSIdea


class SaaSIdeaFinder:
    """Main class to find and analyze SaaS ideas from Twitter."""
    
    def __init__(self, use_mock: bool = False, use_nitter: bool = False, use_apify: bool = True):
        """
        Initialize the finder.
        
        Args:
            use_mock: If True, use mock Twitter client for testing
            use_nitter: If True, use Nitter scraper (deprecated, most instances down)
            use_apify: If True, use Apify scraper (recommended, requires paid plan)
        """
        self.use_apify = use_apify
        self.scraper_manager = None
        
        if use_mock:
            self.twitter = MockTwitterClient()
        elif use_nitter:
            self.twitter = NitterClient()
        else:
            self.twitter = get_twitter_client(use_mock=False, use_nitter=False)
        
        self.mrr_parser = MRRParser()
        self.url_extractor = URLExtractor()
        self.revenue_extractor = RevenueExtractor()
        self.product_url_extractor = ProductURLExtractor()
        self.scorer = IdeaScorer()
    
    async def _get_scraper(self) -> ScraperManager:
        """Get or initialize the scraper manager."""
        if self.scraper_manager is None:
            self.scraper_manager = ScraperManager()
            await self.scraper_manager.initialize()
        return self.scraper_manager
    
    async def search_async(
        self,
        query: Optional[str] = None,
        hashtags: Optional[list[str]] = None,
        days: int = 7,
        max_results: int = 100,
        min_mrr: float = 0
    ) -> list[SaaSIdea]:
        """
        Async search Twitter for SaaS ideas using Apify.
        
        Args:
            query: Direct search query
            hashtags: List of hashtags to search
            days: Number of days to look back
            max_results: Maximum tweets to fetch
            min_mrr: Minimum MRR to include (0 = all)
        
        Returns:
            List of scored SaaS ideas
        """
        ideas = []
        scraper = await self._get_scraper()
        
        # Build search query
        if hashtags:
            search_query = ' OR '.join(f'#{tag}' for tag in hashtags)
        else:
            search_query = query or '#buildinpublic MRR'
        
        # Calculate date range
        since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Search tweets
        async for tweet in scraper.search(search_query, limit=max_results, since=since_date):
            idea = self._process_tweet(tweet)
            if idea:
                if min_mrr > 0 and (idea.reported_mrr or 0) < min_mrr:
                    continue
                ideas.append(idea)
        
        # Sort by score
        ideas.sort(key=lambda x: self._get_total_score(x), reverse=True)
        
        return ideas
    
    def search(
        self,
        query: Optional[str] = None,
        hashtags: Optional[list[str]] = None,
        days: int = 7,
        max_results: int = 100,
        min_mrr: float = 0
    ) -> list[SaaSIdea]:
        """
        Search Twitter for SaaS ideas.
        
        Args:
            query: Direct search query
            hashtags: List of hashtags to search
            days: Number of days to look back
            max_results: Maximum tweets to fetch
            min_mrr: Minimum MRR to include (0 = all)
        
        Returns:
            List of scored SaaS ideas
        """
        # Use async version if apify is enabled
        if self.use_apify:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.search_async(query, hashtags, days, max_results, min_mrr)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.search_async(query, hashtags, days, max_results, min_mrr)
                )
        
        # Legacy search using old Twitter client
        ideas = []
        
        # Determine search method
        if hashtags:
            tweets = self.twitter.search_by_hashtags(
                hashtags=hashtags,
                days=days,
                max_results=max_results
            )
        else:
            tweets = self.twitter.search_revenue_tweets(
                query=query,
                days=days,
                max_results=max_results
            )
        
        # Process each tweet
        for tweet in tweets:
            idea = self._process_tweet(tweet)
            if idea:
                # Filter by minimum MRR if specified
                if min_mrr > 0 and (idea.reported_mrr or 0) < min_mrr:
                    continue
                ideas.append(idea)
        
        # Sort by score
        ideas.sort(key=lambda x: self._get_total_score(x), reverse=True)
        
        return ideas
    
    def _process_tweet(self, tweet) -> Optional[SaaSIdea]:
        """Process a single tweet into a SaaSIdea."""
        try:
            # Handle Tweet model from scrapers
            if hasattr(tweet, 'text'):
                text = tweet.text
                tweet_id = tweet.id
                author_username = tweet.author.username if tweet.author else 'unknown'
                author_followers = tweet.author.followers_count if tweet.author else 0
                likes = tweet.metrics.like_count if tweet.metrics else 0
                retweets = tweet.metrics.retweet_count if tweet.metrics else 0
                replies = tweet.metrics.reply_count if tweet.metrics else 0
                impressions = tweet.metrics.impression_count if tweet.metrics else 0
                tweet_urls = tweet.urls or []
                author_bio = tweet.author.description if tweet.author else None
            else:
                # It's a dict (legacy format)
                text = tweet.get('text', '') or tweet.get('fullText', '')
                tweet_id = tweet.get('id', '')
                author = tweet.get('author', {})
                author_username = author.get('username', author.get('userName', 'unknown'))
                author_followers = author.get('followers_count', author.get('followers', 0))
                metrics = tweet.get('public_metrics', {})
                likes = metrics.get('like_count', tweet.get('likeCount', 0))
                retweets = metrics.get('retweet_count', tweet.get('retweetCount', 0))
                replies = metrics.get('reply_count', tweet.get('replyCount', 0))
                impressions = metrics.get('impression_count', tweet.get('viewCount', 0))
                tweet_urls = []
                author_bio = author.get('description')
            
            # Extract revenue using new extractor
            revenue = self.revenue_extractor.extract(text)
            
            # Also try legacy parser for compatibility
            if not revenue:
                mrr_results = self.mrr_parser.parse(text)
                mrr_data = mrr_results[0] if mrr_results else None
                reported_mrr = mrr_data.amount if mrr_data else None
            else:
                reported_mrr = revenue.normalized_monthly_usd or revenue.amount
            
            # Extract product URL
            product_url = None
            product_domain = None
            
            # Try URLs from tweet first
            for url in tweet_urls:
                product = self.product_url_extractor.extract_product_url(url)
                if product:
                    product_url = product
                    product_domain = self.product_url_extractor.extract_domain(url)
                    break
            
            # Fall back to text extraction
            if not product_url:
                product_url_obj = self.url_extractor.get_best_product_url(text)
                if product_url_obj:
                    product_url = product_url_obj.url
                    product_domain = product_url_obj.domain
            
            # Determine product name
            product_name = self._extract_product_name(text, product_domain)
            
            # Build engagement data
            engagement = {
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
            }
            total_engagement = likes + retweets + replies
            engagement['rate'] = f"{(total_engagement / max(author_followers, 1) * 100):.2f}%"
            
            # Create SaaSIdea
            # mrr_data is a RevenueData dataclass with .amount attribute
            reported_mrr = mrr_data.amount if mrr_data else None
            
            idea = SaaSIdea(
                tweet_id=str(tweet_id),
                tweet_text=text,
                tweet_url=f"https://twitter.com/{author_username}/status/{tweet_id}",
                author_username=author_username,
                author_followers=author_followers,
                tweet_date=datetime.now(),
                likes=likes,
                retweets=retweets,
                replies=replies,
                impressions=impressions,
                product_name=product_name,
                product_url=product_url,
                product_domain=product_domain,
                reported_mrr=reported_mrr,
                date_found=datetime.now()
            )
            
            # Score the idea - store full ScoringResult object for database
            scoring_result = self.scorer.score_idea(idea)
            idea.score = scoring_result  # Database expects ScoringResult object
            
            return idea
            
        except Exception as e:
            print(f"Error processing tweet: {e}")
            return None
    
    def _extract_product_name(self, text: str, domain: Optional[str]) -> str:
        """Extract product name from tweet text or domain."""
        # Try to extract from domain
        if domain:
            # Remove common TLDs and clean
            name = domain.split('.')[0]
            return name.title()
        
        # Look for common patterns
        import re
        
        # Pattern: "Building X" or "launched X"
        patterns = [
            r'building\s+(\w+)',
            r'launched?\s+(\w+)',
            r'created?\s+(\w+)',
            r'(\w+)\s+saas',
            r'my\s+(\w+)\s+app',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).title()
        
        return "Unknown Product"
    
    def _get_total_score(self, idea: SaaSIdea) -> int:
        """Calculate total score from score components."""
        if idea.score is None:
            return 0
        
        # Handle ScoringResult object (has total_score attribute)
        if hasattr(idea.score, 'total_score'):
            return idea.score.total_score
        
        # Handle dict
        if isinstance(idea.score, dict):
            return (
                idea.score.get('traction', 0) +
                idea.score.get('growth', 0) +
                idea.score.get('traffic', 0) +
                idea.score.get('simplicity', 0)
            )
        
        # Handle int
        if isinstance(idea.score, int):
            return idea.score
        
        return 0
