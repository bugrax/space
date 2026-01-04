"""
Celery tasks for Twitter crawling and data processing.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from .celery_app import celery_app
from .storage.database import Database
from .twitter.client import MockTwitterClient
from .twitter.nitter_scraper import NitterClient
from .finder import SaaSIdeaFinder
from .scoring.scorer import IdeaScorer

# Task logger
logger = get_task_logger(__name__)

# Initialize shared resources
db = Database()

# Check if we should use mock client (for testing)
USE_MOCK = os.getenv("USE_MOCK_TWITTER", "false").lower() == "true"


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.scan_revenue_tweets",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def scan_revenue_tweets(self, days: int = 1, max_results: int = 100):
    """
    Scan Twitter for revenue-related tweets using Nitter scraper.
    
    This task searches for tweets mentioning MRR, ARR, revenue figures.
    """
    logger.info(f"Starting revenue tweet scan (days={days}, max_results={max_results})")
    
    try:
        # Use Nitter for scraping (no API needed)
        finder = SaaSIdeaFinder(use_mock=USE_MOCK, use_nitter=not USE_MOCK)
        
        # Search for revenue-related tweets
        ideas = finder.search(
            query="MRR OR ARR OR revenue",
            days=days,
            max_results=max_results,
            min_mrr=0
        )
        
        # Save to database
        new_count, updated_count = db.save_ideas(ideas)
        
        # Log search history
        db.log_search(
            query="MRR OR ARR OR revenue",
            results_count=len(ideas),
            new_ideas_count=new_count
        )
        
        result = {
            "task": "scan_revenue_tweets",
            "timestamp": datetime.utcnow().isoformat(),
            "total_found": len(ideas),
            "new_saved": new_count,
            "updated": updated_count,
            "status": "success"
        }
        
        logger.info(f"Revenue scan complete: {new_count} new, {updated_count} updated")
        return result
        
    except Exception as e:
        logger.error(f"Revenue scan failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.scan_hashtags",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def scan_hashtags(self, hashtags: list[str], days: int = 1, max_results: int = 50):
    """
    Scan Twitter for specific hashtags using Nitter scraper.
    
    Popular hashtags: #buildinpublic, #indiehackers, #saas, #microsaas
    """
    logger.info(f"Starting hashtag scan: {hashtags}")
    
    try:
        finder = SaaSIdeaFinder(use_mock=USE_MOCK, use_nitter=not USE_MOCK)
        
        total_found = 0
        total_new = 0
        total_updated = 0
        
        for hashtag in hashtags:
            logger.info(f"Scanning #{hashtag}...")
            
            # Build query
            query = f"#{hashtag} (MRR OR ARR OR revenue OR launched OR \"making money\")"
            
            ideas = finder.search(
                query=query,
                days=days,
                max_results=max_results,
                min_mrr=0
            )
            
            new_count, updated_count = db.save_ideas(ideas)
            
            total_found += len(ideas)
            total_new += new_count
            total_updated += updated_count
            
            # Log each hashtag search
            db.log_search(
                query=f"#{hashtag}",
                hashtags=[hashtag],
                results_count=len(ideas),
                new_ideas_count=new_count
            )
        
        result = {
            "task": "scan_hashtags",
            "timestamp": datetime.utcnow().isoformat(),
            "hashtags": hashtags,
            "total_found": total_found,
            "new_saved": total_new,
            "updated": total_updated,
            "status": "success"
        }
        
        logger.info(f"Hashtag scan complete: {total_new} new, {total_updated} updated")
        return result
        
    except Exception as e:
        logger.error(f"Hashtag scan failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.deep_scan",
    max_retries=2,
    default_retry_delay=300,
    time_limit=600  # 10 minutes for deep scan
)
def deep_scan(self, days: int = 7, max_results: int = 500):
    """
    Perform a comprehensive deep scan of Twitter.
    
    This task runs less frequently but searches more thoroughly.
    """
    logger.info(f"Starting deep scan (days={days}, max_results={max_results})")
    
    try:
        finder = SaaSIdeaFinder(use_mock=True)  # TODO: Set to False in production
        
        # Multiple search queries for comprehensive coverage
        queries = [
            # Revenue mentions
            "\"$\" MRR -filter:retweets",
            "\"$\" ARR -filter:retweets",
            "hit revenue milestone",
            "crossed MRR",
            "making money online SaaS",
            
            # Build in public
            "#buildinpublic revenue",
            "#buildinpublic MRR",
            "#buildinpublic launched",
            
            # Indie hackers
            "#indiehackers MRR",
            "#indiehackers revenue",
            "#indiehackers launched",
            
            # SaaS specific
            "micro-SaaS revenue",
            "bootstrapped SaaS MRR",
            "solo founder revenue",
            
            # Milestone announcements
            "first paying customer",
            "reached $1k MRR",
            "reached $5k MRR",
            "reached $10k MRR",
        ]
        
        total_found = 0
        total_new = 0
        total_updated = 0
        
        for query in queries:
            logger.info(f"Deep scanning: {query[:50]}...")
            
            try:
                ideas = finder.search(
                    query=query,
                    days=days,
                    max_results=max_results // len(queries),
                    min_mrr=0
                )
                
                new_count, updated_count = db.save_ideas(ideas)
                
                total_found += len(ideas)
                total_new += new_count
                total_updated += updated_count
                
            except Exception as e:
                logger.warning(f"Query failed: {query[:50]}... Error: {e}")
                continue
        
        # Log the deep scan
        db.log_search(
            query="deep_scan",
            keywords=queries[:5],  # First 5 for reference
            results_count=total_found,
            new_ideas_count=total_new
        )
        
        result = {
            "task": "deep_scan",
            "timestamp": datetime.utcnow().isoformat(),
            "queries_run": len(queries),
            "total_found": total_found,
            "new_saved": total_new,
            "updated": total_updated,
            "status": "success"
        }
        
        logger.info(f"Deep scan complete: {total_new} new ideas from {total_found} tweets")
        return result
        
    except Exception as e:
        logger.error(f"Deep scan failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.rescore_ideas",
    max_retries=1
)
def rescore_ideas(self, min_age_hours: int = 24):
    """
    Rescore existing ideas that haven't been updated recently.
    
    This helps keep scores fresh as engagement metrics change.
    """
    logger.info(f"Starting rescore task (min_age={min_age_hours}h)")
    
    try:
        scorer = IdeaScorer()
        
        # Get ideas that need rescoring
        cutoff = datetime.utcnow() - timedelta(hours=min_age_hours)
        ideas = db.list_ideas(limit=100)  # Get recent ideas
        
        rescored_count = 0
        
        for idea_dict in ideas:
            # TODO: Implement rescoring logic when we have traffic data API
            # For now, just log
            pass
        
        result = {
            "task": "rescore_ideas",
            "timestamp": datetime.utcnow().isoformat(),
            "rescored": rescored_count,
            "status": "success"
        }
        
        logger.info(f"Rescore complete: {rescored_count} ideas updated")
        return result
        
    except Exception as e:
        logger.error(f"Rescore failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.cleanup_old_data",
    max_retries=1
)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Clean up old data to prevent database bloat.
    
    Removes:
    - Old search history
    - Low-score ideas older than threshold
    """
    logger.info(f"Starting cleanup (keeping {days_to_keep} days)")
    
    try:
        # This would need database methods to implement properly
        # For now, just log the intent
        
        result = {
            "task": "cleanup_old_data",
            "timestamp": datetime.utcnow().isoformat(),
            "days_kept": days_to_keep,
            "status": "success"
        }
        
        logger.info("Cleanup complete")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="saas_finder.tasks.scan_founder",
    max_retries=3,
    default_retry_delay=30
)
def scan_founder(self, username: str, days: int = 30):
    """
    Scan a specific founder's tweets for revenue updates.
    
    Used for watchlist functionality.
    """
    logger.info(f"Scanning founder: @{username}")
    
    try:
        finder = SaaSIdeaFinder(use_mock=True)
        
        query = f"from:{username} (MRR OR ARR OR revenue OR launched)"
        
        ideas = finder.search(
            query=query,
            days=days,
            max_results=50,
            min_mrr=0
        )
        
        new_count, updated_count = db.save_ideas(ideas)
        
        result = {
            "task": "scan_founder",
            "timestamp": datetime.utcnow().isoformat(),
            "founder": username,
            "total_found": len(ideas),
            "new_saved": new_count,
            "status": "success"
        }
        
        logger.info(f"Founder scan complete: @{username} - {new_count} new ideas")
        return result
        
    except Exception as e:
        logger.error(f"Founder scan failed for @{username}: {e}")
        raise


