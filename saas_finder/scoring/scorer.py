"""
Scoring system for evaluating SaaS ideas.

Implements a 4-filter scoring system:
1. Traction (0-30 points): Based on MRR amount
2. Growth Signal (0-25 points): Based on screenshots, engagement, followers
3. Traffic Diversity (0-25 points): Based on traffic sources
4. Simplicity (0-20 points): Based on product complexity
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ..config import config
from ..twitter.models import Tweet
from ..parsers.mrr import MRRParser
from ..parsers.url import URLExtractor


class ReplicabilityLevel(str, Enum):
    """How replicable is this SaaS idea."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ProductComplexity(str, Enum):
    """Estimated product complexity."""
    SINGLE_FEATURE = "single_feature"
    SIMPLE_SAAS = "simple_saas"
    COMPLEX_SAAS = "complex_saas"
    PLATFORM = "platform"
    UNKNOWN = "unknown"


@dataclass
class TrafficData:
    """Traffic analysis data for a product."""
    organic_percent: float = 0.0
    paid_percent: float = 0.0
    social_percent: float = 0.0
    referral_percent: float = 0.0
    direct_percent: float = 0.0
    estimated_monthly_visits: Optional[int] = None
    domain_authority: Optional[int] = None
    top_keywords: list[str] = field(default_factory=list)
    
    @property
    def has_data(self) -> bool:
        """Check if traffic data is available."""
        return any([
            self.organic_percent > 0,
            self.paid_percent > 0,
            self.social_percent > 0,
            self.estimated_monthly_visits is not None
        ])


@dataclass
class ScoringResult:
    """Result of scoring an idea."""
    total_score: int
    traction_score: int  # 0-30
    growth_score: int    # 0-25
    traffic_score: int   # 0-25
    simplicity_score: int  # 0-20
    breakdown: dict[str, str] = field(default_factory=dict)
    
    @property
    def grade(self) -> str:
        """Get letter grade based on score."""
        if self.total_score >= 90:
            return "A+"
        elif self.total_score >= 80:
            return "A"
        elif self.total_score >= 70:
            return "B"
        elif self.total_score >= 60:
            return "C"
        elif self.total_score >= 50:
            return "D"
        else:
            return "F"


@dataclass
class SaaSIdea:
    """
    A validated SaaS idea extracted from Twitter.
    """
    # Source information
    tweet_id: str
    tweet_url: str
    tweet_text: str
    author_username: str
    author_followers: int
    tweet_date: datetime
    
    # Engagement
    likes: int
    retweets: int
    replies: int
    impressions: int
    
    # Revenue data
    reported_mrr: Optional[float] = None
    revenue_confidence: float = 0.0
    
    # Product info
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    product_domain: Optional[str] = None
    
    # Screenshot indicator
    has_screenshot: bool = False
    has_stripe_screenshot: bool = False  # If screenshot likely shows Stripe
    
    # Traffic data
    traffic: TrafficData = field(default_factory=TrafficData)
    
    # Scoring
    score: Optional[ScoringResult] = None
    
    # Classification
    complexity: ProductComplexity = ProductComplexity.UNKNOWN
    category: Optional[str] = None
    replicability: ReplicabilityLevel = ReplicabilityLevel.UNKNOWN
    replicability_note: Optional[str] = None
    
    # Metadata
    date_found: datetime = field(default_factory=datetime.now)
    
    @property
    def total_score(self) -> int:
        """Get total score or 0."""
        return self.score.total_score if self.score else 0
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.impressions == 0:
            return 0.0
        total_engagement = self.likes + self.retweets + self.replies
        return total_engagement / self.impressions
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "product_name": self.product_name or "Unknown",
            "product_url": self.product_url,
            "found_in_tweet": self.tweet_url,
            "author": f"@{self.author_username}",
            "author_followers": self.author_followers,
            "reported_mrr": self.reported_mrr,
            "score": self.total_score,
            "grade": self.score.grade if self.score else "N/A",
            "score_breakdown": {
                "traction": self.score.traction_score if self.score else 0,
                "growth": self.score.growth_score if self.score else 0,
                "traffic": self.score.traffic_score if self.score else 0,
                "simplicity": self.score.simplicity_score if self.score else 0
            },
            "engagement": {
                "likes": self.likes,
                "retweets": self.retweets,
                "replies": self.replies,
                "rate": f"{self.engagement_rate:.2%}"
            },
            "traffic_source": {
                "organic": f"{self.traffic.organic_percent:.0%}",
                "paid": f"{self.traffic.paid_percent:.0%}",
                "social": f"{self.traffic.social_percent:.0%}",
                "referral": f"{self.traffic.referral_percent:.0%}"
            } if self.traffic.has_data else None,
            "has_screenshot": self.has_screenshot,
            "replicability": self.replicability.value,
            "replicability_note": self.replicability_note,
            "category": self.category,
            "complexity": self.complexity.value,
            "date_found": self.date_found.isoformat(),
            "tweet_date": self.tweet_date.isoformat()
        }


