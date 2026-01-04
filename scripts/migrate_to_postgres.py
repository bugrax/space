#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from saas_finder.storage.models import Base, IdeaModel, SearchHistoryModel, WatchlistModel


def migrate_data():
    """Migrate data from SQLite to PostgreSQL."""
    
    # Source: SQLite
    sqlite_path = os.getenv("SQLITE_PATH", "./data/ideas.db")
    sqlite_url = f"sqlite:///{sqlite_path}"
    
    # Target: PostgreSQL  
    postgres_url = os.getenv(
        "DATABASE_URL",
        "postgresql://saas_finder:saas_finder_secret@localhost:5432/saas_finder"
    )
    
    print(f"📦 Source: {sqlite_url}")
    print(f"🎯 Target: {postgres_url}")
    
    # Check if SQLite file exists
    if not Path(sqlite_path).exists():
        print(f"❌ SQLite database not found: {sqlite_path}")
        print("Nothing to migrate.")
        return
    
    # Connect to SQLite
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()
    
    # Connect to PostgreSQL
    postgres_engine = create_engine(
        postgres_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )
    
    # Create tables in PostgreSQL
    print("\n📝 Creating tables in PostgreSQL...")
    Base.metadata.create_all(postgres_engine)
    
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    
    try:
        # Migrate Ideas
        print("\n🔄 Migrating ideas...")
        ideas = sqlite_session.query(IdeaModel).all()
        print(f"   Found {len(ideas)} ideas in SQLite")
        
        migrated_ideas = 0
        skipped_ideas = 0
        
        for idea in ideas:
            # Check if already exists
            existing = postgres_session.query(IdeaModel).filter(
                IdeaModel.tweet_id == idea.tweet_id
            ).first()
            
            if existing:
                skipped_ideas += 1
                continue
            
            # Create new record - only copy fields that exist in the model
            new_idea = IdeaModel(
                tweet_id=idea.tweet_id,
                tweet_text=idea.tweet_text,
                tweet_url=idea.tweet_url,
                author_username=idea.author_username,
                author_followers=idea.author_followers,
                tweet_date=idea.tweet_date,
                likes=idea.likes,
                retweets=idea.retweets,
                replies=idea.replies,
                impressions=idea.impressions,
                product_name=idea.product_name,
                product_url=idea.product_url,
                product_domain=idea.product_domain,
                reported_mrr=idea.reported_mrr,
                total_score=idea.total_score,
                traction_score=idea.traction_score,
                growth_score=idea.growth_score,
                traffic_score=idea.traffic_score,
                simplicity_score=idea.simplicity_score,
                score_breakdown=idea.score_breakdown,
                date_found=idea.date_found,
                updated_at=idea.updated_at
            )
            postgres_session.add(new_idea)
            migrated_ideas += 1
        
        postgres_session.commit()
        print(f"   ✅ Migrated: {migrated_ideas}, Skipped: {skipped_ideas}")
        
        # Migrate Search History
        print("\n🔄 Migrating search history...")
        history_items = sqlite_session.query(SearchHistoryModel).all()
        print(f"   Found {len(history_items)} history items in SQLite")
        
        migrated_history = 0
        for item in history_items:
            new_item = SearchHistoryModel(
                query=item.query,
                hashtags=getattr(item, 'hashtags', None),
                keywords=getattr(item, 'keywords', None),
                search_date=getattr(item, 'search_date', None),
                results_count=item.results_count,
                new_ideas_count=item.new_ideas_count
            )
            postgres_session.add(new_item)
            migrated_history += 1
        
        postgres_session.commit()
        print(f"   ✅ Migrated: {migrated_history}")
        
        # Migrate Watchlist
        print("\n🔄 Migrating watchlist...")
        watchlist_items = sqlite_session.query(WatchlistModel).all()
        print(f"   Found {len(watchlist_items)} watchlist items in SQLite")
        
        migrated_watchlist = 0
        for item in watchlist_items:
            # Check if idea exists in postgres
            idea_exists = postgres_session.query(IdeaModel).filter(
                IdeaModel.id == item.idea_id
            ).first()
            
            if idea_exists:
                new_item = WatchlistModel(
                    idea_id=item.idea_id,
                    reason=item.reason,
                    priority=item.priority,
                    added_date=item.added_date
                )
                postgres_session.add(new_item)
                migrated_watchlist += 1
        
        postgres_session.commit()
        print(f"   ✅ Migrated: {migrated_watchlist}")
        
        print("\n" + "="*50)
        print("✅ Migration completed successfully!")
        print("="*50)
        
        # Show summary
        pg_ideas = postgres_session.query(IdeaModel).count()
        print(f"\n📊 PostgreSQL now has {pg_ideas} ideas")
        
    except Exception as e:
        postgres_session.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()


if __name__ == "__main__":
    migrate_data()
