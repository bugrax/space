"""
Data models for Twitter data.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class RevenueType(str, Enum):
    """Type of revenue reported."""
    MRR = "MRR"
    ARR = "ARR"
    MONTHLY = "MONTHLY"
    UNKNOWN = "UNKNOWN"


class ExtractedRevenue(BaseModel):
    """Revenue data extracted from tweet text."""
    raw_match: str
    amount: int
    type: RevenueType
    confidence: float  # 0.0 - 1.0
    has_screenshot: bool = False


class ExtractedProduct(BaseModel):
    """Product information extracted from tweet URLs."""
    url: str
    name: Optional[str] = None
    domain: str
    is_valid_product: bool = True


class TweetAuthor(BaseModel):
    """Twitter user/author information."""
    id: str
    username: str
    name: str
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    verified: bool = False
    description: Optional[str] = None
    profile_image_url: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Alias for compatibility
    @property
    def display_name(self) -> str:
        return self.name


class TweetMedia(BaseModel):
    """Media attachment in a tweet."""
    media_key: Optional[str] = None
    type: str  # "photo", "video", "animated_gif"
    url: Optional[str] = None
    preview_image_url: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Alias for compatibility
    @property
    def preview_url(self) -> Optional[str]:
        return self.preview_image_url


class TweetMetrics(BaseModel):
    """Engagement metrics for a tweet."""
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    impression_count: int = 0
    bookmark_count: int = 0
    
    @property
    def total_engagement(self) -> int:
        """Calculate total engagement."""
        return self.like_count + self.retweet_count + self.reply_count + self.quote_count
    
    def engagement_rate(self, impressions: Optional[int] = None) -> float:
        """
        Calculate engagement rate.
        Uses impressions if available, otherwise returns 0.
        """
        imp = impressions or self.impression_count
        if imp == 0:
            return 0.0
        return self.total_engagement / imp


class Tweet(BaseModel):
    """Represents a tweet with all relevant data."""
    id: str
    text: str
    created_at: datetime
    author: Optional[TweetAuthor] = None
    metrics: TweetMetrics = Field(default_factory=TweetMetrics)
    media: List[TweetMedia] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    mentioned_users: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    source: Optional[str] = None  # 'twscrape', 'apify', 'scweet', 'nitter', 'mock'
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional fields from apidojo
    is_reply: bool = False
    is_retweet: bool = False
    is_quote: bool = False
    
    # Computed engagement rate
    engagement_rate: float = 0.0
    
    @property
    def tweet_url(self) -> str:
        """Get the URL to this tweet."""
        if self.author:
            return f"https://twitter.com/{self.author.username}/status/{self.id}"
        return f"https://twitter.com/i/status/{self.id}"
    
    # Alias for compatibility
    @property
    def url(self) -> str:
        return self.tweet_url
    
    @property
    def likes(self) -> int:
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return m.like_count
    
    @property
    def retweets(self) -> int:
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return m.retweet_count
    
    @property
    def replies(self) -> int:
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return m.reply_count
    
    @property
    def quotes(self) -> int:
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return m.quote_count
    
    @property
    def views(self) -> Optional[int]:
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return m.impression_count if m.impression_count > 0 else None
    
    @property
    def has_image(self) -> bool:
        """Check if tweet has image attachments."""
        return any(m.type == "photo" for m in self.media)
    
    @property
    def has_video(self) -> bool:
        """Check if tweet has video attachments."""
        return any(m.type in ("video", "animated_gif") for m in self.media)
    
    @property
    def external_urls(self) -> List[str]:
        """Get URLs that are not Twitter/X links."""
        excluded_domains = [
            "twitter.com",
            "x.com",
            "t.co",
            "pic.twitter.com"
        ]
        return [
            url for url in self.urls
            if not any(domain in url.lower() for domain in excluded_domains)
        ]
    
    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate based on author's followers."""
        if not self.author or self.author.followers_count == 0:
            return 0.0
        m: TweetMetrics = self.metrics  # type: ignore[assignment]
        return (m.total_engagement / self.author.followers_count) * 100
    
    def model_dump_json_friendly(self) -> dict:
        """Return a JSON-serializable dictionary."""
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        data["tweet_url"] = self.tweet_url
        data["has_image"] = self.has_image
        data["external_urls"] = self.external_urls
        return data

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SaaSIdea(BaseModel):
    """Extracted SaaS idea from a tweet."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Source
    source_tweet_id: str
    source_tweet_url: str
    source_tweet_text: str
    
    # Author
    author_username: str
    author_followers: int
    author_verified: bool
    
    # Extracted Data
    revenue: Optional[ExtractedRevenue] = None
    products: List[ExtractedProduct] = Field(default_factory=list)
    
    # Engagement from tweet
    likes: int
    retweets: int
    engagement_rate: float
    
    # Timestamps
    tweet_created_at: datetime
    found_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    status: str = "new"  # new, validated, rejected, building
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

