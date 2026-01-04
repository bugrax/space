"""
MRR/Revenue parser for extracting revenue data from tweet text.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RevenueType(str, Enum):
    """Type of revenue metric."""
    MRR = "MRR"
    ARR = "ARR"
    MONTHLY = "monthly"
    REVENUE = "revenue"
    UNKNOWN = "unknown"


@dataclass
class RevenueData:
    """Extracted revenue information."""
    amount: float
    type: RevenueType
    raw_text: str
    confidence: float  # 0.0 to 1.0
    
    @property
    def monthly_equivalent(self) -> float:
        """Convert to monthly equivalent."""
        if self.type == RevenueType.ARR:
            return self.amount / 12
        return self.amount
    
    def __str__(self) -> str:
        return f"${self.amount:,.0f} {self.type.value}"


class MRRParser:
    """
    Parser for extracting MRR, ARR, and revenue data from text.
    
    Handles various formats:
    - "$5,000 MRR"
    - "$10K MRR"
    - "10k/month"
    - "$50k ARR"
    - "$5000/mo"
    - "5K per month"
    - "$10,000 monthly revenue"
    """
    
    # Patterns for matching revenue mentions
    PATTERNS = [
        # $X,XXX MRR/ARR format
        (
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?\s*(MRR|ARR)',
            lambda m: (
                MRRParser._parse_amount(m.group(1), 'k' in m.group(0).lower() and 'k' not in m.group(1).lower()),
                RevenueType.MRR if m.group(2).upper() == 'MRR' else RevenueType.ARR,
                0.95
            )
        ),
        # $XK MRR/ARR format (e.g., "$10K MRR")
        (
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]\s*(MRR|ARR)',
            lambda m: (
                MRRParser._parse_amount(m.group(1), True),
                RevenueType.MRR if m.group(2).upper() == 'MRR' else RevenueType.ARR,
                0.95
            )
        ),
        # $X,XXX/month or /mo format
        (
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?\s*(?:/month|/mo\b|per\s+month)',
            lambda m: (
                MRRParser._parse_amount(m.group(1), 'k' in m.group(0).lower() and 'k' not in m.group(1).lower()),
                RevenueType.MONTHLY,
                0.90
            )
        ),
        # XK/month format (without $)
        (
            r'([\d,]+(?:\.\d+)?)\s*[kK]\s*(?:/month|/mo\b|per\s+month)',
            lambda m: (
                MRRParser._parse_amount(m.group(1), True),
                RevenueType.MONTHLY,
                0.75
            )
        ),
        # $X,XXX monthly revenue
        (
            r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?\s*(?:monthly\s+)?revenue',
            lambda m: (
                MRRParser._parse_amount(m.group(1), 'k' in m.group(0).lower() and 'k' not in m.group(1).lower()),
                RevenueType.REVENUE,
                0.80
            )
        ),
        # "hit/reached/crossed $X,XXX" near MRR/ARR context
        (
            r'(?:hit|reached|crossed|passed)\s+\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?',
            lambda m: (
                MRRParser._parse_amount(m.group(1), 'k' in m.group(0).lower() and 'k' not in m.group(1).lower()),
                RevenueType.UNKNOWN,
                0.70
            )
        ),
        # "making $X,XXX" pattern
        (
            r'making\s+\$\s*([\d,]+(?:\.\d+)?)\s*[kK]?\s*(?:/month|/mo\b|per\s+month|monthly)?',
            lambda m: (
                MRRParser._parse_amount(m.group(1), 'k' in m.group(0).lower() and 'k' not in m.group(1).lower()),
                RevenueType.MONTHLY,
                0.75
            )
        ),
        # X paying customers at $Y pattern (calculate MRR)
        (
            r'(\d+)\s+paying\s+customers?\s+(?:at\s+)?\$\s*([\d,]+(?:\.\d+)?)',
            lambda m: (
                int(m.group(1).replace(',', '')) * float(m.group(2).replace(',', '')),
                RevenueType.MRR,
                0.65
            )
        ),
    ]
    
    @staticmethod
    def _parse_amount(amount_str: str, multiply_k: bool = False) -> float:
        """
        Parse amount string to float.
        
        Args:
            amount_str: String like "5,000" or "10"
            multiply_k: Whether to multiply by 1000
        
        Returns:
            Parsed amount as float
        """
        # Remove commas
        cleaned = amount_str.replace(',', '')
        amount = float(cleaned)
        
        if multiply_k:
            amount *= 1000
        
        return amount
    
    def parse(self, text: str) -> list[RevenueData]:
        """
        Parse text and extract all revenue mentions.
        
        Args:
            text: Tweet text to parse
        
        Returns:
            List of RevenueData objects found
        """
        results = []
        text_lower = text.lower()
        
        for pattern, extractor in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    amount, rev_type, confidence = extractor(match)
                    
                    # Skip very small amounts (likely not revenue)
                    if amount < 100:
                        continue
                    
                    # Boost confidence if context supports it
                    if rev_type == RevenueType.UNKNOWN:
                        if 'mrr' in text_lower:
                            rev_type = RevenueType.MRR
                            confidence += 0.1
                        elif 'arr' in text_lower:
                            rev_type = RevenueType.ARR
                            confidence += 0.1
                        elif any(kw in text_lower for kw in ['month', 'monthly', '/mo']):
                            rev_type = RevenueType.MONTHLY
                            confidence += 0.05
                    
                    # Cap confidence at 1.0
                    confidence = min(confidence, 1.0)
                    
                    results.append(RevenueData(
                        amount=amount,
                        type=rev_type,
                        raw_text=match.group(0),
                        confidence=confidence
                    ))
                    
                except (ValueError, IndexError):
                    continue
        
        # Deduplicate by similar amounts (within 10% of each other)
        results = self._deduplicate(results)
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def _deduplicate(self, results: list[RevenueData]) -> list[RevenueData]:
        """
        Remove duplicate or very similar revenue mentions.
        
        Keeps the one with highest confidence when amounts are within 10%.
        """
        if len(results) <= 1:
            return results
        
        unique = []
        for result in sorted(results, key=lambda x: x.confidence, reverse=True):
            is_duplicate = False
            for existing in unique:
                # Check if amounts are within 10% of each other
                if existing.amount > 0:
                    ratio = abs(result.amount - existing.amount) / existing.amount
                    if ratio < 0.1:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique.append(result)
        
        return unique
    
    def get_best_mrr(self, text: str) -> Optional[RevenueData]:
        """
        Get the most likely MRR value from text.
        
        Args:
            text: Tweet text to parse
        
        Returns:
            Best RevenueData match or None
        """
        results = self.parse(text)
        if not results:
            return None
        
        # Prefer MRR type, then MONTHLY, then others
        mrr_results = [r for r in results if r.type == RevenueType.MRR]
        if mrr_results:
            return mrr_results[0]
        
        monthly_results = [r for r in results if r.type == RevenueType.MONTHLY]
        if monthly_results:
            return monthly_results[0]
        
        return results[0]
    
    def has_revenue_mention(self, text: str) -> bool:
        """
        Quick check if text mentions any revenue.
        
        Args:
            text: Tweet text to check
        
        Returns:
            True if any revenue pattern is found
        """
        text_lower = text.lower()
        
        # Quick keyword check first
        keywords = ['mrr', 'arr', 'revenue', '/month', 'per month', '/mo']
        if not any(kw in text_lower for kw in keywords):
            # Check for $ followed by numbers
            if not re.search(r'\$\s*[\d,]+', text):
                return False
        
        return len(self.parse(text)) > 0


# Convenience functions
def parse_mrr(text: str) -> Optional[RevenueData]:
    """
    Parse MRR from text.
    
    Args:
        text: Tweet text
    
    Returns:
        Best RevenueData match or None
    """
    parser = MRRParser()
    return parser.get_best_mrr(text)


def has_revenue(text: str) -> bool:
    """
    Check if text mentions revenue.
    
    Args:
        text: Tweet text
    
    Returns:
        True if revenue is mentioned
    """
    parser = MRRParser()
    return parser.has_revenue_mention(text)
