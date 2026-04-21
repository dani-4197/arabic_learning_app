from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class Card(ABC):
    # Abstract base class for all card types.
    def __init__(self, card_id: int, word_id: int, user_id: int):
        # Initializes base card attributes.
        self._card_id = card_id
        self._word_id = word_id
        self._user_id = user_id
    
    @abstractmethod
    def display(self) -> str:
        # Polymorphic method - must be implemented by subclasses.
        pass
    
    @abstractmethod
    def calculate_next_review(self) -> int:
        # Polymorphic method for scheduling.
        pass
    
    @property
    def card_id(self) -> int:
        #Returns card ID
        return self._card_id
    
    @property
    def word_id(self) -> int:
        #Returns word ID
        return self._word_id
    
    @property
    def user_id(self) -> int:
        #Returns user ID
        return self._user_id


class Flashcard(Card):
    """
    Concrete implementation for Leitner system flashcards.
    Inherits from Card base class.
    """
    
    # Class constants for Leitner intervals
    INTERVALS = {1: 1, 2: 2, 3: 5, 4: 10, 5: 21}
    
    # Weights for scoring system
    WEIGHTS = {4: 2, 3: 1, 2: -1, 1: -2}
    
    def __init__(self, card_id: int, word_id: int, user_id: int, 
                 set_id: int, box_level: int = 1, weighted_score: float = 0.0, 
                 total_reviews: int = 0, arabic_term: str = "", 
                 english_translation: str = ""):
        # Initialize flashcard with Leitner system parameters.
        super().__init__(card_id, word_id, user_id)  # Call parent constructor
        self._set_id = set_id
        self._box_level = box_level
        self._weighted_score = weighted_score
        self._total_reviews = total_reviews
        self._next_review_date = datetime.now()
        self._arabic_term = arabic_term
        self._english_translation = english_translation
    
    def display(self) -> str:
        # Polymorphic implementation - overrides abstract method.
        return f"Flashcard: Box {self._box_level}, Reviews: {self._total_reviews}"
    
    def calculate_next_review(self) -> int:
        # Polymorphic implementation - returns days until next review and uses Leitner intervals.
        return self.INTERVALS.get(self._box_level, 1)
    
    def update_leitner_box(self, score: int) -> None:
        # Core SRS algorithm - updates box level based on 4-point score.
        # Validate input
        if score not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid score: {score}. Must be 1-4.")
        
        current_box = self._box_level
        
        # Leitner promotion logic
        if score == 1:
            new_box = 1  # Reset to start
        elif score == 2:
            new_box = current_box  # No change
        elif score == 3:
            new_box = min(current_box + 1, 5)  # Promote 1 level
        else: 
            new_box = min(current_box + 2, 5)  # Promote 2 levels
        
        # Update state
        self._box_level = new_box
        self._total_reviews += 1
        self._weighted_score += self.WEIGHTS[score]
        
        # Calculate next review date
        interval_days = self.INTERVALS[new_box]
        self._next_review_date = datetime.now() + timedelta(days=interval_days)
    
    def calculate_recall_percentage(self) -> float:
        """
        Algorithm for weighted progress calculation.
        Normalizes score so worst possible (-2*N) = 0% and best possible (+2*N) = 100%
        """
        if self._total_reviews == 0:
            return 0.0
        """
        Normalize: shift range so minimum is 0
        Worst case: always scoring 1 (-2 points each time)
        Best case: always scoring 4 (+2 points each time)
        """
        normalized_score = self._weighted_score + (self._total_reviews * 2)
        max_possible = self._total_reviews * 4
        
        percentage = (normalized_score / max_possible) * 100
        return round(percentage, 2)
    
    @property
    def box_level(self) -> int:
        #Returns current Leitner box level#
        return self._box_level
    
    @property
    def is_mastered(self) -> bool:
        #Returns True if card has reached Box 5
        return self._box_level == 5
    
    @property
    def next_review_date(self) -> datetime:
        #Returns scheduled next review date
        return self._next_review_date
    
    @property
    def arabic_term(self) -> str:
        #Returns Arabic term
        return self._arabic_term
    
    @property
    def english_translation(self) -> str:
        #Returns English translation
        return self._english_translation
    
    @property
    def weighted_score(self) -> float:
        #Returns weighted score
        return self._weighted_score
    
    @property
    def total_reviews(self) -> int:
        #Returns total review count
        return self._total_reviews
    
    def to_dict(self) -> Dict[str, Any]:
        # Converts flashcard to dictionary for JSON serialization.
                                        
        return {
            'card_id': self._card_id,
            'word_id': self._word_id,
            'user_id': self._user_id,
            'set_id': self._set_id,
            'box_level': self._box_level,
            'next_review_date': self._next_review_date.isoformat(),
            'weighted_score': self._weighted_score,
            'total_reviews': self._total_reviews,
            'is_mastered': self.is_mastered,
            'recall_percentage': self.calculate_recall_percentage(),
            'arabic_term': self._arabic_term,
            'english_translation': self._english_translation
        }
