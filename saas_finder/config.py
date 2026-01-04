"""
Configuration management for the SaaS Idea Finder.
"""

import os
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ScraperConfig:
    """Twitter scraper configuration."""
    # Accounts file for twscrape (now in config/ folder)
    accounts_file: str = field(default_factory=lambda: os.getenv("TWITTER_ACCOUNTS_FILE", "config/accounts.txt"))
    
    # Apify configuration (backup scraper)
    apify_api_token: Optional[str] = field(default_factory=lambda: os.getenv("APIFY_API_TOKEN"))
    apify_actor_id: str = field(default_factory=lambda: os.getenv("APIFY_ACTOR_ID", "apidojo/tweet-scraper"))
    
    # Scraping settings
    scrape_interval_hours: int = field(default_factory=lambda: int(os.getenv("SCRAPE_INTERVAL_HOURS", "4")))
    max_tweets_per_query: int = field(default_factory=lambda: int(os.getenv("MAX_TWEETS_PER_QUERY", "100")))
    rate_limit_delay: float = field(default_factory=lambda: float(os.getenv("RATE_LIMIT_DELAY", "2.0")))
    
    # Enable/disable scrapers
    enable_twscrape: bool = field(default_factory=lambda: os.getenv("ENABLE_TWSCRAPE", "true").lower() == "true")
    enable_apify: bool = field(default_factory=lambda: os.getenv("ENABLE_APIFY", "true").lower() == "true")
    enable_scweet: bool = field(default_factory=lambda: os.getenv("ENABLE_SCWEET", "false").lower() == "true")
    
    # Revenue detection
    min_mrr_threshold: int = field(default_factory=lambda: int(os.getenv("MIN_MRR_THRESHOLD", "500")))
    
    # Search queries - optimized for MRR/revenue tweets
    search_queries: List[str] = field(default_factory=lambda: [
        # Direct MRR mentions
        '"$1k MRR"',
        '"$2k MRR"', 
        '"$5k MRR"',
        '"$10k MRR"',
        '"$1K MRR"',
        '"$5K MRR"',
        '"$10K MRR"',
        # Milestone tweets
        '"hit $" MRR',
        '"reached $" MRR',
        '"crossed $" MRR',
        '"passed $" MRR',
        # Revenue mentions
        '"$" monthly revenue',
        '"$" ARR',
        'MRR milestone #buildinpublic',
        # Screenshot proof
        'stripe dashboard #buildinpublic',
        'stripe screenshot MRR',
        # Community hashtags with revenue
        '#buildinpublic MRR',
        '#indiehackers MRR',
        '#microsaas revenue',
    ])
    
    def has_apify(self) -> bool:
        """Check if Apify is configured."""
        return bool(self.apify_api_token)


@dataclass
class TwitterConfig:
    """Twitter API configuration (legacy, for API-based access)."""
    bearer_token: str = field(default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""))
    
    # Default hashtags to search
    default_hashtags: List[str] = field(default_factory=lambda: [
        "buildinpublic",
        "indiehackers",
        "saas",
        "mrr",
        "solopreneur"
    ])
    
    # Default keywords to search
    default_keywords: List[str] = field(default_factory=lambda: [
        "MRR",
        "revenue",
        "ARR",
        "per month",
        "stripe",
        "paying customers"
    ])
    
    # Max results per query
    max_results: int = 100
    
    def validate(self) -> bool:
        """Check if Twitter credentials are configured."""
        return bool(self.bearer_token)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    # PostgreSQL connection URL (primary)
    url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "postgresql://saas_finder:saas_finder_secret@localhost:5432/saas_finder"
    ))
    # SQLite fallback path (for local dev without Docker)
    sqlite_path: str = field(default_factory=lambda: os.getenv("DATABASE_PATH", "./data/ideas.db"))
    
    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return self.url.startswith("postgresql")
    
    def get_connection_url(self) -> str:
        """Get the database connection URL."""
        return self.url
    
    def ensure_directory(self) -> None:
        """Create database directory if using SQLite."""
        if not self.is_postgres:
            db_path = Path(self.sqlite_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class TrafficConfig:
    """Traffic analysis API configuration."""
    similarweb_api_key: Optional[str] = field(default_factory=lambda: os.getenv("SIMILARWEB_API_KEY"))
    semrush_api_key: Optional[str] = field(default_factory=lambda: os.getenv("SEMRUSH_API_KEY"))
    
    def has_traffic_api(self) -> bool:
        """Check if any traffic API is configured."""
        return bool(self.similarweb_api_key or self.semrush_api_key)


@dataclass
class NotificationConfig:
    """Notification configuration."""
    slack_webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL"))
    
    def has_slack(self) -> bool:
        """Check if Slack is configured."""
        return bool(self.slack_webhook_url)


@dataclass
class ScoringConfig:
    """Scoring system weights."""
    # Traction (MRR thresholds)
    mrr_high: int = 10000  # 30 points
    mrr_medium: int = 5000  # 20 points
    mrr_low: int = 1000    # 10 points
    
    # Engagement rate threshold
    engagement_rate_threshold: float = 0.05  # 5%
    
    # Follower thresholds
    follower_threshold: int = 5000
    
    # Traffic diversity thresholds
    organic_traffic_threshold: float = 0.30  # 30%


@dataclass
class RedisConfig:
    """Redis configuration for task queue."""
    url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))


@dataclass
class Config:
    """Main configuration container."""
    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)


# Global config instance
config = Config()
