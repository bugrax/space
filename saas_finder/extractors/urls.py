"""
URL Extractor - Extract and validate product URLs from tweets.

Extracts URLs and determines if they're likely to be SaaS products.
"""

import re
from typing import List, Optional
from urllib.parse import urlparse

from saas_finder.twitter.models import ExtractedProduct


class URLExtractor:
    """Extract and validate product URLs from tweets."""
    
    # Domains to exclude (social media, common services)
    EXCLUDED_DOMAINS = {
        # Social media
        "twitter.com", "x.com", "t.co", "pic.twitter.com",
        "facebook.com", "fb.com", "instagram.com", "linkedin.com",
        "tiktok.com", "youtube.com", "youtu.be", "reddit.com",
        "discord.com", "discord.gg", "threads.net",
        
        # Common services
        "google.com", "goo.gl", "bit.ly", "bitly.com",
        "medium.com", "substack.com", "notion.so", "notion.site",
        "github.com", "gitlab.com", "stackoverflow.com",
        
        # Email/productivity
        "gmail.com", "outlook.com", "slack.com", "zoom.us",
        
        # Link shorteners
        "ow.ly", "tinyurl.com", "rebrand.ly", "short.io",
        "is.gd", "v.gd", "cutt.ly", "shorturl.at",
        
        # Other
        "wikipedia.org", "amazon.com", "ebay.com",
    }
    
    # Product-like TLDs and patterns
    PRODUCT_TLDS = {".com", ".io", ".co", ".app", ".dev", ".ai", ".so", ".me"}
    
    # Keywords that suggest a product
    PRODUCT_KEYWORDS = {
        "app", "dashboard", "pricing", "demo", "beta",
        "saas", "tool", "software", "platform", "service"
    }
    
    def extract(self, text: str, urls: Optional[List[str]] = None) -> List[ExtractedProduct]:
        """
        Extract product URLs from tweet text and URL list.
        
        Args:
            text: Tweet text
            urls: Pre-extracted URLs from tweet metadata
            
        Returns:
            List of ExtractedProduct objects
        """
        all_urls = set()
        
        # Get URLs from metadata
        if urls:
            all_urls.update(urls)
        
        # Also extract from text
        text_urls = self._extract_urls_from_text(text)
        all_urls.update(text_urls)
        
        products = []
        for url in all_urls:
            product = self._analyze_url(url)
            if product and product.is_valid_product:
                products.append(product)
        
        return products
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex."""
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        # Clean up URLs (remove trailing punctuation)
        cleaned = []
        for url in urls:
            # Remove trailing punctuation that might have been captured
            url = url.rstrip('.,;:!?)\'"')
            if url:
                cleaned.append(url)
        
        return cleaned
    
    def _analyze_url(self, url: str) -> Optional[ExtractedProduct]:
        """
        Analyze a URL to determine if it's a product.
        
        Args:
            url: URL to analyze
            
        Returns:
            ExtractedProduct or None
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            
            # Skip excluded domains
            if any(excluded in domain for excluded in self.EXCLUDED_DOMAINS):
                return ExtractedProduct(
                    url=url,
                    domain=domain,
                    is_valid_product=False
                )
            
            # Determine if it's likely a product
            is_product = self._is_likely_product(url, domain, parsed.path)
            
            # Try to extract product name from domain
            name = self._extract_name_from_domain(domain)
            
            return ExtractedProduct(
                url=url,
                name=name,
                domain=domain,
                is_valid_product=is_product
            )
            
        except Exception:
            return None
    
    def _is_likely_product(self, url: str, domain: str, path: str) -> bool:
        """Determine if URL is likely a SaaS product."""
        url_lower = url.lower()
        
        # Check for product TLDs
        has_product_tld = any(domain.endswith(tld) for tld in self.PRODUCT_TLDS)
        
        # Check for product keywords in URL
        has_product_keyword = any(kw in url_lower for kw in self.PRODUCT_KEYWORDS)
        
        # Short domain names are often products
        base_domain = domain.split('.')[0]
        is_short_domain = len(base_domain) <= 15
        
        # Paths that suggest products
        product_paths = ["/pricing", "/demo", "/features", "/about", "/blog"]
        has_product_path = any(p in path.lower() for p in product_paths)
        
        # Score-based decision
        score = 0
        if has_product_tld:
            score += 2
        if has_product_keyword:
            score += 2
        if is_short_domain:
            score += 1
        if has_product_path:
            score += 1
        if domain.endswith(".ai") or domain.endswith(".io"):
            score += 1  # Extra boost for AI/IO domains
        
        return score >= 2
    
    def _extract_name_from_domain(self, domain: str) -> str:
        """Extract a product name from domain."""
        # Remove TLD
        parts = domain.split('.')
        if len(parts) >= 2:
            name = parts[0]
        else:
            name = domain
        
        # Capitalize
        return name.title()
    
    def extract_all(self, text: str, urls: Optional[List[str]] = None) -> List[ExtractedProduct]:
        """
        Extract all URLs including non-product ones.
        
        Args:
            text: Tweet text
            urls: Pre-extracted URLs
            
        Returns:
            All ExtractedProduct objects (including non-products)
        """
        all_urls = set()
        
        if urls:
            all_urls.update(urls)
        
        text_urls = self._extract_urls_from_text(text)
        all_urls.update(text_urls)
        
        products = []
        for url in all_urls:
            product = self._analyze_url(url)
            if product:
                products.append(product)
        
        return products


# Singleton instance
url_extractor = URLExtractor()