class IdeaScorer:
    """
    Scores SaaS ideas based on 4 filters.
    """
    
    def __init__(self):
        self.mrr_parser = MRRParser()
        self.url_extractor = URLExtractor()
        self.scoring_config = config.scoring
    
    def score_idea(self, idea: SaaSIdea) -> ScoringResult:
        """
        Calculate score for a SaaS idea.
        
        Args:
            idea: SaaSIdea to score
        
        Returns:
            ScoringResult with breakdown
        """
        breakdown = {}
        
        # Filter 1: Traction (0-30 points)
        traction_score, traction_details = self._score_traction(idea)
        breakdown["traction"] = traction_details
        
        # Filter 2: Growth Signal (0-25 points)
        growth_score, growth_details = self._score_growth(idea)
        breakdown["growth"] = growth_details
        
        # Filter 3: Traffic Diversity (0-25 points)
        traffic_score, traffic_details = self._score_traffic(idea)
        breakdown["traffic"] = traffic_details
        
        # Filter 4: Simplicity (0-20 points)
        simplicity_score, simplicity_details = self._score_simplicity(idea)
        breakdown["simplicity"] = simplicity_details
        
        total = traction_score + growth_score + traffic_score + simplicity_score
        
        return ScoringResult(
            total_score=total,
            traction_score=traction_score,
            growth_score=growth_score,
            traffic_score=traffic_score,
            simplicity_score=simplicity_score,
            breakdown=breakdown
        )
    
    def _score_traction(self, idea: SaaSIdea) -> tuple[int, str]:
        """
        Score based on MRR traction.
        
        0-30 points based on MRR amount.
        """
        score = 0
        details = []
        
        mrr = idea.reported_mrr or 0
        
        if mrr >= self.scoring_config.mrr_high:  # $10K+
            score = 30
            details.append(f"High MRR (${mrr:,.0f}): +30")
        elif mrr >= self.scoring_config.mrr_medium:  # $5K+
            score = 20
            details.append(f"Medium MRR (${mrr:,.0f}): +20")
        elif mrr >= self.scoring_config.mrr_low:  # $1K+
            score = 10
            details.append(f"Low MRR (${mrr:,.0f}): +10")
        else:
            details.append(f"No significant MRR (${mrr:,.0f}): +0")
        
        # Bonus for high confidence
        if idea.revenue_confidence >= 0.9:
            score = min(score + 2, 30)
            details.append("High confidence revenue data: +2")
        
        return score, " | ".join(details)
    
    def _score_growth(self, idea: SaaSIdea) -> tuple[int, str]:
        """
        Score based on growth signals.
        
        0-25 points based on:
        - Has screenshot: +10
        - Engagement rate > 5%: +10
        - Author followers > 5000: +5
        """
        score = 0
        details = []
        
        # Screenshot presence (especially Stripe)
        if idea.has_stripe_screenshot:
            score += 12
            details.append("Stripe screenshot: +12")
        elif idea.has_screenshot:
            score += 10
            details.append("Has screenshot: +10")
        
        # Engagement rate
        eng_threshold = self.scoring_config.engagement_rate_threshold
        if idea.engagement_rate > eng_threshold:
            score += 10
            details.append(f"High engagement ({idea.engagement_rate:.1%}): +10")
        elif idea.engagement_rate > eng_threshold / 2:
            score += 5
            details.append(f"Medium engagement ({idea.engagement_rate:.1%}): +5")
        
        # Author influence
        if idea.author_followers >= self.scoring_config.follower_threshold:
            score += 5
            details.append(f"Influential author ({idea.author_followers:,} followers): +5")
        elif idea.author_followers >= self.scoring_config.follower_threshold / 2:
            score += 3
            details.append(f"Growing author ({idea.author_followers:,} followers): +3")
        
        # Cap at 25
        score = min(score, 25)
        
        if not details:
            details.append("No strong growth signals: +0")
        
        return score, " | ".join(details)
    
    def _score_traffic(self, idea: SaaSIdea) -> tuple[int, str]:
        """
        Score based on traffic diversity.
        
        0-25 points based on:
        - Organic traffic > 30%: +15
        - Has both paid and organic: +10
        """
        score = 0
        details = []
        
        if not idea.traffic.has_data:
            # No traffic data available - give neutral score
            return 10, "No traffic data available: +10 (neutral)"
        
        traffic = idea.traffic
        organic_threshold = self.scoring_config.organic_traffic_threshold
        
        # Organic traffic
        if traffic.organic_percent >= organic_threshold:
            score += 15
            details.append(f"Strong organic ({traffic.organic_percent:.0%}): +15")
        elif traffic.organic_percent >= organic_threshold / 2:
            score += 8
            details.append(f"Some organic ({traffic.organic_percent:.0%}): +8")
        
        # Traffic diversity (both paid and organic)
        if traffic.paid_percent > 0.05 and traffic.organic_percent > 0.05:
            score += 10
            details.append("Diverse traffic sources: +10")
        
        # Cap at 25
        score = min(score, 25)
        
        if not details:
            details.append("Limited traffic diversity: +0")
        
        return score, " | ".join(details)
    
    def _score_simplicity(self, idea: SaaSIdea) -> tuple[int, str]:
        """
        Score based on product simplicity.
        
        0-20 points based on complexity:
        - Single feature tool: +20
        - Simple SaaS: +10
        - Complex SaaS/Platform: +0
        """
        score = 0
        details = []
        
        if idea.complexity == ProductComplexity.SINGLE_FEATURE:
            score = 20
            details.append("Single feature tool: +20")
        elif idea.complexity == ProductComplexity.SIMPLE_SAAS:
            score = 10
            details.append("Simple SaaS: +10")
        elif idea.complexity == ProductComplexity.COMPLEX_SAAS:
            score = 5
            details.append("Complex SaaS: +5")
        elif idea.complexity == ProductComplexity.PLATFORM:
            score = 0
            details.append("Platform (complex): +0")
        else:
            # Unknown - give neutral score
            score = 10
            details.append("Complexity unknown: +10 (neutral)")
        
        return score, " | ".join(details)
    
    def determine_replicability(self, idea: SaaSIdea) -> tuple[ReplicabilityLevel, str]:
        """
        Determine how replicable this idea is.
        
        Args:
            idea: SaaSIdea to analyze
        
        Returns:
            Tuple of (ReplicabilityLevel, explanation)
        """
        traffic = idea.traffic
        
        # High paid traffic = easy to replicate with ads
        if traffic.paid_percent > 0.5:
            return (
                ReplicabilityLevel.HIGH,
                f"Mostly paid traffic ({traffic.paid_percent:.0%}), can launch ads quickly"
            )
        
        # Balanced traffic = medium replicability
        if traffic.paid_percent > 0.2 and traffic.organic_percent > 0.2:
            return (
                ReplicabilityLevel.MEDIUM,
                "Mixed traffic sources, requires both SEO and ads strategy"
            )
        
        # High organic = harder to replicate (SEO takes time)
        if traffic.organic_percent > 0.6:
            return (
                ReplicabilityLevel.LOW,
                f"Mostly organic ({traffic.organic_percent:.0%}), SEO advantage hard to replicate"
            )
        
        # Simple product = easier to replicate
        if idea.complexity == ProductComplexity.SINGLE_FEATURE:
            return (
                ReplicabilityLevel.HIGH,
                "Simple single-feature tool, can build MVP quickly"
            )
        
        # Low MRR might mean untapped market
        if idea.reported_mrr and idea.reported_mrr < 5000:
            return (
                ReplicabilityLevel.MEDIUM,
                "Early stage, market validation still needed"
            )
        
        return (ReplicabilityLevel.UNKNOWN, "Insufficient data for analysis")
    
    def process_tweet(self, tweet: Tweet) -> Optional[SaaSIdea]:
        """
        Process a tweet and create a SaaSIdea if it contains revenue data.
        
        Args:
            tweet: Tweet to process
        
        Returns:
            SaaSIdea or None if not relevant
        """
        # Parse MRR
        revenue_data = self.mrr_parser.get_best_mrr(tweet.text)
        
        # Extract product URL
        product_urls = self.url_extractor.extract_from_tweet(
            tweet.text,
            tweet.urls
        )
        
        # Determine if we have enough data
        has_revenue = revenue_data is not None
        
        # Skip if no revenue mention (core requirement)
        if not has_revenue:
            return None
        
        # Get best product URL
        product_url = product_urls[0] if product_urls else None
        
        # Detect screenshot type
        has_screenshot = tweet.has_image
        has_stripe_screenshot = self._is_stripe_screenshot(tweet)
        
        # Create idea
        idea = SaaSIdea(
            tweet_id=tweet.id,
            tweet_url=tweet.tweet_url,
            tweet_text=tweet.text,
            author_username=tweet.author.username if tweet.author else "unknown",
            author_followers=tweet.author.followers_count if tweet.author else 0,
            tweet_date=tweet.created_at,
            likes=tweet.metrics.like_count,
            retweets=tweet.metrics.retweet_count,
            replies=tweet.metrics.reply_count,
            impressions=tweet.metrics.impression_count,
            reported_mrr=revenue_data.monthly_equivalent if revenue_data else None,
            revenue_confidence=revenue_data.confidence if revenue_data else 0.0,
            product_name=product_url.product_name if product_url else None,
            product_url=product_url.url if product_url else None,
            product_domain=product_url.domain if product_url else None,
            has_screenshot=has_screenshot,
            has_stripe_screenshot=has_stripe_screenshot,
            complexity=self._estimate_complexity(tweet.text),
            category=self._guess_category(tweet.text)
        )
        
        # Score the idea
        idea.score = self.score_idea(idea)
        
        # Determine replicability
        idea.replicability, idea.replicability_note = self.determine_replicability(idea)
        
        return idea
    
    def _is_stripe_screenshot(self, tweet: Tweet) -> bool:
        """
        Heuristic to detect if screenshot might be Stripe dashboard.
        
        Args:
            tweet: Tweet to analyze
        
        Returns:
            True if likely Stripe screenshot
        """
        if not tweet.has_image:
            return False
        
        text_lower = tweet.text.lower()
        stripe_indicators = [
            'stripe', 'dashboard', 'mrr chart', 'revenue chart',
            'stripe dashboard', 'payment', 'subscription'
        ]
        
        return any(ind in text_lower for ind in stripe_indicators)
    
    def _estimate_complexity(self, text: str) -> ProductComplexity:
        """
        Estimate product complexity from tweet text.
        
        Args:
            text: Tweet text
        
        Returns:
            ProductComplexity enum value
        """
        text_lower = text.lower()
        
        # Single feature indicators
        single_feature_words = [
            'simple tool', 'one feature', 'single feature',
            'chrome extension', 'browser extension', 'bookmarklet',
            'widget', 'plugin', 'addon', 'shortcut'
        ]
        if any(word in text_lower for word in single_feature_words):
            return ProductComplexity.SINGLE_FEATURE
        
        # Platform indicators
        platform_words = [
            'platform', 'marketplace', 'ecosystem', 'suite',
            'enterprise', 'b2b platform', 'api platform'
        ]
        if any(word in text_lower for word in platform_words):
            return ProductComplexity.PLATFORM
        
        # Complex SaaS indicators
        complex_words = [
            'integrations', 'team features', 'collaboration',
            'workflow', 'automation platform', 'enterprise'
        ]
        if any(word in text_lower for word in complex_words):
            return ProductComplexity.COMPLEX_SAAS
        
        # Simple SaaS is default if product URL exists
        return ProductComplexity.SIMPLE_SAAS
    
    def _guess_category(self, text: str) -> Optional[str]:
        """
        Guess product category from tweet text.
        
        Args:
            text: Tweet text
        
        Returns:
            Category string or None
        """
        text_lower = text.lower()
        
        categories = {
            "AI/ML Tool": ['ai', 'gpt', 'llm', 'machine learning', 'chatbot', 'ai-powered'],
            "Video Tool": ['video', 'youtube', 'tiktok', 'reels', 'shorts', 'video editor'],
            "Writing Tool": ['writing', 'copywriting', 'content', 'blog', 'seo content'],
            "Design Tool": ['design', 'figma', 'ui/ux', 'graphics', 'logo'],
            "Developer Tool": ['developer', 'api', 'devtool', 'github', 'coding', 'code'],
            "Marketing Tool": ['marketing', 'email', 'newsletter', 'social media', 'ads'],
            "Productivity Tool": ['productivity', 'notion', 'task', 'todo', 'calendar'],
            "Analytics Tool": ['analytics', 'dashboard', 'metrics', 'tracking'],
            "E-commerce Tool": ['ecommerce', 'shopify', 'store', 'dropshipping'],
            "Finance Tool": ['finance', 'invoice', 'accounting', 'expense', 'budget'],
            "HR Tool": ['hr', 'hiring', 'recruitment', 'employee', 'payroll'],
            "Education Tool": ['education', 'course', 'learning', 'tutorial', 'teaching'],
        }
        
        for category, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return None
