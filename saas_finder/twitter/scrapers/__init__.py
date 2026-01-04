"""
Twitter scrapers with automatic fallback.
Priority: twscrape -> apify -> scweet
"""

from .base import BaseScraper
from .twscrape_client import TwscrapeClient
from .apify_client import ApifyTwitterClient
from .scweet_client import ScweetClient
from .scraper_manager import ScraperManager

__all__ = [
    "BaseScraper",
    "TwscrapeClient",
    "ApifyTwitterClient",
    "ScweetClient",
    "ScraperManager",
]
