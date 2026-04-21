from typing import Optional, Dict, Any

class VocabularyCache:
    # Hash table implementation for O(1) vocabulary lookups.
    
    def __init__(self):
        #Initializes empty hash table using Python dictionary.
        self._word_cache: Dict[int, 'VocabularyWord'] = {}
    
    def add_word(self, word_id: int, word_obj: 'VocabularyWord') -> None:
        """
        Adds word to cache.
        Time complexity: O(1) average case
        Space complexity: O(n) where n = number of words
        """
        if not isinstance(word_id, int) or word_id < 0:
            raise ValueError("word_id must be non-negative integer")
        
        self._word_cache[word_id] = word_obj
    
    def get_word(self, word_id: int) -> Optional['VocabularyWord']:
        """
        Retrieves word from cache. 
        Time complexity: O(1) average case
        """
        return self._word_cache.get(word_id, None)
    
    def remove_word(self, word_id: int) -> None:
        """
        Removes word from cache.
        Time complexity: O(1) average case
        """
        if word_id in self._word_cache:
            del self._word_cache[word_id]
    
    def size(self) -> int:
        # Returns number of words in cache.
        
        return len(self._word_cache)
    
    def clear(self) -> None:
        """
        Clears entire cache.
        Time complexity: O(1) operation
        """
        self._word_cache = {}
    
    def contains(self, word_id: int) -> bool:
        """
        Checks if word exists in cache.
        Time complexity: O(1) average case
        """
        return word_id in self._word_cache


class VocabularyWord:
    # Represents a single Arabic-English word pair.
    
    def __init__(self, word_id: int, arabic_term: str, 
                 english_translation: str, category: str, 
                 example_sentence: str = ""):
        # Initialize vocabulary word.
        
        self._word_id = word_id
        self._arabic_term = arabic_term
        self._english_translation = english_translation
        self._category = category
        self._example_sentence = example_sentence
    
    @property
    def word_id(self):
        """Returns word ID"""
        return self._word_id
    
    @property
    def arabic(self):
        return self._arabic_term
    
    @property
    def english(self):
        return self._english_translation
    
    @property
    def category(self):
        return self._category
    
    @property
    def example(self):
        return self._example_sentence
    
    def to_dict(self) -> Dict[str, Any]:
        # Converts to dictionary for JSON serialization.

        return {
            'word_id': self._word_id,
            'arabic': self._arabic_term,
            'english': self._english_translation,
            'category': self._category,
            'example': self._example_sentence
        }
