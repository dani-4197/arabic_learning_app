from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class Card(ABC):
    # Abstract base class that defines the interface every card type must follow.
    # This is so if I ever add a different card format (multiple choice, fill-in-the-blank) it's will have display() and calculate_next_review() - the rest of the app can treat all card types the same
    
    def __init__(self, card_id: int, word_id: int, user_id: int):
        self._card_id = card_id
        self._word_id = word_id
        self._user_id = user_id
    
    @abstractmethod
    def display(self) -> str:
        # Forces every subclass to define how it presents itself, the abstract decorator means Python will raise an error at startup if a subclass forgets to implement this, rather than failing silently at runtime.
        pass
    
    @abstractmethod
    def calculate_next_review(self) -> int:
        pass
    
    @property
    def card_id(self) -> int:
        return self._card_id
    
    @property
    def word_id(self) -> int:
        return self._word_id
    
    @property
    def user_id(self) -> int:
        return self._user_id


class Flashcard(Card):
    # The concrete card type used throughout the app, inherits Card's interface and adds all Leitner SRS logic on top.
    # Storing these as class-level constants rather than magic numbers scattered through the methods makes it easy to adjust the review schedule in one place.
    INTERVALS = {1: 1, 2: 2, 3: 5, 4: 10, 5: 21}  # days between reviews per box
    WEIGHTS   = {4: 2, 3: 1, 2: -1, 1: -2}          # score contribution to recall %
    
    def __init__(self, card_id: int, word_id: int, user_id: int, 
                 set_id: int, box_level: int = 1, weighted_score: float = 0.0, 
                 total_reviews: int = 0, arabic_term: str = "", 
                 english_translation: str = ""):
        super().__init__(card_id, word_id, user_id)  # pass shared fields up to Card
        self._set_id = set_id
        self._box_level = box_level
        self._weighted_score = weighted_score
        self._total_reviews = total_reviews
        self._next_review_date = datetime.now()
        self._arabic_term = arabic_term
        self._english_translation = english_translation
    
    def display(self) -> str:
        # Fulfils abstract method requirement from Card.
        return f"Flashcard: Box {self._box_level}, Reviews: {self._total_reviews}"
    
    def calculate_next_review(self) -> int:
        # Looks up the interval for the current box level, the .get(__ , 1) fallback means an unexpected box value defaults to 1 day rather than crashing.
        return self.INTERVALS.get(self._box_level, 1)
    
    def update_leitner_box(self, score: int) -> None:
        # Core of the SRS system; the box level controls how often a card comes back - getting it wrong resets to box 1 (review tomorrow), getting it right promotes it so it won't appear for longer and longer intervals.
        
        if score not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid score: {score}. Must be 1-4.")
        
        current_box = self._box_level
        
        if score == 1:
            new_box = 1                          # forgot - start over
        elif score == 2:
            new_box = current_box                # struggled - stay put
        elif score == 3:
            new_box = min(current_box + 1, 5)   # good - move up one
        else:
            new_box = min(current_box + 2, 5)   # perfect - skip ahead two
        
        # min(__, 5) caps the box at 5 in both promotion cases so we never accidentally go above the highest Leitner level
        
        self._box_level = new_box
        self._total_reviews += 1
        self._weighted_score += self.WEIGHTS[score]
        
        interval_days = self.INTERVALS[new_box]
        self._next_review_date = datetime.now() + timedelta(days=interval_days)
    
    def calculate_recall_percentage(self) -> float:
        # The weighted score runs from -(2 * total_reviews) to +(2 * total_reviews), so we shift it up by (total_reviews * 2) to make the worst case 0, then divide by (total_reviews * 4) to bring the best case to 1; Multiplying by 100 gives a clean percentage
        
        if self._total_reviews == 0:
            return 0.0
        
        normalized_score = self._weighted_score + (self._total_reviews * 2)
        max_possible = self._total_reviews * 4
        
        percentage = (normalized_score / max_possible) * 100
        return round(percentage, 2)
    
    @property
    def box_level(self) -> int:
        return self._box_level
    
    @property
    def is_mastered(self) -> bool:
        # Box 5 is the top of the Leitner system - a card here has been recalled correctly enough times so its treated as learned and drops out of the regular review queue.
        return self._box_level == 5
    
    @property
    def next_review_date(self) -> datetime:
        return self._next_review_date
    
    @property
    def arabic_term(self) -> str:
        return self._arabic_term
    
    @property
    def english_translation(self) -> str:
        return self._english_translation
    
    @property
    def weighted_score(self) -> float:
        return self._weighted_score
    
    @property
    def total_reviews(self) -> int:
        return self._total_reviews
    
    def to_dict(self) -> Dict[str, Any]:
        # Serialises the card into a plain dictionary so Flask's jsonify() can send it to the frontend - datetime objects aren't JSON-serialisable on their own, so next_review_date gets converted to an ISO string here
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
