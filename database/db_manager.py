import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

class DatabaseManager:
    # Single point of contact for all database operations, every service and model goes through this instead of opening their own connections, which keeps the connection logic in one place.
    
    def __init__(self, db_path='database/arabic_learning.db'):
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        # Foreign key enforcement is off by default in SQLite and has to be switched on per connection. Doing it here means every connection automatically respects the ON DELETE CASCADE rules defined in the schema.
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def create_tables(self):
        # CREATE TABLE IF NOT EXISTS means this is safe to call every time the app starts — it only creates the table if it doesn't already exist, so existing data is never overwritten on restart.
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Credentials live in a separate table from progress data so that authentication logic doesn't have to touch the User table and vice versa.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserAccount (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT UNIQUE NOT NULL,
                    PasswordHash TEXT NOT NULL,
                    Salt TEXT NOT NULL,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ON DELETE CASCADE means deleting a UserAccount automatically removes the User row too — no orphaned rows left behind.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS User (
                    UserID INTEGER PRIMARY KEY,
                    DailyCardGoal INTEGER DEFAULT 20 CHECK(DailyCardGoal BETWEEN 5 AND 50),
                    NotificationTime TEXT DEFAULT '18:00',
                    CurrentStreak INTEGER DEFAULT 0,
                    TotalPoints INTEGER DEFAULT 0,
                    LongestStreak INTEGER DEFAULT 0,
                    FOREIGN KEY (UserID) REFERENCES UserAccount(UserID) ON DELETE CASCADE
                )
            ''')
            
            # CHECK constraint on Category enforces that only the defined vocabulary categories can be inserted — the database itself rejects anything else so the app doesn't need to duplicate that validation in Python.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS VocabularyWord (
                    WordID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ArabicTerm TEXT UNIQUE NOT NULL,
                    EnglishTranslation TEXT NOT NULL,
                    Category TEXT NOT NULL CHECK(Category IN ('General Nouns', 'Verbs', 'Adjectives', 
                                                               'Quranic', 'Daily Life', 'Numbers')),
                    ExampleSentence TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS FlashcardSet (
                    SetID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER,
                    SetName TEXT NOT NULL,
                    CreationDate DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
                )
            ''')
            
            # UNIQUE(UserID, WordID, SetID) prevents the same word appearing twice in the same set for the same user — duplicate cards would skew the SRS scheduling and confuse the review queue.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Flashcard (
                    CardID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER NOT NULL,
                    WordID INTEGER NOT NULL,
                    SetID INTEGER NOT NULL,
                    BoxLevel INTEGER DEFAULT 1 CHECK(BoxLevel BETWEEN 1 AND 5),
                    NextReviewDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                    WeightedScore REAL DEFAULT 0.0,
                    TotalReviews INTEGER DEFAULT 0,
                    IsMastered BOOLEAN DEFAULT 0,
                    LastReviewed DATETIME,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
                    FOREIGN KEY (WordID) REFERENCES VocabularyWord(WordID) ON DELETE CASCADE,
                    FOREIGN KEY (SetID) REFERENCES FlashcardSet(SetID) ON DELETE CASCADE,
                    UNIQUE(UserID, WordID, SetID)
                )
            ''')
            
            # These indexes speed up the two queries that run most often: fetching due cards by user+date, and looking up cards within a set.
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_flashcard_user_review
                ON Flashcard(UserID, NextReviewDate)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_flashcard_set_word
                ON Flashcard(SetID, WordID)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_vocab_category
                ON VocabularyWord(Category)
            ''')
            
            conn.commit()
            print("✓ Database tables created successfully")
            
        except sqlite3.Error as e:
            print(f"✗ Database creation error: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        # Generic SELECT wrapper — the ? placeholders in the query string are filled in by SQLite itself rather than by string formatting, which prevents SQL injection regardless of what's in params.
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return results
        except sqlite3.Error as e:
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> bool:
        # Wraps INSERT/UPDATE/DELETE with automatic commit and rollback. Returning a bool instead of raising exceptions means the calling code can handle failures with a simple if-check rather than try/except.
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Update execution error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        # Returns a named dictionary rather than a raw tuple so the caller can access fields by name (e.g. result['salt']) instead of by position, which is much less fragile if the column order ever changes.
        query = '''
            SELECT UserID, Username, PasswordHash, Salt
            FROM UserAccount
            WHERE Username = ?
        '''
        results = self.execute_query(query, (username,))
        
        if results and len(results) > 0:
            return {
                'user_id': results[0][0],
                'username': results[0][1],
                'password_hash': results[0][2],
                'salt': results[0][3]
            }
        return None
