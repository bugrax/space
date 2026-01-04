"""
Revenue Extractor - Extract MRR/ARR/Revenue figures from tweet text.

Patterns detected:
- $10,000 MRR / $10K MRR
- $10,000 ARR / $10K ARR
- $10,000/month / $10K per month
- "hit $10K" / "crossed $50,000"
- "5 figure MRR" / "6 figure ARR"
- Stripe screenshot indicators
"""

import re
from typing import Optional, List, Tuple

from saas_finder.twitter.models import ExtractedRevenue, RevenueType


class RevenueExtractor:
    """Extract MRR/ARR/Revenue figures from tweet text."""
    
    # Regex patterns for revenue detection
    # Format: (pattern, revenue_type, base_confidence)
    PATTERNS = [
        # $10,000 MRR, $10K MRR, $10k mrr
        (r'\$\s*([\d,]+\.?\d*)\s*([kK])?\s*(MRR|mrr)', RevenueType.MRR, 0.95),
        
        # $10,000 ARR, $10K ARR
        (r'\$\s*([\d,]+\.?\d*)\s*([kK])?\s*(ARR|arr)', RevenueType.ARR, 0.95),
        
        # $10,000/month, $10K per month, $10k monthly, $10K/mo
        (r'\$\s*([\d,]+\.?\d*)\s*([kK])?\s*(?:/month|per\s*month|monthly|/mo\b)', RevenueType.MONTHLY, 0.90),
        
        # "making $5,000", "hit $10K", "crossed $50,000", "reached $20k"
        (r'(?:making|hit|crossed|reached|at)\s*\$\s*([\d,]+\.?\d*)\s*([kK])?', RevenueType.UNKNOWN, 0.75),
        
        # "10K MRR", "50k in revenue"
        (r'([\d,]+\.?\d*)\s*([kK])\s*(?:MRR|in\s*revenue|revenue)', RevenueType.MRR, 0.80),
        
        # "$5,000 in monthly revenue"
        (r'\$\s*([\d,]+\.?\d*)\s*([kK])?\s*(?:in\s*)?(?:monthly\s*)?revenue', RevenueType.MONTHLY, 0.85),
        
        # "5 figure MRR", "6 figure ARR"
        (r'([4-7])\s*figure\s*(MRR|ARR|revenue)', RevenueType.UNKNOWN, 0.70),
        
        # Just passed $X, Now at $X
        (r'(?:just\s*passed|now\s*at|currently\s*at)\s*\$\s*([\d,]+\.?\d*)\s*([kK])?', RevenueType.UNKNOWN, 0.70),
        
        # Growing to $X MRR, scaled to $X
        (r'(?:growing\s*to|scaled\s*to|grew\s*to)\s*\$\s*([\d,]+\.?\d*)\s*([kK])?\s*(?:MRR)?', RevenueType.MRR, 0.75),
        
        # $X/mo, $X per mo (shorter form)
        (r'\$\s*([\d,]+\.?\d*)\s*([kK])?\s*/mo\b', RevenueType.MONTHLY, 0.85),
        
        # Revenue: $X, MRR: $X
        (r'(?:revenue|mrr|arr)\s*:\s*\$\s*([\d,]+\.?\d*)\s*([kK])?', RevenueType.MRR, 0.90),
        
        # From $0 to $X
        (r'from\s*\$0\s*to\s*\$\s*([\d,]+\.?\d*)\s*([kK])?', RevenueType.UNKNOWN, 0.70),
    ]
    
    # Figure estimates (for "X figure" patterns)
    FIGURE_ESTIMATES = {
        '4': 5000,      # 4 figures = ~$5,000
        '5': 50000,     # 5 figures = ~$50,000  
        '6': 500000,    # 6 figures = ~$500,000
        '7': 5000000,   # 7 figures = ~$5,000,000
    }
    
    # Screenshot indicators - boost confidence if present
    SCREENSHOT_KEYWORDS = [
        'screenshot', 'proof', 'stripe', 'dashboard',
        'pic', 'image', 'attached', 'below', 'stats',
        '👇', '📊', '📈', '💰', '🚀', '💵'
    ]
    
    def extract(self, text: str) -> Optional[ExtractedRevenue]:
        """
        Extract revenue information from text.
        Returns the highest confidence match.
        
        Args:
            text: Tweet text to analyze
            
        Returns:
            ExtractedRevenue or None if no revenue found
        """
        if not text:
            return None
        
        best_match: Optional[ExtractedRevenue] = None
        best_confidence = 0.0
        
        for pattern, revenue_type, base_confidence in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    amount, confidence = self._parse_match(match, base_confidence)
                    
                    if amount is None or amount <= 0:
                        continue
                    
                    # Boost confidence for screenshot indicators
                    has_screenshot = self._check_screenshot_indicators(text)
                    if has_screenshot:
                        confidence = min(confidence + 0.1, 1.0)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = ExtractedRevenue(
                            raw_match=match.group(0),
                            amount=amount,
                            type=revenue_type,
                            confidence=confidence,
                            has_screenshot=has_screenshot
                        )
                        
                except Exception:
                    continue
        
        return best_match
    
    def _parse_match(self, match: re.Match, base_confidence: float) -> Tuple[Optional[int], float]:
        """Parse regex match to extract amount."""
        groups = match.groups()
        
        # Handle "X figure" pattern
        if 'figure' in match.group(0).lower():
            figure = groups[0]
            amount = self.FIGURE_ESTIMATES.get(figure, 0)
            return amount, base_confidence
        
        # Extract number
        num_str = groups[0].replace(',', '')
        
        try:
            amount = float(num_str)
        except ValueError:
            return None, 0.0
        
        # Check for K multiplier
        k_multiplier = groups[1] if len(groups) > 1 else None
        if k_multiplier and k_multiplier.lower() == 'k':
            amount *= 1000
        
        # Sanity checks
        if amount <= 0:
            return None, 0.0
        
        # Very high amounts might be typos or different context
        if amount > 100_000_000:  # $100M seems unreasonable for #buildinpublic
            return None, 0.0
        
        return int(amount), base_confidence
    
    def _check_screenshot_indicators(self, text: str) -> bool:
        """Check if tweet mentions a screenshot or contains image indicators."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.SCREENSHOT_KEYWORDS)
    
    def extract_all(self, text: str) -> List[ExtractedRevenue]:
        """
        Extract all revenue mentions (not just the best one).
        
        Useful for analyzing tweets that mention multiple revenue figures.
        
        Args:
            text: Tweet text to analyze
            
        Returns:
            List of ExtractedRevenue sorted by confidence
        """
        if not text:
            return []
        
        results = []
        seen_amounts = set()  # Avoid duplicates
        has_screenshot = self._check_screenshot_indicators(text)
        
        for pattern, revenue_type, base_confidence in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    amount, confidence = self._parse_match(match, base_confidence)
                    
                    if amount is None or amount <= 0:
                        continue
                    
                    # Skip if we've already seen this amount
                    if amount in seen_amounts:
                        continue
                    seen_amounts.add(amount)
                    
                    if has_screenshot:
                        confidence = min(confidence + 0.1, 1.0)
                    
                    results.append(ExtractedRevenue(
                        raw_match=match.group(0),
                        amount=amount,
                        type=revenue_type,
                        confidence=confidence,
                        has_screenshot=has_screenshot
                    ))
                        
                except Exception:
                    continue
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def is_revenue_tweet(self, text: str, min_confidence: float = 0.5) -> bool:
        """
        Quick check if a tweet contains revenue information.
        
        Args:
            text: Tweet text
            min_confidence: Minimum confidence threshold
            
        Returns:
            True if tweet likely contains revenue info
        """
        result = self.extract(text)
        return result is not None and result.confidence >= min_confidence


# Singleton instance for convenience
revenue_extractor = RevenueExtractor()
