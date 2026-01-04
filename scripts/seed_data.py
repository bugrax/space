"""
Seed sample data for testing the dashboard.

Usage:
    python scripts/seed_data.py
"""
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime, timedelta
from saas_finder.storage.database import Database
from saas_finder.scoring.scorer import SaaSIdea, ScoringResult, TrafficData, ReplicabilityLevel, ProductComplexity

# Initialize database
db = Database()


def make_score(traction, growth, traffic, simplicity):
    """Helper to create ScoringResult."""
    return ScoringResult(
        total_score=traction + growth + traffic + simplicity,
        traction_score=traction,
        growth_score=growth,
        traffic_score=traffic,
        simplicity_score=simplicity
    )


# Sample ideas
SAMPLE_IDEAS = [
    SaaSIdea(
        tweet_id="1001",
        tweet_text="Just hit $5K MRR with my micro-SaaS! 🚀 Building a simple invoice generator for freelancers. No VC, no team, just me and my laptop. #buildinpublic",
        tweet_url="https://twitter.com/solofounder/status/1001",
        author_username="solofounder",
        author_followers=12500,
        product_name="InvoiceSimple",
        product_url="https://invoicesimple.io",
        product_domain="invoicesimple.io",
        reported_mrr=5000,
        revenue_confidence=0.9,
        likes=245, retweets=42, replies=18, impressions=10000,
        tweet_date=datetime.now() - timedelta(days=2),
        date_found=datetime.now(),
        score=make_score(25, 20, 18, 16),
        replicability=ReplicabilityLevel.HIGH,
        replicability_note="Simple invoicing tool with clear value prop. Easy to replicate with modern frameworks.",
        complexity=ProductComplexity.SIMPLE_SAAS,
        category="Finance"
    ),
    SaaSIdea(
        tweet_id="1002",
        tweet_text="$12K MRR 🎉 My AI writing assistant is growing 30% MoM. Started as a weekend project, now my full-time gig! https://writeassist.ai #indiehackers #saas",
        tweet_url="https://twitter.com/aibuilder/status/1002",
        author_username="aibuilder",
        author_followers=28000,
        product_name="WriteAssist",
        product_url="https://writeassist.ai",
        product_domain="writeassist.ai",
        reported_mrr=12000,
        revenue_confidence=0.85,
        likes=512, retweets=89, replies=47, impressions=22000,
        tweet_date=datetime.now() - timedelta(days=1),
        date_found=datetime.now(),
        score=make_score(28, 23, 20, 12),
        replicability=ReplicabilityLevel.MEDIUM,
        replicability_note="AI writing market is competitive but still has niches. Need good prompting skills.",
        complexity=ProductComplexity.COMPLEX_SAAS,
        category="AI/ML",
        traffic=TrafficData(organic_percent=45, paid_percent=15, social_percent=30, direct_percent=10)
    ),
    SaaSIdea(
        tweet_id="1003",
        tweet_text="My bookmark manager just crossed $2K MRR! Clean design + fast search = happy users. Still bootstrapped! #buildinpublic",
        tweet_url="https://twitter.com/designdev/status/1003",
        author_username="designdev",
        author_followers=8500,
        product_name="QuickMarks",
        product_url="https://quickmarks.app",
        product_domain="quickmarks.app",
        reported_mrr=2000,
        revenue_confidence=0.8,
        likes=156, retweets=23, replies=12, impressions=7000,
        tweet_date=datetime.now() - timedelta(days=3),
        date_found=datetime.now(),
        score=make_score(18, 15, 14, 18),
        replicability=ReplicabilityLevel.HIGH,
        replicability_note="Bookmark managers are straightforward to build. Focus on UX to differentiate.",
        complexity=ProductComplexity.SIMPLE_SAAS,
        category="Productivity"
    ),
    SaaSIdea(
        tweet_id="1004",
        tweet_text="Newsletter analytics tool at $8.5K MRR! Helping creators understand their audience. Open rates, click maps, subscriber insights. https://mailmetrics.co #saas",
        tweet_url="https://twitter.com/mailguru/status/1004",
        author_username="mailguru",
        author_followers=15200,
        product_name="MailMetrics",
        product_url="https://mailmetrics.co",
        product_domain="mailmetrics.co",
        reported_mrr=8500,
        revenue_confidence=0.85,
        likes=287, retweets=45, replies=23, impressions=12000,
        tweet_date=datetime.now() - timedelta(days=4),
        date_found=datetime.now(),
        score=make_score(24, 19, 17, 14),
        replicability=ReplicabilityLevel.MEDIUM,
        replicability_note="Email analytics requires integrations with major providers. Technical but doable.",
        complexity=ProductComplexity.COMPLEX_SAAS,
        category="Marketing",
        traffic=TrafficData(organic_percent=35, paid_percent=25, social_percent=25, direct_percent=15)
    ),
    SaaSIdea(
        tweet_id="1005",
        tweet_text="Hit $1.5K MRR with my habit tracker! 🎯 Simple UI, push notifications, streaks. No fancy features, just what works. #indiehackers",
        tweet_url="https://twitter.com/habithacker/status/1005",
        author_username="habithacker",
        author_followers=5200,
        product_name="HabitFlow",
        product_url="https://habitflow.app",
        product_domain="habitflow.app",
        reported_mrr=1500,
        revenue_confidence=0.75,
        likes=98, retweets=14, replies=8, impressions=4200,
        tweet_date=datetime.now() - timedelta(days=5),
        date_found=datetime.now(),
        score=make_score(15, 12, 10, 20),
        replicability=ReplicabilityLevel.HIGH,
        replicability_note="Habit trackers are beginner-friendly. Many exist but room for better UX.",
        complexity=ProductComplexity.SINGLE_FEATURE,
        category="Productivity",
        traffic=TrafficData(organic_percent=20, paid_percent=10, social_percent=50, direct_percent=20)
    ),
    SaaSIdea(
        tweet_id="1006",
        tweet_text="$25K ARR! 🚀 My API monitoring tool is growing. Uptime checks, latency tracking, Slack alerts. B2B SaaS is where it's at! https://apiwatch.dev",
        tweet_url="https://twitter.com/devopsdan/status/1006",
        author_username="devopsdan",
        author_followers=22000,
        product_name="APIWatch",
        product_url="https://apiwatch.dev",
        product_domain="apiwatch.dev",
        reported_mrr=2083,  # ARR/12
        revenue_confidence=0.9,
        likes=345, retweets=67, replies=34, impressions=15000,
        tweet_date=datetime.now() - timedelta(days=6),
        date_found=datetime.now(),
        score=make_score(20, 18, 20, 10),
        replicability=ReplicabilityLevel.MEDIUM,
        replicability_note="API monitoring is technical but well-documented space. Good B2B potential.",
        complexity=ProductComplexity.COMPLEX_SAAS,
        category="Developer Tools",
        traffic=TrafficData(organic_percent=55, paid_percent=5, social_percent=20, direct_percent=20)
    ),
    SaaSIdea(
        tweet_id="1007",
        tweet_text="Just launched my Chrome extension for reading time estimates. Already at $800 MRR in week 2! 📚 https://readtime.co #buildinpublic",
        tweet_url="https://twitter.com/readaholic/status/1007",
        author_username="readaholic",
        author_followers=3200,
        product_name="ReadTime",
        product_url="https://readtime.co",
        product_domain="readtime.co",
        reported_mrr=800,
        revenue_confidence=0.7,
        likes=67, retweets=12, replies=5, impressions=2800,
        tweet_date=datetime.now() - timedelta(days=1),
        date_found=datetime.now(),
        score=make_score(12, 22, 8, 18),
        replicability=ReplicabilityLevel.HIGH,
        replicability_note="Browser extensions are great for quick MVPs. Low barrier to entry.",
        complexity=ProductComplexity.SINGLE_FEATURE,
        category="Productivity"
    ),
    SaaSIdea(
        tweet_id="1008",
        tweet_text="$18K MRR with my social media scheduler! 📱 Supports Twitter, LinkedIn, and now Threads. Growing 15% monthly. #saas #indiehackers",
        tweet_url="https://twitter.com/socialpro/status/1008",
        author_username="socialpro",
        author_followers=45000,
        product_name="PostQueue",
        product_url="https://postqueue.io",
        product_domain="postqueue.io",
        reported_mrr=18000,
        revenue_confidence=0.9,
        likes=678, retweets=123, replies=67, impressions=32000,
        tweet_date=datetime.now() - timedelta(days=3),
        date_found=datetime.now(),
        score=make_score(30, 20, 22, 8),
        replicability=ReplicabilityLevel.LOW,
        replicability_note="Social media schedulers require multiple API integrations. Competitive market.",
        complexity=ProductComplexity.PLATFORM,
        category="Marketing",
        traffic=TrafficData(organic_percent=40, paid_percent=30, social_percent=20, direct_percent=10)
    ),
]


def main():
    """Seed sample data into database."""
    print("🌱 Seeding sample data...")
    new_count, updated_count = db.save_ideas(SAMPLE_IDEAS)
    print(f"✅ Added {new_count} new ideas, updated {updated_count} existing")

    # Show stats
    stats = db.get_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Total Ideas: {stats['total_ideas']}")
    print(f"   With MRR: {stats['with_mrr']}")
    print(f"   High Score: {stats['high_score_ideas']}")
    print(f"   Avg MRR: ${stats['average_mrr']:,.0f}")
    print(f"   Avg Score: {stats['average_score']:.1f}")


if __name__ == "__main__":
    main()
