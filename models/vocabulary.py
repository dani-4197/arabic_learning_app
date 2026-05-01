from typing import Optional, Dict, Any

class VocabularyCache:
    # Cache built on top of Python's dictionary so vocabulary lookups during a review session don't need a database call every time. I used dictionaries as they give O(1) average-case access for when the app might look up the same word repeatedly across a session.
    
    def __init__(self):
        self._word_cache: Dict[int, 'VocabularyWord'] = {}
    
    def add_word(self, word_id: int, word_obj: 'VocabularyWord') -> None:
        # Reject anything that isn't a non-negative integer up front — word IDs come from the database so this should always be fine, but catching it here means bad data fails loudly rather than silently storing something unusable.
        if not isinstance(word_id, int) or word_id < 0:
            raise ValueError("word_id must be non-negative integer")
        self._word_cache[word_id] = word_obj
    
    def get_word(self, word_id: int) -> Optional['VocabularyWord']:
        # .get() returns None instead of raising KeyError if the word isn't in the cache, which is the safer default for a lookup that might miss.
        return self._word_cache.get(word_id, None)
    
    def remove_word(self, word_id: int) -> None:
        # Checks before deleting so calling remove on a missing ID is a no-op rather than an exception — the caller doesn't have to worry about whether the word was there in the first place.
        if word_id in self._word_cache:
            del self._word_cache[word_id]
    
    def size(self) -> int:
        return len(self._word_cache)
    
    def clear(self) -> None:
        # Reassigning to an empty dict is faster than calling .clear() on a large dictionary as Python can just drop the reference to the old object.
        self._word_cache = {}
    
    def contains(self, word_id: int) -> bool:
        return word_id in self._word_cache


class VocabularyWord:
    # Represents a single Arabic-English word pair from the database, I'm keeping this as its own class rather than just passing dicts around so the vocabulary data always has a consistent structure.
    
    def __init__(self, word_id: int, arabic_term: str, 
                 english_translation: str, category: str, 
                 example_sentence: str = ""):
        self._word_id = word_id
        self._arabic_term = arabic_term
        self._english_translation = english_translation
        self._category = category
        self._example_sentence = example_sentence
    
    @property
    def word_id(self):
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
        # Used when the word needs to be passed to a template or API response as plain data rather than a Python object.
        return {
            'word_id': self._word_id,
            'arabic': self._arabic_term,
            'english': self._english_translation,
            'category': self._category,
            'example': self._example_sentence
        }
