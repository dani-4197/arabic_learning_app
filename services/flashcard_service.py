from collections import deque
from datetime import datetime, date
from typing import List, Optional, Deque
import sqlite3

class ReviewQueue:
    # Manages the order cards are presented during a review session, its built on collections.deque rather than a regular list because deque is optimised for appending and removing from both ends - popleft() is O(1) on a deque but O(n) on a list, which would slow down every card flip as the queue grew.
    
    def __init__(self):
        self._queue: Deque = deque()
    
    def enqueue(self, card) -> None:
        if card is None:
            raise ValueError("Cannot enqueue None")
        self._queue.append(card)
    
    def dequeue(self):
        # Return None rather than raising an IndexError on an empty queue - the review page can check for None and end the session cleanly.
        if self.is_empty():
            return None
        return self._queue.popleft()
    
    def peek(self):
        # Lets the UI check what's coming next without consuming the card.
        if self.is_empty():
            return None
        return self._queue[0]
    
    def is_empty(self) -> bool:
        return len(self._queue) == 0
    
    def size(self) -> int:
        return len(self._queue)
    
    def clear(self) -> None:
        self._queue.clear()


class FlashcardService:
    # Handles all database operations relating to flashcards, it sits between the Flask routes and the database so the route don't have to have any SQL directly.
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_flashcard(self, user_id: int, word_id: int, set_id: int) -> bool:
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check for an existing card before inserting - the UNIQUE constraint on (UserID, WordID, SetID) would catch this too, but checking first lets us return False cleanly instead of catching an IntegrityError.
            cursor.execute('''
                SELECT CardID FROM Flashcard
                WHERE UserID = ? AND WordID = ? AND SetID = ?
            ''', (user_id, word_id, set_id))
            
            if cursor.fetchone():
                print("Card already exists for this user")
                return False
            
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
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # date(NextReviewDate) <= date('now') captures everything scheduled for today or any earlier day the user missed — so catching up is handled automatically without any extra logic. ORDER BY BoxLevel ASC prioritises lower-box cards so struggling words always come up before easy ones in the same session.
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
            
            # Convert tuples to named dictionaries so templates can reference fields by name rather than index — much safer if the column order ever shifts.
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
        if score not in [1, 2, 3, 4]:
            print(f"Invalid score: {score}")
            return False
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT BoxLevel, WeightedScore, TotalReviews
                FROM Flashcard WHERE CardID = ?
            ''', (card_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"Card {card_id} not found")
                return False
            
            current_box, weighted_score, total_reviews = result
            
            # Mirror the same promotion logic from Flashcard.update_leitner_box but applied directly via SQL so we don't need to instantiate a Flashcard object just to update a row.
            if score == 1:
                new_box = 1
            elif score == 2:
                new_box = current_box
            elif score == 3:
                new_box = min(current_box + 1, 5)
            else:
                new_box = min(current_box + 2, 5)
            
            weights = {1: -2, 2: -1, 3: 1, 4: 2}
            new_weighted_score = weighted_score + weights[score]
            new_total_reviews = total_reviews + 1
            
            intervals = {1: 1, 2: 2, 3: 5, 4: 10, 5: 21}
            interval_days = intervals[new_box]
            
            # datetime('now', '+N days') is all handled by SQLite so the next review date is always calculated relative to server time and stored as a consistent format in the database.
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
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # JOIN here pulls the Arabic and English text in the same query so the sets page doesn't need a separate lookup per card.
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
