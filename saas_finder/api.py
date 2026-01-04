"""
FastAPI Backend for SaaS Idea Finder Dashboard
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from saas_finder.storage.database import Database
from saas_finder.config import config
from saas_finder.twitter.scrapers import ScraperManager
from saas_finder.extractors.revenue import revenue_extractor
from saas_finder.extractors.urls import url_extractor
from saas_finder.twitter.models import SaaSIdea
from saas_finder.finder import SaaSIdeaFinder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global scraper manager
scraper_manager: Optional[ScraperManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global scraper_manager
    logger.info("Starting SaaS Idea Finder API...")
    
    # Initialize scraper manager
    scraper_manager = ScraperManager(
        accounts_file=config.scraper.accounts_file,
        apify_token=config.scraper.apify_api_token,
        enable_scweet=config.scraper.enable_scweet,
        rate_limit_delay=config.scraper.rate_limit_delay
    )
    
    # Try to initialize scrapers (non-blocking)
    try:
        await scraper_manager.initialize()
    except Exception as e:
        logger.warning(f"Scraper initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    if scraper_manager:
        await scraper_manager.close()

app = FastAPI(
    title="SaaS Idea Finder API",
    description="API for discovering and analyzing validated SaaS ideas from Twitter",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = Database()

# Request/Response models
class ScanRequest(BaseModel):
    hashtags: List[str] = ["buildinpublic", "indiehackers", "saas"]
    days: int = 7
    max_results: int = 100

class ScrapeRequest(BaseModel):
    queries: Optional[List[str]] = None
    limit_per_query: int = 50
    min_mrr: int = 500

class ScrapeResponse(BaseModel):
    status: str
    tweets_found: int
    ideas_extracted: int
    ideas: List[dict]

class NoteRequest(BaseModel):
    note: str

class ScanResponse(BaseModel):
    total_found: int
    new_saved: int
    status: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "SaaS Idea Finder API"}

@app.get("/api/ideas")
async def list_ideas(
    min_score: int = Query(0, ge=0, le=100),
    category: Optional[str] = None,
    favorites: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """List all discovered SaaS ideas with optional filtering"""
    try:
        # Get all ideas from database
        all_ideas = db.list_ideas(limit=limit * 2)  # Fetch more for filtering
        
        # Apply filters
        filtered_ideas = []
        for idea in all_ideas:
            # Calculate total score
            score_data = idea.get('score', {})
            if isinstance(score_data, dict):
                total_score = (
                    score_data.get('traction', 0) +
                    score_data.get('growth', 0) +
                    score_data.get('traffic', 0) +
                    score_data.get('simplicity', 0)
                )
            else:
                total_score = score_data or 0
            
            # Skip if below minimum score
            if total_score < min_score:
                continue
            
            # Filter by favorites
            if favorites and not idea.get('is_favorited', False):
                continue
            
            # Filter by category
            if category and idea.get('category') != category:
                continue
            
            # Transform to response format
            filtered_ideas.append({
                'id': idea.get('id'),
                'product_name': idea.get('product_name', 'Unknown'),
                'product_url': idea.get('product_url'),
                'product_domain': idea.get('product_domain'),
                'found_in_tweet': idea.get('tweet_text'),  # Database uses tweet_text
                'tweet_url': idea.get('tweet_url'),
                'author': idea.get('author', '@unknown'),
                'author_followers': idea.get('author_followers', 0),
                'reported_mrr': idea.get('reported_mrr'),
                'score': total_score,
                'grade': idea.get('grade', 'C'),
                'score_breakdown': {
                    'traction': score_data.get('traction', 0) if isinstance(score_data, dict) else 0,
                    'growth': score_data.get('growth', 0) if isinstance(score_data, dict) else 0,
                    'traffic': score_data.get('traffic', 0) if isinstance(score_data, dict) else 0,
                    'simplicity': score_data.get('simplicity', 0) if isinstance(score_data, dict) else 0,
                },
                'engagement': idea.get('engagement', {
                    'likes': 0, 'retweets': 0, 'replies': 0, 'rate': '0%'
                }),
                'traffic_source': idea.get('traffic_source'),
                'has_screenshot': idea.get('has_screenshot', False),
                'replicability': idea.get('replicability', 'medium'),
                'replicability_note': idea.get('replicability_note'),
                'category': idea.get('category', 'Other'),
                'complexity': idea.get('complexity', 'medium'),
                'date_found': idea.get('date_found', datetime.now().isoformat()),
                'tweet_date': idea.get('tweet_date', datetime.now().isoformat()),
                'is_favorited': idea.get('is_favorited', False),
            })
        
        # Apply pagination
        return filtered_ideas[offset:offset + limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ideas/{idea_id}")
async def get_idea(idea_id: int):
    """Get detailed information about a specific idea"""
    try:
        idea = db.get_idea(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        return idea
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ideas/{idea_id}/favorite")
async def toggle_favorite(idea_id: int):
    """Toggle favorite status of an idea"""
    try:
        result = db.toggle_favorite(idea_id)
        return {"success": True, "is_favorited": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ideas/{idea_id}/note")
async def add_note(idea_id: int, request: NoteRequest):
    """Add a note to an idea"""
    try:
        db.add_note(idea_id, request.note)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    try:
        all_ideas = db.list_ideas(limit=10000)
        
        total_ideas = len(all_ideas)
        with_mrr = 0
        high_score_count = 0
        favorites_count = 0
        total_mrr = 0
        total_score = 0
        
        for idea in all_ideas:
            # Count MRR
            mrr = idea.get('reported_mrr')
            if mrr and mrr > 0:
                with_mrr += 1
                total_mrr += mrr
            
            # Calculate score
            score_data = idea.get('score', {})
            if isinstance(score_data, dict):
                score = (
                    score_data.get('traction', 0) +
                    score_data.get('growth', 0) +
                    score_data.get('traffic', 0) +
                    score_data.get('simplicity', 0)
                )
            else:
                score = score_data or 0
            
            total_score += score
            
            # Count high scores
            if score >= 70:
                high_score_count += 1
            
            # Count favorites
            if idea.get('is_favorited', False):
                favorites_count += 1
        
        return {
            'total_ideas': total_ideas,
            'with_mrr': with_mrr,
            'high_score_ideas': high_score_count,
            'favorites': favorites_count,
            'average_mrr': total_mrr / with_mrr if with_mrr > 0 else 0,
            'average_score': total_score / total_ideas if total_ideas > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan", response_model=ScanResponse)
async def scan_twitter(request: ScanRequest):
    """Scan Twitter for new SaaS ideas"""
    try:
        # Initialize finder
        finder = SaaSIdeaFinder(use_mock=True)  # Use mock for testing
        
        # Build query from hashtags
        query = " OR ".join([f"#{tag}" for tag in request.hashtags])
        
        # Search for ideas
        ideas = finder.search(
            query=query,
            days=request.days,
            max_results=request.max_results
        )
        
        # Save to database
        new_count = 0
        for idea in ideas:
            try:
                db.save_idea(idea)
                new_count += 1
            except:
                pass  # Skip duplicates
        
        return ScanResponse(
            total_found=len(ideas),
            new_saved=new_count,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/categories")
async def get_categories():
    """Get list of unique categories"""
    try:
        all_ideas = db.list_ideas(limit=10000)
        categories = set()
        for idea in all_ideas:
            cat = idea.get('category')
            if cat:
                categories.add(cat)
        return sorted(list(categories))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/ideas/{idea_id}")
async def delete_idea(idea_id: int):
    """Delete an idea"""
    try:
        db.delete_idea(idea_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SCRAPER ENDPOINTS
# ============================================

@app.get("/api/scraper/status")
async def get_scraper_status():
    """Get status of all scrapers."""
    if not scraper_manager:
        return {
            "status": "not_initialized",
            "scrapers": []
        }
    
    try:
        status = await scraper_manager.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting scraper status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "scrapers": []
        }

@app.post("/api/scraper/search", response_model=ScrapeResponse)
async def scrape_twitter(request: ScrapeRequest):
    """
    Scrape Twitter for SaaS ideas.
    Uses default queries if none provided.
    """
    if not scraper_manager or not scraper_manager._initialized:
        raise HTTPException(
            status_code=503,
            detail="Scraper not initialized. Check accounts.txt or API tokens."
        )
    
    queries = request.queries or config.scraper.search_queries
    
    tweets = []
    ideas = []
    
    try:
        # Scrape tweets
        async for tweet in scraper_manager.search_multiple_queries(
            queries=queries,
            limit_per_query=request.limit_per_query
        ):
            tweets.append(tweet)
            
            # Extract revenue
            revenue = revenue_extractor.extract(tweet.text)
            
            # Only create idea if revenue found and meets threshold
            if revenue and revenue.amount >= request.min_mrr:
                # Extract products
                products = url_extractor.extract(tweet.text, tweet.urls)
                
                idea = SaaSIdea(
                    source_tweet_id=tweet.id,
                    source_tweet_url=tweet.tweet_url,
                    source_tweet_text=tweet.text,
                    author_username=tweet.author.username if tweet.author else "unknown",
                    author_followers=tweet.author.followers_count if tweet.author else 0,
                    author_verified=tweet.author.verified if tweet.author else False,
                    revenue=revenue,
                    products=products,
                    likes=tweet.metrics.like_count,
                    retweets=tweet.metrics.retweet_count,
                    engagement_rate=tweet.engagement_rate,
                    tweet_created_at=tweet.created_at,
                )
                ideas.append(idea)
        
        return ScrapeResponse(
            status="completed",
            tweets_found=len(tweets),
            ideas_extracted=len(ideas),
            ideas=[idea.model_dump() for idea in ideas]
        )
        
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scraper/trigger")
async def trigger_background_scrape(background_tasks: BackgroundTasks):
    """Trigger a background scrape job."""
    if not scraper_manager:
        raise HTTPException(status_code=503, detail="Scraper not initialized")
    
    background_tasks.add_task(run_background_scrape)
    return {"status": "scheduled", "message": "Scrape job queued"}

async def run_background_scrape():
    """Background task for scraping."""
    global scraper_manager
    
    if not scraper_manager:
        logger.error("Scraper manager not initialized")
        return
    
    logger.info("Starting background scrape...")
    
    try:
        ideas_found = 0
        async for tweet in scraper_manager.search_multiple_queries(
            queries=config.scraper.search_queries,
            limit_per_query=config.scraper.max_tweets_per_query
        ):
            revenue = revenue_extractor.extract(tweet.text)
            
            if revenue and revenue.amount >= config.scraper.min_mrr_threshold:
                # Save to database
                try:
                    products = url_extractor.extract(tweet.text, tweet.urls)
                    
                    idea_data = {
                        "product_name": products[0].name if products else "Unknown",
                        "product_url": products[0].url if products else None,
                        "product_domain": products[0].domain if products else None,
                        "found_in_tweet": tweet.text[:500],
                        "tweet_url": tweet.tweet_url,
                        "author": f"@{tweet.author.username}" if tweet.author else "@unknown",
                        "author_followers": tweet.author.followers_count if tweet.author else 0,
                        "reported_mrr": revenue.amount,
                        "has_screenshot": revenue.has_screenshot,
                        "date_found": datetime.utcnow().isoformat(),
                        "tweet_date": tweet.created_at.isoformat(),
                        "engagement": {
                            "likes": tweet.metrics.like_count,
                            "retweets": tweet.metrics.retweet_count,
                            "replies": tweet.metrics.reply_count,
                            "rate": f"{tweet.engagement_rate:.2f}%"
                        }
                    }
                    
                    db.save_idea(idea_data)
                    ideas_found += 1
                    logger.info(f"Saved idea: {idea_data.get('product_name')} - ${revenue.amount} MRR")
                    
                except Exception as e:
                    logger.warning(f"Failed to save idea: {e}")
        
        logger.info(f"Background scrape completed. Found {ideas_found} ideas.")
        
    except Exception as e:
        logger.error(f"Background scrape error: {e}")

@app.get("/health")
async def health_check():
    """Health check with scraper status."""
    scraper_status = None
    if scraper_manager:
        try:
            scraper_status = await scraper_manager.get_status()
        except:
            pass
    
    return {
        "status": "healthy",
        "service": "SaaS Idea Finder API",
        "scrapers": scraper_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
