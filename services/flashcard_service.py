from collections import deque
from datetime import datetime, date
from typing import List, Optional, Deque
import sqlite3

class ReviewQueue:
    # Queue (FIFO) for managing flashcard review order
    
    def __init__(self):
        # Initialize queue using deque.
        self._queue: Deque = deque()
    
    def enqueue(self, card):
        """
        Adds card to end of queue.
        Time complexity: O(1)
        """
        if card is None:
            raise ValueError("Cannot enqueue None")
        
        self._queue.append(card)
    
    def dequeue(self):
        """
        Removes and returns card from front of queue.
        Time complexity: O(1)
        """
        if self.is_empty():
            return None
        
        return self._queue.popleft()
    
    def peek(self):
        # Views next card without removing.
        if self.is_empty():
            return None
        
        return self._queue[0]
    
    def is_empty(self) -> bool:
        # Checks if queue has no elements.
        return len(self._queue) == 0
    
    def size(self) -> int:
        # Returns number of cards in queue.
        return len(self._queue)
    
    def clear(self) -> None:
        # Empties the queue.
        self._queue.clear()


class FlashcardService:
    """
    Business logic for flashcard operations.
    Handles card creation, updates, and review scheduling.
    """
    
    def __init__(self, db_manager):
        # Initialize service with database manager.
        self.db_manager = db_manager
    
    def create_flashcard(self, user_id: int, word_id: int, set_id: int) -> bool:
        # Creates a new flashcard for a user.
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check if card already exists for this user/word/set combo
            cursor.execute('''
                SELECT CardID FROM Flashcard
                WHERE UserID = ? AND WordID = ? AND SetID = ?
            ''', (user_id, word_id, set_id))
            
            if cursor.fetchone():
                print("Card already exists for this user")
                return False
            
            # Create new flashcard with default values
            cursor.execute('''
                INSERT INTO Flashcard 
                (UserID, WordID, SetID, BoxLevel, NextReviewDate, WeightedScore, TotalReviews)
                VALUES (?, ?, ?, 1, datetime('now'), 0.0, 0)
            ''', (user_id, word_id, set_id))
            
            conn.commit()
            print(f"✓ Flashcard created for word {word_id}")
            return True
            
        except sqlite3.Error as e:
            print(f"Error creating flashcard: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_due_cards(self, user_id: int, limit: Optional[int] = None) -> List:
        # Retrieves all flashcards due for review today.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get all cards where next review date is today or earlier
            query = '''
                SELECT 
                    f.CardID, f.UserID, f.WordID, f.SetID,
                    f.BoxLevel, f.NextReviewDate, f.WeightedScore, f.TotalReviews,
                    v.ArabicTerm, v.EnglishTranslation, v.Category
                FROM Flashcard f
                JOIN VocabularyWord v ON f.WordID = v.WordID
                WHERE f.UserID = ? AND date(f.NextReviewDate) <= date('now')
                ORDER BY f.BoxLevel ASC, f.NextReviewDate ASC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (user_id,))
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            cards = []
            for row in results:
                cards.append({
                    'card_id': row[0],
                    'user_id': row[1],
                    'word_id': row[2],
                    'set_id': row[3],
                    'box_level': row[4],
                    'next_review_date': row[5],
                    'weighted_score': row[6],
                    'total_reviews': row[7],
                    'arabic_term': row[8],
                    'english_translation': row[9],
                    'category': row[10]
                })
            
            return cards
            
        except sqlite3.Error as e:
            print(f"Error getting due cards: {e}")
            return []
        finally:
            conn.close()
    
    def update_card_after_review(self, card_id: int, score: int) -> bool:
        # Updates flashcard after user reviews it.
        # Validate score
        if score not in [1, 2, 3, 4]:
            print(f"Invalid score: {score}")
            return False
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get current card state
            cursor.execute('''
                SELECT BoxLevel, WeightedScore, TotalReviews
                FROM Flashcard WHERE CardID = ?
            ''', (card_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"Card {card_id} not found")
                return False
            
            current_box, weighted_score, total_reviews = result
            
            # Calculate new box level (Leitner algorithm)
            if score == 1:
                new_box = 1  # Forgot - reset to box 1
            elif score == 2:
                new_box = current_box  # Struggled - stay in same box
            elif score == 3:
                new_box = min(current_box + 1, 5)  # Good - move up 1
            else:  # score == 4
                new_box = min(current_box + 2, 5)  # Perfect - move up 2
            
            # Update weighted score
            weights = {1: -2, 2: -1, 3: 1, 4: 2}
            new_weighted_score = weighted_score + weights[score]
            new_total_reviews = total_reviews + 1
            
            # Calculate next review date based on new box
            intervals = {1: 1, 2: 2, 3: 5, 4: 10, 5: 21}
            interval_days = intervals[new_box]
            
            # Update database
            cursor.execute('''
                UPDATE Flashcard
                SET BoxLevel = ?,
                    WeightedScore = ?,
                    TotalReviews = ?,
                    NextReviewDate = datetime('now', '+' || ? || ' days'),
                    LastReviewed = datetime('now'),
                    IsMastered = ?
                WHERE CardID = ?
            ''', (new_box, new_weighted_score, new_total_reviews, 
                  interval_days, 1 if new_box == 5 else 0, card_id))
            
            conn.commit()
            print(f"✓ Card {card_id} updated: Box {current_box} → {new_box}")
            return True
            
        except sqlite3.Error as e:
            print(f"Error updating card: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_cards_by_set(self, user_id: int, set_id: int) -> List:
        # Gets all cards in a specific set for a user.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    f.CardID, f.BoxLevel, f.TotalReviews, f.IsMastered,
                    v.ArabicTerm, v.EnglishTranslation
                FROM Flashcard f
                JOIN VocabularyWord v ON f.WordID = v.WordID
                WHERE f.UserID = ? AND f.SetID = ?
                ORDER BY v.ArabicTerm
            ''', (user_id, set_id))
            
            results = cursor.fetchall()
            
            cards = []
            for row in results:
                cards.append({
                    'card_id': row[0],
                    'box_level': row[1],
                    'total_reviews': row[2],
                    'is_mastered': row[3],
                    'arabic_term': row[4],
                    'english_translation': row[5]
                })
            
            return cards
            
        except sqlite3.Error as e:
            print(f"Error getting cards by set: {e}")
            return []
        finally:
            conn.close()
