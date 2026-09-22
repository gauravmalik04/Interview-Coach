import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger("ai_interview.question_loader")

class QuestionItem(BaseModel):
    id: str
    category: str
    difficulty: str
    text: str
    optimal_complexity: Optional[str] = ""
    follow_ups: List[str] = []

class QuestionLoader:
    """Service to load, parse, cache, and serve technical interview questions."""

    def __init__(self):
        self._questions: List[QuestionItem] = []
        self._is_loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def get_all_questions(self) -> List[QuestionItem]:
        return self._questions

    def get_categories(self) -> List[str]:
        return list(set(q.category for q in self._questions))

    def get_questions_by_category(self, category: str, limit: Optional[int] = None) -> List[QuestionItem]:
        """Retrieve questions matching category (case-insensitive substring or exact)."""
        cat_lower = category.lower()
        if any(term in cat_lower for term in ["general", "all", "comprehensive", "mock"]):
            # Diversify across distinct DSA categories
            diverse = []
            seen_categories = set()
            for q in self._questions:
                if q.category not in seen_categories:
                    diverse.append(q)
                    seen_categories.add(q.category)
            # If diverse list is short, append remainder
            for q in self._questions:
                if q not in diverse:
                    diverse.append(q)
            if limit:
                return diverse[:limit]
            return diverse

        filtered = [
            q for q in self._questions
            if cat_lower in q.category.lower() or q.category.lower() in cat_lower
        ]
        if not filtered:
            # Fallback to all questions if specific category not found
            filtered = self._questions
        if limit:
            return filtered[:limit]
        return filtered

    async def load_questions(self, force_refresh: bool = False) -> List[QuestionItem]:
        """Load questions from GitHub or fallback to local questions.json."""
        if self._is_loaded and not force_refresh:
            return self._questions

        loaded = False

        # Attempt to fetch from GitHub if configured
        if settings.GITHUB_QUESTIONS_URL and not settings.DEBUG:
            try:
                logger.info(f"Attempting to fetch questions from {settings.GITHUB_QUESTIONS_URL}...")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(settings.GITHUB_QUESTIONS_URL)
                    if response.status_code == 200:
                        # If a raw JSON endpoint or markdown is parsed:
                        data = response.json()
                        self._questions = [QuestionItem(**item) for item in data]
                        loaded = True
                        logger.info(f"Successfully loaded {len(self._questions)} questions from remote source.")
            except Exception as e:
                logger.warning(f"Failed to load remote questions: {e}. Falling back to bundled JSON.")

        # Local fallback
        if not loaded:
            fallback_file = Path(settings.DATA_DIR) / "questions.json"
            if fallback_file.exists():
                try:
                    with open(fallback_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._questions = [QuestionItem(**item) for item in data]
                    loaded = True
                    logger.info(f"Successfully loaded {len(self._questions)} questions from local {fallback_file}.")
                except Exception as e:
                    logger.error(f"Failed to read local questions file: {e}")

        self._is_loaded = loaded
        return self._questions

# Global singleton question loader instance
question_loader = QuestionLoader()
