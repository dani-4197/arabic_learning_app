from abc import ABC, abstractmethod
from datetime import datetime, timedelta

class Card(ABC):
    """
    Abstract base class for all card types
    Demonstrates inheritance and polymorphism
    """
    
    def __init__(self, card_id, word_id, user_id):
        self._card_id = card_id
        self._word_id = word_id
        self._user_id = user_id
    
    @abstractmethod
    def display(self):
        """
        Polymorphic method - must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def calculate_next_review(self):
        """
        Polymorphic method for scheduling
        """
        pass
    
    @property
    def card_id(self):
        return self._card_id
    
    @property
    def word_id(self):
        return self._word_id


class Flashcard(Card):
    """
    Concrete implementation for Leitner system flashcards
    Inherits from Card base class
    """
    
    # Class constants for Leitner intervals (in days)
    INTERVALS = {1: 1, 2: 2, 3: 5, 4: 10, 5: 21}
    WEIGHTS = {4: 2, 3: 1, 2: -1, 1: -2}
    
    def __init__(self, card_id, word_id, user_id, box_level=1, 
                 weighted_score=0.0, total_reviews=0):
        super().__init__(card_id, word_id, user_id)  # Call parent constructor
        self._box_level = box_level
        self._weighted_score = weighted_score
        self._total_reviews = total_reviews
        self._next_review_date = datetime.now()
    
    def display(self):
        """
        Polymorphic implementation - overrides abstract method
        """
        return f"Flashcard: Box {self._box_level}, Reviews: {self._total_reviews}"
    
    def calculate_next_review(self):
        """
        Polymorphic implementation - returns days until next review
        Uses Leitner intervals
        """
        return self.INTERVALS.get(self._box_level, 1)
    
    def update_leitner_box(self, score):
        """
        Core SRS algorithm - updates box level based on 4-point score
        
        Algorithm complexity: O(1)
        
        Score meanings:
        1 - Forgot: Reset to Box 1
        2 - Struggled: Stay in current box
        3 - Good recall: Move up 1 box
        4 - Perfect recall: Move up 2 boxes
        """
        # Defensive programming - validate input
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
        else:  # score == 4
            new_box = min(current_box + 2, 5)  # Promote 2 levels
        
        # Update state
        self._box_level = new_box
        self._total_reviews += 1
        self._weighted_score += self.WEIGHTS[score]
        
        # Calculate next review date
        interval_days = self.INTERVALS[new_box]
        self._next_review_date = datetime.now() + timedelta(days=interval_days)
    
    def calculate_recall_percentage(self):
        """
        Complex algorithm for weighted progress calculation
        
        Normalizes score so worst possible (-2*N) = 0%
        and best possible (+2*N) = 100%
        
        Time complexity: O(1)
        """
        if self._total_reviews == 0:
            return 0.0
        
        # Normalize: shift range so minimum is 0
        normalized_score = self._weighted_score + (self._total_reviews * 2)
        max_possible = self._total_reviews * 4
        
        percentage = (normalized_score / max_possible) * 100
        return round(percentage, 2)
    
    @property
    def box_level(self):
        return self._box_level
    
    @property
    def is_mastered(self):
        return self._box_level == 5
