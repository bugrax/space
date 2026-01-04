"""
Storage module for persisting SaaS ideas.
"""

from .database import Database, get_db
from .models import IdeaModel, SearchHistoryModel

__all__ = ["Database", "get_db", "IdeaModel", "SearchHistoryModel"]
