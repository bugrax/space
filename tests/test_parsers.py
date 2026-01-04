"""
Tests for the MRR parser.
"""

import pytest
from saas_finder.parsers.mrr import MRRParser, RevenueType


class TestMRRParser:
    """Test MRR parsing functionality."""
    
    def setup_method(self):
        self.parser = MRRParser()
    
    def test_basic_mrr_format(self):
        """Test basic $X MRR format."""
        result = self.parser.get_best_mrr("Just hit $10,000 MRR!")
        assert result is not None
        assert result.amount == 10000
        assert result.type == RevenueType.MRR
    
    def test_k_format(self):
        """Test $XK MRR format."""
        result = self.parser.get_best_mrr("Crossed $10K MRR today!")
        assert result is not None
        assert result.amount == 10000
        assert result.type == RevenueType.MRR
    
    def test_arr_format(self):
        """Test ARR format."""
        result = self.parser.get_best_mrr("We're at $120K ARR")
        assert result is not None
        assert result.amount == 120000
        assert result.type == RevenueType.ARR
        assert result.monthly_equivalent == 10000
    
    def test_per_month_format(self):
        """Test per month format."""
        result = self.parser.get_best_mrr("Making $5,000 per month")
        assert result is not None
        assert result.amount == 5000
        assert result.type == RevenueType.MONTHLY
    
    def test_slash_month_format(self):
        """Test /month format."""
        result = self.parser.get_best_mrr("Revenue: $3K/month")
        assert result is not None
        assert result.amount == 3000
    
    def test_hit_crossed_format(self):
        """Test hit/crossed pattern."""
        result = self.parser.get_best_mrr("Finally crossed $20K! So happy!")
        assert result is not None
        assert result.amount == 20000
    
    def test_no_revenue(self):
        """Test text without revenue."""
        result = self.parser.get_best_mrr("Building something cool")
        assert result is None
    
    def test_small_amount_ignored(self):
        """Test that very small amounts are ignored."""
        result = self.parser.get_best_mrr("Only spent $50 on marketing")
        assert result is None
    
    def test_has_revenue_mention(self):
        """Test has_revenue_mention method."""
        assert self.parser.has_revenue_mention("$10K MRR")
        assert self.parser.has_revenue_mention("making $5000/month")
        assert not self.parser.has_revenue_mention("just launched!")
    
    def test_paying_customers_format(self):
        """Test paying customers pattern."""
        result = self.parser.get_best_mrr("50 paying customers at $100")
        assert result is not None
        assert result.amount == 5000


class TestURLExtractor:
    """Test URL extraction functionality."""
    
    def test_basic_extraction(self):
        from saas_finder.parsers.url import URLExtractor
        
        extractor = URLExtractor()
        urls = extractor.extract_urls("Check out https://example.com for more")
        
        assert len(urls) == 1
        assert urls[0] == "https://example.com"
    
    def test_product_url_detection(self):
        from saas_finder.parsers.url import URLExtractor
        
        extractor = URLExtractor()
        result = extractor.get_best_product_url("My tool: https://mytool.io")
        
        assert result is not None
        assert result.is_product_url
        assert result.domain == "mytool.io"
    
    def test_social_media_excluded(self):
        from saas_finder.parsers.url import URLExtractor
        
        extractor = URLExtractor()
        urls = ["https://twitter.com/user", "https://linkedin.com/in/user"]
        results = extractor.extract_product_urls(urls)
        
        assert len(results) == 0
    
    def test_product_name_extraction(self):
        from saas_finder.parsers.url import URLExtractor
        
        extractor = URLExtractor()
        result = extractor.get_best_product_url("https://getmyproduct.com")
        
        assert result is not None
        assert result.product_name == "Myproduct"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
