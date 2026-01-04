"""
Database operations for storing and retrieving SaaS ideas.
"""

import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, desc, asc
from sqlalchemy.orm import sessionmaker, Session

from ..config import config
from ..scoring.scorer import SaaSIdea
from .models import Base, IdeaModel, SearchHistoryModel, WatchlistModel


class Database:
    """Database manager for SaaS ideas storage."""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_url: Database connection URL. Uses config if not provided.
                   Supports both PostgreSQL and SQLite.
        """
        # Get database URL from environment or config
        self.db_url = db_url or os.getenv("DATABASE_URL") or config.database.get_connection_url()
        
        # Create engine with appropriate settings
        if self.db_url.startswith("postgresql"):
            # PostgreSQL settings
            self.engine = create_engine(
                self.db_url,
                echo=False,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True  # Handle stale connections
            )
        else:
            # SQLite settings
            Path(config.database.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(
                f"sqlite:///{config.database.sqlite_path}",
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self):
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # ==================== IDEA OPERATIONS ====================
    
    def save_idea(self, idea: SaaSIdea) -> IdeaModel:
        """
        Save a SaaS idea to the database.
        
        Args:
            idea: SaaSIdea to save
        
        Returns:
            Saved IdeaModel
        """
        with self.get_session() as session:
            # Check if already exists
            existing = session.query(IdeaModel).filter(
                IdeaModel.tweet_id == idea.tweet_id
            ).first()
            
            if existing:
                # Update existing record
                return self._update_idea_model(existing, idea, session)
            
            # Create new record
            model = self._create_idea_model(idea)
            session.add(model)
            session.flush()
            
            return model
    
    def save_ideas(self, ideas: list[SaaSIdea]) -> tuple[int, int]:
        """
        Save multiple ideas to the database.
        
        Args:
            ideas: List of SaaSIdea objects
        
        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0
        
        with self.get_session() as session:
            for idea in ideas:
                existing = session.query(IdeaModel).filter(
                    IdeaModel.tweet_id == idea.tweet_id
                ).first()
                
                if existing:
                    self._update_idea_model(existing, idea, session)
                    updated_count += 1
                else:
                    model = self._create_idea_model(idea)
                    session.add(model)
                    new_count += 1
        
        return new_count, updated_count
    
    def get_idea(self, idea_id: int) -> Optional[dict]:
        """Get idea by ID."""
        with self.get_session() as session:
            idea = session.query(IdeaModel).filter(
                IdeaModel.id == idea_id
            ).first()
            if idea:
                return idea.to_dict()
            return None
    
    def get_idea_by_tweet(self, tweet_id: str) -> Optional[IdeaModel]:
        """Get idea by tweet ID."""
        with self.get_session() as session:
            return session.query(IdeaModel).filter(
                IdeaModel.tweet_id == tweet_id
            ).first()
    
    def list_ideas(
        self,
        min_score: int = 0,
        min_mrr: float = 0,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "score",
        ascending: bool = False,
        favorites_only: bool = False
    ) -> list[dict]:
        """
        List ideas with filtering and sorting.
        
        Args:
            min_score: Minimum total score
            min_mrr: Minimum MRR
            category: Filter by category
            limit: Maximum results
            offset: Pagination offset
            order_by: Field to sort by (score, mrr, date_found, tweet_date)
            ascending: Sort ascending if True
            favorites_only: Only return favorited ideas
        
        Returns:
            List of idea dictionaries
        """
        with self.get_session() as session:
            query = session.query(IdeaModel)
            
            # Apply filters
            if min_score > 0:
                query = query.filter(IdeaModel.total_score >= min_score)
            
            if min_mrr > 0:
                query = query.filter(IdeaModel.reported_mrr >= min_mrr)
            
            if category:
                query = query.filter(IdeaModel.category == category)
            
            if favorites_only:
                query = query.filter(IdeaModel.is_favorited == True)
            
            # Apply sorting
            order_column = {
                "score": IdeaModel.total_score,
                "mrr": IdeaModel.reported_mrr,
                "date_found": IdeaModel.date_found,
                "tweet_date": IdeaModel.tweet_date,
                "likes": IdeaModel.likes
            }.get(order_by, IdeaModel.total_score)
            
            if ascending:
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Convert to dicts while in session
            return [idea.to_dict() for idea in query.all()]
    
    def count_ideas(
        self,
        min_score: int = 0,
        min_mrr: float = 0,
        category: Optional[str] = None
    ) -> int:
        """Count ideas matching filters."""
        with self.get_session() as session:
            query = session.query(IdeaModel)
            
            if min_score > 0:
                query = query.filter(IdeaModel.total_score >= min_score)
            
            if min_mrr > 0:
                query = query.filter(IdeaModel.reported_mrr >= min_mrr)
            
            if category:
                query = query.filter(IdeaModel.category == category)
            
            return query.count()
    
    def delete_idea(self, idea_id: int) -> bool:
        """Delete an idea by ID."""
        with self.get_session() as session:
            idea = session.query(IdeaModel).filter(
                IdeaModel.id == idea_id
            ).first()
            
            if idea:
                session.delete(idea)
                return True
            return False
    
    def toggle_favorite(self, idea_id: int) -> bool:
        """Toggle favorite status for an idea."""
        with self.get_session() as session:
            idea = session.query(IdeaModel).filter(
                IdeaModel.id == idea_id
            ).first()
            
            if idea:
                idea.is_favorited = not idea.is_favorited
                return idea.is_favorited
            return False
    
    def add_note(self, idea_id: int, note: str) -> bool:
        """Add a note to an idea."""
        with self.get_session() as session:
            idea = session.query(IdeaModel).filter(
                IdeaModel.id == idea_id
            ).first()
            
            if idea:
                idea.user_notes = note
                return True
            return False
    
    def get_categories(self) -> list[tuple[str, int]]:
        """Get all categories with counts."""
        with self.get_session() as session:
            results = session.query(
                IdeaModel.category,
                # Count
            ).filter(
                IdeaModel.category.isnot(None)
            ).group_by(
                IdeaModel.category
            ).all()
            
            # Manual count since SQLAlchemy count is tricky
            categories = []
            for cat, in results:
                count = session.query(IdeaModel).filter(
                    IdeaModel.category == cat
                ).count()
                categories.append((cat, count))
            
            return sorted(categories, key=lambda x: x[1], reverse=True)
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.get_session() as session:
            total = session.query(IdeaModel).count()
            with_mrr = session.query(IdeaModel).filter(
                IdeaModel.reported_mrr.isnot(None),
                IdeaModel.reported_mrr > 0
            ).count()
            high_score = session.query(IdeaModel).filter(
                IdeaModel.total_score >= 70
            ).count()
            favorites = session.query(IdeaModel).filter(
                IdeaModel.is_favorited == True
            ).count()
            
            # Average MRR
            from sqlalchemy import func
            avg_mrr = session.query(func.avg(IdeaModel.reported_mrr)).filter(
                IdeaModel.reported_mrr.isnot(None),
                IdeaModel.reported_mrr > 0
            ).scalar() or 0
            
            # Average score
            avg_score = session.query(func.avg(IdeaModel.total_score)).scalar() or 0
            
            return {
                "total_ideas": total,
                "with_mrr": with_mrr,
                "high_score_ideas": high_score,
                "favorites": favorites,
                "average_mrr": round(avg_mrr, 2),
                "average_score": round(avg_score, 1)
            }
    
    # ==================== SEARCH HISTORY ====================
    
    def log_search(
        self,
        query: str,
        hashtags: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        results_count: int = 0,
        new_ideas_count: int = 0
    ) -> SearchHistoryModel:
        """Log a search operation."""
        with self.get_session() as session:
            history = SearchHistoryModel(
                query=query,
                hashtags=hashtags,
                keywords=keywords,
                results_count=results_count,
                new_ideas_count=new_ideas_count
            )
            session.add(history)
            session.flush()
            return history
    
    def get_search_history(self, limit: int = 20) -> list[SearchHistoryModel]:
        """Get recent search history."""
        with self.get_session() as session:
            return session.query(SearchHistoryModel).order_by(
                desc(SearchHistoryModel.search_date)
            ).limit(limit).all()
    
    # ==================== WATCHLIST ====================
    
    def add_to_watchlist(
        self,
        identifier: str,
        watch_type: str = "founder",
        notes: Optional[str] = None
    ) -> WatchlistModel:
        """Add item to watchlist."""
        with self.get_session() as session:
            item = WatchlistModel(
                watch_type=watch_type,
                identifier=identifier,
                notes=notes
            )
            session.add(item)
            session.flush()
            return item
    
    def get_watchlist(
        self,
        watch_type: Optional[str] = None,
        active_only: bool = True
    ) -> list[WatchlistModel]:
        """Get watchlist items."""
        with self.get_session() as session:
            query = session.query(WatchlistModel)
            
            if watch_type:
                query = query.filter(WatchlistModel.watch_type == watch_type)
            
            if active_only:
                query = query.filter(WatchlistModel.is_active == True)
            
            return query.all()
    
    def remove_from_watchlist(self, item_id: int) -> bool:
        """Remove item from watchlist."""
        with self.get_session() as session:
            item = session.query(WatchlistModel).filter(
                WatchlistModel.id == item_id
            ).first()
            
            if item:
                item.is_active = False
                return True
            return False
    
    # ==================== HELPER METHODS ====================
    
    def _create_idea_model(self, idea: SaaSIdea) -> IdeaModel:
        """Create IdeaModel from SaaSIdea."""
        return IdeaModel(
            tweet_id=idea.tweet_id,
            tweet_url=idea.tweet_url,
            tweet_text=idea.tweet_text,
            author_username=idea.author_username,
            author_followers=idea.author_followers,
            tweet_date=idea.tweet_date,
            likes=idea.likes,
            retweets=idea.retweets,
            replies=idea.replies,
            impressions=idea.impressions,
            reported_mrr=idea.reported_mrr,
            revenue_confidence=idea.revenue_confidence,
            product_name=idea.product_name,
            product_url=idea.product_url,
            product_domain=idea.product_domain,
            has_screenshot=idea.has_screenshot,
            has_stripe_screenshot=idea.has_stripe_screenshot,
            traffic_data=idea.traffic.model_dump() if hasattr(idea.traffic, 'model_dump') else None,
            total_score=idea.score.total_score if idea.score else 0,
            traction_score=idea.score.traction_score if idea.score else 0,
            growth_score=idea.score.growth_score if idea.score else 0,
            traffic_score=idea.score.traffic_score if idea.score else 0,
            simplicity_score=idea.score.simplicity_score if idea.score else 0,
            score_breakdown=idea.score.breakdown if idea.score else None,
            complexity=idea.complexity.value if idea.complexity else None,
            category=idea.category,
            replicability=idea.replicability.value if idea.replicability else None,
            replicability_note=idea.replicability_note,
            date_found=idea.date_found
        )
    
    def _update_idea_model(
        self,
        model: IdeaModel,
        idea: SaaSIdea,
        _session: Session
    ) -> IdeaModel:
        """Update existing IdeaModel with new data."""
        # Update engagement metrics (these change over time)
        model.likes = idea.likes
        model.retweets = idea.retweets
        model.replies = idea.replies
        model.impressions = idea.impressions
        
        # Update score if better
        if idea.score and idea.score.total_score > model.total_score:
            model.total_score = idea.score.total_score
            model.traction_score = idea.score.traction_score
            model.growth_score = idea.score.growth_score
            model.traffic_score = idea.score.traffic_score
            model.simplicity_score = idea.score.simplicity_score
            model.score_breakdown = idea.score.breakdown
        
        return model


# Singleton database instance
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Get the database instance (creates if needed)."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
