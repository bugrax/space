"""
Tests for the scoring system.
"""

import pytest
from datetime import datetime, timezone

from saas_finder.scoring.scorer import (
    IdeaScorer,
    SaaSIdea,
    TrafficData,
    ProductComplexity,
    ReplicabilityLevel
)


class TestIdeaScorer:
    """Test the idea scoring system."""
    
    def setup_method(self):
        self.scorer = IdeaScorer()
    
    def create_sample_idea(self, **kwargs) -> SaaSIdea:
        """Create a sample idea for testing."""
        defaults = {
            "tweet_id": "123456",
            "tweet_url": "https://twitter.com/user/status/123456",
            "tweet_text": "Sample tweet text",
            "author_username": "testuser",
            "author_followers": 1000,
            "tweet_date": datetime.now(timezone.utc),
            "likes": 100,
            "retweets": 20,
            "replies": 10,
            "impressions": 5000,
            "reported_mrr": 5000,
            "has_screenshot": False,
            "complexity": ProductComplexity.SIMPLE_SAAS,
        }
        defaults.update(kwargs)
        return SaaSIdea(**defaults)
    
    def test_high_mrr_score(self):
        """Test scoring for high MRR."""
        idea = self.create_sample_idea(reported_mrr=15000)
        result = self.scorer.score_idea(idea)
        
        assert result.traction_score == 30
    
    def test_medium_mrr_score(self):
        """Test scoring for medium MRR."""
        idea = self.create_sample_idea(reported_mrr=7000)
        result = self.scorer.score_idea(idea)
        
        assert result.traction_score == 20
    
    def test_low_mrr_score(self):
        """Test scoring for low MRR."""
        idea = self.create_sample_idea(reported_mrr=2000)
        result = self.scorer.score_idea(idea)
        
        assert result.traction_score == 10
    
    def test_screenshot_bonus(self):
        """Test growth score with screenshot."""
        idea = self.create_sample_idea(has_screenshot=True)
        result = self.scorer.score_idea(idea)
        
        assert result.growth_score >= 10
    
    def test_stripe_screenshot_bonus(self):
        """Test higher bonus for Stripe screenshot."""
        idea = self.create_sample_idea(
            has_screenshot=True,
            has_stripe_screenshot=True
        )
        result = self.scorer.score_idea(idea)
        
        assert result.growth_score >= 12
    
    def test_high_engagement_bonus(self):
        """Test engagement rate bonus."""
        idea = self.create_sample_idea(
            likes=500,
            retweets=100,
            replies=50,
            impressions=5000  # 13% engagement
        )
        result = self.scorer.score_idea(idea)
        
        # Should get engagement bonus
        assert "engagement" in result.breakdown.get("growth", "").lower()
    
    def test_simplicity_single_feature(self):
        """Test simplicity score for single feature tool."""
        idea = self.create_sample_idea(
            complexity=ProductComplexity.SINGLE_FEATURE
        )
        result = self.scorer.score_idea(idea)
        
        assert result.simplicity_score == 20
    
    def test_simplicity_complex(self):
        """Test simplicity score for complex product."""
        idea = self.create_sample_idea(
            complexity=ProductComplexity.COMPLEX_SAAS
        )
        result = self.scorer.score_idea(idea)
        
        assert result.simplicity_score <= 10
    
    def test_traffic_diversity(self):
        """Test traffic diversity scoring."""
        traffic = TrafficData(
            organic_percent=0.4,
            paid_percent=0.3,
            social_percent=0.2,
            referral_percent=0.1
        )
        idea = self.create_sample_idea()
        idea.traffic = traffic
        
        result = self.scorer.score_idea(idea)
        
        # Should get both organic and diversity bonus
        assert result.traffic_score >= 20
    
    def test_total_score_calculation(self):
        """Test total score is sum of components."""
        idea = self.create_sample_idea(
            reported_mrr=10000,  # 30 traction
            has_screenshot=True,  # 10 growth
            complexity=ProductComplexity.SINGLE_FEATURE  # 20 simplicity
        )
        result = self.scorer.score_idea(idea)
        
        expected = (
            result.traction_score +
            result.growth_score +
            result.traffic_score +
            result.simplicity_score
        )
        assert result.total_score == expected
    
    def test_replicability_high_paid(self):
        """Test replicability for high paid traffic."""
        traffic = TrafficData(paid_percent=0.6, organic_percent=0.2)
        idea = self.create_sample_idea()
        idea.traffic = traffic
        
        level, note = self.scorer.determine_replicability(idea)
        
        assert level == ReplicabilityLevel.HIGH
        assert "paid" in note.lower()
    
    def test_replicability_high_organic(self):
        """Test replicability for high organic traffic."""
        traffic = TrafficData(paid_percent=0.1, organic_percent=0.7)
        idea = self.create_sample_idea()
        idea.traffic = traffic
        
        level, note = self.scorer.determine_replicability(idea)
        
        assert level == ReplicabilityLevel.LOW
        assert "organic" in note.lower()
    
    def test_grade_a_plus(self):
        """Test A+ grade for high score."""
        idea = self.create_sample_idea(
            reported_mrr=15000,
            has_stripe_screenshot=True,
            has_screenshot=True,
            author_followers=10000,
            likes=500,
            impressions=5000,
            complexity=ProductComplexity.SINGLE_FEATURE
        )
        idea.traffic = TrafficData(organic_percent=0.4, paid_percent=0.3)
        
        result = self.scorer.score_idea(idea)
        
        # With all bonuses, should be high score
        assert result.total_score >= 70


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
