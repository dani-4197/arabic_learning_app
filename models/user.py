import hashlib
import secrets
import sqlite3
from typing import Optional

class User:
    
    def __init__(self, user_id: int, username: str):
        # Initialize user object with ID and username.
        self._user_id = user_id
        self._username = username
        self._daily_goal = 20
        self._current_streak = 0
        self._total_points = 0
        self._longest_streak = 0
    
    @property
    def user_id(self) -> int:
        #Returns user ID#
        return self._user_id
    
    @property
    def username(self) -> str:
        #Returns username#
        return self._username
    
    @property
    def total_points(self) -> int:
        #Returns total points earned#
        return self._total_points
    
    @property
    def current_streak(self) -> int:
        #Returns current study streak#
        return self._current_streak
    
    @property
    def daily_goal(self) -> int:
        #Returns daily card review goal#
        return self._daily_goal
    
    @staticmethod
    def generate_salt(length: int = 16) -> str:
        # Generates cryptographically secure random salt.
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_password(plain_password: str, salt: str) -> str:
        # Hashes password with SHA-256.

        salted = plain_password + salt
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()
    
    @classmethod
    def register(cls, db_manager, username: str, password: str) -> Optional['User']:
        # Factory method for user registration.
        # Input validation
        if len(username) < 4:
            raise ValueError("Username must be at least 4 characters")
        
        if len(username) > 20:
            raise ValueError("Username must be at most 20 characters")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")
        
        # Generate salt and hash password
        salt = cls.generate_salt()
        password_hash = cls.hash_password(password, salt)
        
        # Insert into database with transaction
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Insert into UserAccount table
            cursor.execute('''
                INSERT INTO UserAccount (Username, PasswordHash, Salt)
                VALUES (?, ?, ?)
            ''', (username, password_hash, salt))
            
            user_id = cursor.lastrowid
            
            # Insert into User table with default values
            cursor.execute('''
                INSERT INTO User (UserID)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            
            print(f"✓ User '{username}' registered successfully")
            return cls(user_id, username)
            
        except sqlite3.IntegrityError:
            conn.rollback()
            raise ValueError("Username already exists")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Registration failed: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def validate_login(db_manager, username: str, entered_password: str) -> Optional['User']:
        # Validates user credentials and returns User object if successful.
        try:
            # Retrieve user record
            user_data = db_manager.get_user_by_username(username)
            
            if user_data is None:
                return None  # Invalid username
            
            # Retrieve stored hash and salt
            stored_hash = user_data['password_hash']
            retrieved_salt = user_data['salt']
            
            # Hash entered password with retrieved salt
            entered_hash = User.hash_password(entered_password, retrieved_salt)
            
            # Compare hashes - constant time comparison
            if entered_hash == stored_hash:
                user = User(user_data['user_id'], user_data['username'])
                
                # Load user preferences
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DailyCardGoal, CurrentStreak, TotalPoints, LongestStreak
                    FROM User WHERE UserID = ?
                ''', (user.user_id,))
                
                prefs = cursor.fetchone()
                if prefs:
                    user._daily_goal = prefs[0]
                    user._current_streak = prefs[1]
                    user._total_points = prefs[2]
                    user._longest_streak = prefs[3]
                
                conn.close()
                return user
            else:
                return None  # Incorrect password
                
        except Exception as e:
            print(f"Login validation error: {e}")
            return None
    
    def add_points(self, points: int) -> None:
        # Adds points to user total with validation
        if points < 0:
            raise ValueError("Cannot add negative points")
        
        self._total_points += points
    
    def update_streak(self, db_manager) -> None:
        # Updates user's study streak in database.
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Update longest streak if current exceeds it
            if self._current_streak > self._longest_streak:
                self._longest_streak = self._current_streak
            
            cursor.execute('''
                UPDATE User
                SET CurrentStreak = ?, TotalPoints = ?, LongestStreak = ?
                WHERE UserID = ?
            ''', (self._current_streak, self._total_points, self._longest_streak, self._user_id))
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Streak update error: {e}")
            conn.rollback()
        finally:
            conn.close()
