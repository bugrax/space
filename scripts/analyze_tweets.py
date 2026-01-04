"""
Script to analyze tweets from Apify and extract SaaS ideas.
Uses RevenueExtractor and URLExtractor from saas_finder.

Usage:
    python scripts/analyze_tweets.py [--limit N] [--query "search term"]
"""
import argparse
import json
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from apify_client import ApifyClient
from saas_finder.extractors.revenue import RevenueExtractor
from saas_finder.extractors.urls import URLExtractor
from saas_finder.config import config


def main():
    parser = argparse.ArgumentParser(description="Analyze tweets and extract SaaS ideas")
    parser.add_argument("--limit", type=int, default=20, help="Max tweets to fetch (capped at 100)")
    parser.add_argument("--query", type=str, default="$10k MRR", help="Search query")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (max 120)")
    parser.add_argument("--output", type=str, default="data/extracted_ideas.json", help="Output file")
    args = parser.parse_args()
    
    # SAFETY: Hard caps to prevent runaway costs
    args.limit = min(args.limit, 100)  # Max 100 tweets
    args.timeout = min(args.timeout, 120)  # Max 2 minutes
    
    # Get API token from config or env
    api_token = config.scraper.apify_api_token or os.environ.get("APIFY_API_TOKEN")
    if not api_token:
        print("Error: APIFY_API_TOKEN not set")
        sys.exit(1)
    
    client = ApifyClient(api_token)
    revenue_extractor = RevenueExtractor()
    url_extractor = URLExtractor()
    
    print(f"Searching: '{args.query}' (limit: {args.limit}, timeout: {args.timeout}s)")
    
    # Run search with strict limits
    run_input = {
        "searchTerms": [args.query],
        "maxTweets": args.limit,
        "maxItems": args.limit,  # Additional safeguard
        "sort": "Latest",
    }
    
    try:
        run = client.actor("apidojo/tweet-scraper").call(
            run_input=run_input,
            timeout_secs=args.timeout,
            memory_mbytes=256,  # Limit memory to control costs
        )
        print(f"Run completed: {run['status']}")
        dataset_id = run["defaultDatasetId"]
    except Exception as e:
        print(f"Run error: {e}")
        print("NOT falling back to previous runs - this could be expensive!")
        sys.exit(1)
            print(f"Using last run dataset: {dataset_id}")
        else:
            print("No runs found")
            sys.exit(1)
    
    # Load results
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"Loaded {len(items)} tweets")
    
    if not items or (len(items) == 1 and items[0].get("noResults")):
        print("No results found")
        sys.exit(1)
    
    # Process tweets
    ideas = []
    for item in items:
        text = item.get("fullText", "") or item.get("text", "")
        if not text:
            continue
        
        revenue = revenue_extractor.extract(text)
        if not revenue:
            continue
        
        author = item.get("author", {})
        username = author.get("userName", "") or author.get("username", "unknown")
        followers = author.get("followers", 0)
        
        entities = item.get("entities", {})
        urls_data = entities.get("urls", [])
        urls = [u.get("expanded_url") or u.get("url", "") for u in urls_data if isinstance(u, dict)]
        
        products = url_extractor.extract("", urls)
        product_url = products[0].url if products else None
        
        idea = {
            "username": username,
            "followers": followers,
            "text": text[:300],
            "revenue": {
                "type": revenue.type.value,
                "amount": revenue.amount,
                "normalized_monthly": revenue.amount if revenue.type.value in ["MRR", "MONTHLY"] else revenue.amount / 12,
                "confidence": revenue.confidence
            },
            "product_url": product_url,
            "tweet_id": item.get("id"),
            "likes": item.get("likeCount", 0),
            "retweets": item.get("retweetCount", 0),
        }
        ideas.append(idea)
    
    # Sort by revenue
    ideas.sort(key=lambda x: x["revenue"]["normalized_monthly"] or 0, reverse=True)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"EXTRACTED {len(ideas)} SAAS IDEAS WITH REVENUE MENTIONS")
    print(f"{'='*60}\n")
    
    for i, idea in enumerate(ideas[:20], 1):
        rev = idea["revenue"]
        monthly = rev["normalized_monthly"]
        monthly_str = f"${monthly:,.0f}/mo" if monthly else "N/A"
        
        print(f"{i}. @{idea['username']} ({idea['followers']:,} followers)")
        print(f"   Revenue: {rev['type']} ${rev['amount']:,.0f} → {monthly_str}")
        print(f"   Confidence: {rev['confidence']:.0%}")
        if idea['product_url']:
            print(f"   Product: {idea['product_url']}")
        print(f"   Tweet: {idea['text'][:150]}...")
        print(f"   Engagement: {idea['likes']} likes, {idea['retweets']} RTs")
        print()
    
    # Summary
    total_mrr = sum(i["revenue"]["normalized_monthly"] or 0 for i in ideas)
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total ideas found: {len(ideas)}")
    print(f"With product URL: {sum(1 for i in ideas if i['product_url'])}")
    print(f"Combined monthly revenue: ${total_mrr:,.0f}")
    if ideas:
        print(f"Average monthly revenue: ${total_mrr/len(ideas):,.0f}")
    
    # Save to file
    output_path = os.path.join(PROJECT_ROOT, args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(ideas, f, indent=2, default=str)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
