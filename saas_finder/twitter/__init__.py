"""
Twitter module for data collection.

Supports multiple scraping methods with automatic fallback:
1. twscrape (primary) - Fast, uses Twitter's internal GraphQL API
2. Apify (backup) - Paid service, very reliable
3. Scweet (fallback) - Selenium-based, slowest but most reliable

Legacy support:
- Nitter scraper
- Official Twitter API
"""

from .client import TwitterClient, MockTwitterClient, get_twitter_client
from .nitter_scraper import NitterClient, NitterScraper
from .models import (
    Tweet, 
    TweetAuthor, 
    TweetMedia, 
    TweetMetrics,
    SaaSIdea,
    ExtractedRevenue,
    ExtractedProduct,
    RevenueType
)
from .scrapers import (
    BaseScraper,
    TwscrapeClient,
    ApifyTwitterClient,
    ScweetClient,
    ScraperManager
)

__all__ = [
    # Legacy clients
    "TwitterClient", 
    "MockTwitterClient",
    "NitterClient",
    "NitterScraper",
    "get_twitter_client",
    
    # Models
    "Tweet", 
    "TweetAuthor", 
    "TweetMedia",
    "TweetMetrics",
    "SaaSIdea",
    "ExtractedRevenue",
    "ExtractedProduct",
    "RevenueType",
    
    # New scrapers
    "BaseScraper",
    "TwscrapeClient",
    "ApifyTwitterClient",
    "ScweetClient",
    "ScraperManager",
]