# ==================== Utility Tasks ====================

@celery_app.task(name="saas_finder.tasks.health_check")
def health_check():
    """Simple health check task."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db else "disconnected"
    }


@celery_app.task(name="saas_finder.tasks.trigger_manual_scan")
def trigger_manual_scan(
    query: Optional[str] = None,
    hashtags: Optional[list[str]] = None,
    days: int = 7,
    max_results: int = 100
):
    """
    Trigger a manual scan from the API/UI.
    
    This allows users to run custom scans on demand.
    """
    logger.info(f"Manual scan triggered: query={query}, hashtags={hashtags}")
    
    try:
        finder = SaaSIdeaFinder(use_mock=True)
        
        if hashtags:
            # Build hashtag query
            hashtag_query = " OR ".join([f"#{tag}" for tag in hashtags])
            search_query = f"({hashtag_query}) (MRR OR ARR OR revenue)"
        elif query:
            search_query = query
        else:
            search_query = "MRR OR ARR OR revenue"
        
        ideas = finder.search(
            query=search_query,
            days=days,
            max_results=max_results,
            min_mrr=0
        )
        
        new_count, updated_count = db.save_ideas(ideas)
        
        # Log the manual search
        db.log_search(
            query=search_query,
            hashtags=hashtags,
            results_count=len(ideas),
            new_ideas_count=new_count
        )
        
        return {
            "task": "manual_scan",
            "timestamp": datetime.utcnow().isoformat(),
            "query": search_query,
            "total_found": len(ideas),
            "new_saved": new_count,
            "updated": updated_count,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        return {
            "task": "manual_scan",
            "status": "failed",
            "error": str(e)
        }
