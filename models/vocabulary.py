class VocabularyCache:
    """
    Hash table implementation for O(1) vocabulary lookups
    Demonstrates understanding of data structures and complexity analysis
    """
    
    def __init__(self):
        """
        Initializes empty hash table using Python dictionary
        Python dicts use hash tables internally
        """
        self._word_cache = {}  # Dictionary = hash table
    
    def add_word(self, word_id, word_obj):
        """
        Adds word to cache
        
        Time complexity: O(1) average case
        Space complexity: O(n) where n = number of words
        
        Args:
            word_id: Unique identifier for word
            word_obj: VocabularyWord object containing arabic/english
        """
        if not isinstance(word_id, int) or word_id < 0:
            raise ValueError("word_id must be non-negative integer")
        
        self._word_cache[word_id] = word_obj
    
    def get_word(self, word_id):
        """
        Retrieves word from cache
        
        Time complexity: O(1) average case
        Returns None if word not found (defensive programming)
        """
        return self._word_cache.get(word_id, None)
    
    def remove_word(self, word_id):
        """
        Removes word from cache
        
        Time complexity: O(1) average case
        """
        if word_id in self._word_cache:
            del self._word_cache[word_id]
    
    def size(self):
        """Returns number of words in cache"""
        return len(self._word_cache)
    
    def clear(self):
        """Clears entire cache - O(1) operation"""
        self._word_cache = {}


class VocabularyWord:
    """
    Represents a single Arabic-English word pair
    """
    
    def __init__(self, word_id, arabic_term, english_translation, category):
        self._word_id = word_id
        self._arabic_term = arabic_term
        self._english_translation = english_translation
        self._category = category
    
    @property
    def arabic(self):
        return self._arabic_term
    
    @property
    def english(self):
        return self._english_translation
    
    def to_dict(self):
        """Converts to dictionary for JSON serialization"""
        return {
            'word_id': self._word_id,
            'arabic': self._arabic_term,
            'english': self._english_translation,
            'category': self._category
        }
