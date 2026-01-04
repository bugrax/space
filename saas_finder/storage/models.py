"""
SQLAlchemy models for storing SaaS ideas.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IdeaModel(Base):
    """SQLAlchemy model for SaaS ideas."""
    
    __tablename__ = "ideas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Source info
    tweet_id = Column(String(50), unique=True, index=True)
    tweet_url = Column(String(500))
    tweet_text = Column(Text)
    author_username = Column(String(100), index=True)
    author_followers = Column(Integer, default=0)
    tweet_date = Column(DateTime)
    
    # Engagement
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    
    # Revenue
    reported_mrr = Column(Float, nullable=True)
    revenue_confidence = Column(Float, default=0.0)
    
    # Product info
    product_name = Column(String(200), nullable=True)
    product_url = Column(String(500), nullable=True)
    product_domain = Column(String(200), nullable=True, index=True)
    
    # Screenshot
    has_screenshot = Column(Boolean, default=False)
    has_stripe_screenshot = Column(Boolean, default=False)
    
    # Traffic data (JSON)
    traffic_data = Column(JSON, nullable=True)
    
    # Scoring
    total_score = Column(Integer, default=0, index=True)
    traction_score = Column(Integer, default=0)
    growth_score = Column(Integer, default=0)
    traffic_score = Column(Integer, default=0)
    simplicity_score = Column(Integer, default=0)
    score_breakdown = Column(JSON, nullable=True)
    
    # Classification
    complexity = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    replicability = Column(String(20), nullable=True)
    replicability_note = Column(Text, nullable=True)
    
    # Metadata
    date_found = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User annotations
    is_favorited = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # List of user-defined tags
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "tweet_text": self.tweet_text,
            "author": f"@{self.author_username}",
            "author_followers": self.author_followers,
            "tweet_date": self.tweet_date.isoformat() if self.tweet_date else None,
            "engagement": {
                "likes": self.likes,
                "retweets": self.retweets,
                "replies": self.replies,
                "impressions": self.impressions
            },
            "reported_mrr": self.reported_mrr,
            "revenue_confidence": self.revenue_confidence,
            "product_name": self.product_name,
            "product_url": self.product_url,
            "product_domain": self.product_domain,
            "has_screenshot": self.has_screenshot,
            "has_stripe_screenshot": self.has_stripe_screenshot,
            "traffic_data": self.traffic_data,
            "score": {
                "total": self.total_score,
                "traction": self.traction_score,
                "growth": self.growth_score,
                "traffic": self.traffic_score,
                "simplicity": self.simplicity_score,
                "breakdown": self.score_breakdown
            },
            "complexity": self.complexity,
            "category": self.category,
            "replicability": self.replicability,
            "replicability_note": self.replicability_note,
            "date_found": self.date_found.isoformat() if self.date_found else None,
            "is_favorited": self.is_favorited,
            "user_notes": self.user_notes,
            "tags": self.tags
        }


class SearchHistoryModel(Base):
    """Track search history for deduplication and analytics."""
    
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(500))
    hashtags = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    search_date = Column(DateTime, default=datetime.utcnow)
    results_count = Column(Integer, default=0)
    new_ideas_count = Column(Integer, default=0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "query": self.query,
            "hashtags": self.hashtags,
            "keywords": self.keywords,
            "search_date": self.search_date.isoformat() if self.search_date else None,
            "results_count": self.results_count,
            "new_ideas_count": self.new_ideas_count
        }


class WatchlistModel(Base):
    """Watchlist for tracking specific founders or products."""
    
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watch_type = Column(String(20))  # "founder" or "product"
    identifier = Column(String(200), index=True)  # username or domain
    added_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "watch_type": self.watch_type,
            "identifier": self.identifier,
            "added_date": self.added_date.isoformat() if self.added_date else None,
            "notes": self.notes,
            "is_active": self.is_active
        }
