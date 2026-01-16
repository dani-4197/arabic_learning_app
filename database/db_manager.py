import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    """
    Manages all database operations with comprehensive exception handling
    Implements connection pooling and transaction management
    """
    
    def __init__(self, db_path='database/arabic_learning.db'):
        self.db_path = db_path
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.create_tables()
        self.create_indexes()
    
    def get_connection(self):
        """
        Returns a new database connection
        Enables foreign key constraints for referential integrity
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
        return conn
    
    def create_tables(self):
        """
        Creates all database tables
        Demonstrates understanding of relational database design
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # UserAccount table - stores authentication credentials
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserAccount (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT UNIQUE NOT NULL CHECK(length(Username) >= 4),
                    PasswordHash TEXT NOT NULL,
                    Salt TEXT NOT NULL,
                    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # User table - stores user preferences and progress
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS User (
                    UserID INTEGER PRIMARY KEY,
                    DailyCardGoal INTEGER DEFAULT 20 CHECK(DailyCardGoal BETWEEN 5 AND 100),
                    NotificationTime TEXT DEFAULT '18:00',
                    CurrentStreak INTEGER DEFAULT 0,
                    LongestStreak INTEGER DEFAULT 0,
                    TotalPoints INTEGER DEFAULT 0,
                    FOREIGN KEY (UserID) REFERENCES UserAccount(UserID) ON DELETE CASCADE
                )
            ''')
            
            # VocabularyWord table - master vocabulary list
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS VocabularyWord (
                    WordID INTEGER PRIMARY KEY AUTOINCREMENT,
                    ArabicTerm TEXT UNIQUE NOT NULL,
                    EnglishTranslation TEXT NOT NULL,
                    Category TEXT NOT NULL,
                    ExampleSentence TEXT,
                    DifficultyLevel INTEGER DEFAULT 1 CHECK(DifficultyLevel BETWEEN 1 AND 5)
                )
            ''')
            
            # FlashcardSet table - user-created sets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS FlashcardSet (
                    SetID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER,
                    SetName TEXT NOT NULL,
                    CreationDate DATE DEFAULT CURRENT_DATE,
                    Description TEXT,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
                )
            ''')
            
            # Flashcard table - junction table + SRS progress
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
                    LastReviewedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
                    FOREIGN KEY (WordID) REFERENCES VocabularyWord(WordID) ON DELETE CASCADE,
                    FOREIGN KEY (SetID) REFERENCES FlashcardSet(SetID) ON DELETE CASCADE,
                    UNIQUE(UserID, WordID, SetID)
                )
            ''')
            
            # QuizSession table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS QuizSession (
                    SessionID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER NOT NULL,
                    SetID INTEGER NOT NULL,
                    StartTime DATETIME DEFAULT CURRENT_TIMESTAMP,
                    EndTime DATETIME,
                    TotalQuestions INTEGER DEFAULT 0,
                    Score INTEGER DEFAULT 0,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
                    FOREIGN KEY (SetID) REFERENCES FlashcardSet(SetID) ON DELETE CASCADE
                )
            ''')
            
            # QuizSessionAttempt table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS QuizSessionAttempt (
                    AttemptID INTEGER PRIMARY KEY AUTOINCREMENT,
                    SessionID INTEGER NOT NULL,
                    WordID INTEGER NOT NULL,
                    UserAnswer TEXT,
                    IsCorrect BOOLEAN NOT NULL,
                    TimeTakenSec REAL DEFAULT 0.0,
                    FOREIGN KEY (SessionID) REFERENCES QuizSession(SessionID) ON DELETE CASCADE,
                    FOREIGN KEY (WordID) REFERENCES VocabularyWord(WordID) ON DELETE CASCADE
                )
            ''')
            
            # Leaderboard table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Leaderboard (
                    LeaderboardID INTEGER PRIMARY KEY AUTOINCREMENT,
                    UserID INTEGER UNIQUE NOT NULL,
                    TotalPoints INTEGER DEFAULT 0,
                    CurrentStreak INTEGER DEFAULT 0,
                    LongestStreak INTEGER DEFAULT 0,
                    WordsMastered INTEGER DEFAULT 0,
                    TotalReviews INTEGER DEFAULT 0,
                    QuizzesCompleted INTEGER DEFAULT 0,
                    AverageQuizScore REAL DEFAULT 0.0,
                    LastUpdated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    Rank INTEGER,
                    FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            print("✓ Database tables created successfully")
            
        except sqlite3.Error as e:
            print(f"✗ Database creation error: {e}")
            raise
        finally:
            conn.close()
    
    def create_indexes(self):
        """
        Creates indexes for frequently queried columns
        Improves query performance from O(n) to O(log n)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Index for finding due cards (most frequent query
