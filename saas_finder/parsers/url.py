"""
URL extractor for finding and validating product URLs in tweets.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass
class ProductURL:
    """Extracted product URL with metadata."""
    url: str
    domain: str
    is_product_url: bool
    product_name: Optional[str] = None
    confidence: float = 0.5
    
    def __str__(self) -> str:
        return self.url


# Domains that are NOT product URLs (social media, link shorteners, etc.)
EXCLUDED_DOMAINS = {
    # Social Media
    "twitter.com",
    "x.com",
    "t.co",
    "pic.twitter.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "reddit.com",
    "threads.net",
    "mastodon.social",
    
    # Link Shorteners
    "bit.ly",
    "goo.gl",
    "tinyurl.com",
    "ow.ly",
    "buff.ly",
    "is.gd",
    "v.gd",
    "shorte.st",
    "adf.ly",
    
    # Common Non-Product Sites
    "medium.com",
    "substack.com",
    "notion.so",
    "docs.google.com",
    "drive.google.com",
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "imgur.com",
    "giphy.com",
    
    # Payment/Analytics (likely internal links)
    "stripe.com",
    "paypal.com",
    "analytics.google.com",
}

# Domains that suggest product pages
PRODUCT_DOMAIN_PATTERNS = [
    r".*\.io$",
    r".*\.ai$",
    r".*\.co$",
    r".*\.app$",
    r".*\.so$",
    r".*\.tools?$",
    r".*\.dev$",
    r".*\.xyz$",
    r"get.*\.com$",
    r"try.*\.com$",
    r"use.*\.com$",
]


@dataclass
class URLExtractor:
    """
    Extractor for finding and validating product URLs in text.
    """
    
    excluded_domains: set[str] = field(default_factory=set)
    product_patterns: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.excluded_domains:
            self.excluded_domains = EXCLUDED_DOMAINS.copy()
        if not self.product_patterns:
            self.product_patterns = PRODUCT_DOMAIN_PATTERNS.copy()
    
    def extract_urls(self, text: str) -> list[str]:
        """
        Extract all URLs from text.
        
        Args:
            text: Text to search
        
        Returns:
            List of URLs found
        """
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        urls = re.findall(url_pattern, text)
        
        # Clean up URLs (remove trailing punctuation)
        cleaned = []
        for url in urls:
            # Remove common trailing characters that aren't part of URLs
            url = url.rstrip('.,;:!?)\'\"')
            if url:
                cleaned.append(url)
        
        return cleaned
    
    def extract_product_urls(self, urls: list[str]) -> list[ProductURL]:
        """
        Filter and analyze URLs to find product URLs.
        
        Args:
            urls: List of URLs to analyze
        
        Returns:
            List of ProductURL objects
        """
        results = []
        
        for url in urls:
            product_url = self._analyze_url(url)
            if product_url.is_product_url:
                results.append(product_url)
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def _analyze_url(self, url: str) -> ProductURL:
        """
        Analyze a URL and determine if it's a product URL.
        
        Args:
            url: URL to analyze
        
        Returns:
            ProductURL object with analysis results
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            
            # Check if excluded
            if domain in self.excluded_domains:
                return ProductURL(
                    url=url,
                    domain=domain,
                    is_product_url=False,
                    confidence=0.0
                )
            
            # Base confidence
            confidence = 0.5
            
            # Check against product domain patterns
            for pattern in self.product_patterns:
                if re.match(pattern, domain):
                    confidence += 0.2
                    break
            
            # Check path - root or simple paths are more likely to be product pages
            path = parsed.path.strip('/')
            if not path:  # Root URL
                confidence += 0.15
            elif path.count('/') == 0:  # Single level path
                confidence += 0.1
            elif path.count('/') > 2:  # Deep paths are less likely to be product pages
                confidence -= 0.1
            
            # Check for common product page paths
            product_paths = ['pricing', 'features', 'demo', 'signup', 'register', 'start']
            if any(p in path.lower() for p in product_paths):
                confidence += 0.1
            
            # Try to extract product name from domain
            product_name = self._extract_product_name(domain)
            
            # Determine if it's a product URL
            is_product = confidence >= 0.5
            
            return ProductURL(
                url=url,
                domain=domain,
                is_product_url=is_product,
                product_name=product_name,
                confidence=min(confidence, 1.0)
            )
            
        except (ValueError, AttributeError, KeyError):
            return ProductURL(
                url=url,
                domain="",
                is_product_url=False,
                confidence=0.0
            )
    
    def _extract_product_name(self, domain: str) -> Optional[str]:
        """
        Try to extract product name from domain.
        
        Args:
            domain: Domain name
        
        Returns:
            Extracted product name or None
        """
        # Remove TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return None
        
        name_part = parts[0]
        
        # Remove common prefixes
        prefixes = ['get', 'try', 'use', 'my', 'the', 'app', 'www']
        for prefix in prefixes:
            if name_part.lower().startswith(prefix) and len(name_part) > len(prefix):
                name_part = name_part[len(prefix):]
                break
        
        # Clean up
        if len(name_part) < 2:
            name_part = parts[0]
        
        # Capitalize
        return name_part.capitalize()
    
    def get_best_product_url(self, text: str) -> Optional[ProductURL]:
        """
        Extract the best product URL from text.
        
        Args:
            text: Text to search
        
        Returns:
            Best ProductURL or None
        """
        urls = self.extract_urls(text)
        product_urls = self.extract_product_urls(urls)
        
        if not product_urls:
            return None
        
        return product_urls[0]
    
    def extract_from_tweet(
        self,
        text: str,
        attached_urls: Optional[list[str]] = None
    ) -> list[ProductURL]:
        """
        Extract product URLs from tweet text and attached URLs.
        
        Args:
            text: Tweet text
            attached_urls: URLs from tweet entities
        
        Returns:
            List of ProductURL objects
        """
        # Combine text URLs and attached URLs
        all_urls = self.extract_urls(text)
        
        if attached_urls:
            for url in attached_urls:
                if url not in all_urls:
                    all_urls.append(url)
        
        return self.extract_product_urls(all_urls)


# Convenience functions
def extract_product_url(text: str) -> Optional[ProductURL]:
    """
    Extract the best product URL from text.
    
    Args:
        text: Text to search
    
    Returns:
        Best ProductURL or None
    """
    extractor = URLExtractor()
    return extractor.get_best_product_url(text)


def is_product_domain(url: str) -> bool:
    """
    Check if a URL is likely a product URL.
    
    Args:
        url: URL to check
    
    Returns:
        True if likely a product URL
    """
    extractor = URLExtractor()
    urls = extractor.extract_product_urls([url])
    return len(urls) > 0 and urls[0].is_product_url
