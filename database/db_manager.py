import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

class DatabaseManager:
    """
    Manages all database operations
    """
    
    def __init__(self, db_path='database/arabic_learning.db'):
        """
        Initialize database manager and create tables if they don't exist
        """
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Create and return a database connection with foreign keys enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # This enables foreign key constraints
        return conn
    
    def create_tables(self):
        """
        Creates all necessary tables with proper foreign key constraints
        Uses defensive programming to handle existing tables
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # UserAccount table - stores authentication credentials
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserAccount (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT UNIQUE NOT NULL,
                    PasswordHash TEXT NOT NULL,
                    Salt TEXT NOT NULL,
                    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User table - stores user preferences and progress
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
            
            # VocabularyWord table - master vocabulary list
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
            
            # FlashcardSet table - user-created or system sets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS FlashcardSet (
                    SetID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER,
                    SetName TEXT NOT NULL,
                    CreationDate DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
                )
            ''')
            
            # Flashcard table - junction table with SRS progress
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
            
            # Create indexes for performance optimization
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
        """
        Execute a SELECT query and return results.
        """
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
        """
        Execute an INSERT, UPDATE, or DELETE query.
        """
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
        """
        Retrieve user account information by username.
        """
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
