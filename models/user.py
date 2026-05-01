import hashlib
import secrets
import sqlite3
from typing import Optional

class User:
    
    def __init__(self, user_id: int, username: str):
        # Keep the actual user data private so nothing outside class can modify it directly - points and streaks only change through these methods to keep the state consistent.
        self._user_id = user_id
        self._username = username
        self._daily_goal = 20
        self._current_streak = 0
        self._total_points = 0
        self._longest_streak = 0
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    @property
    def total_points(self) -> int:
        return self._total_points
    
    @property
    def current_streak(self) -> int:
        return self._current_streak
    
    @property
    def daily_goal(self) -> int:
        return self._daily_goal
    
    @staticmethod
    def generate_salt(length: int = 16) -> str:
        # secrets.token_hex pulls from the OS's cryptographically secure random number generator - unlike the standard random module, it's designed for security use, so the salt is genuinely unpredictable.
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_password(plain_password: str, salt: str) -> str:
        # Combining the password and salt before hashing means two users with the same password get completely different hashes in the database to stop a leaked database being attacked with precomputed rainbow tables.
        salted = plain_password + salt
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()
    
    @classmethod
    def register(cls, db_manager, username: str, password: str) -> Optional['User']:
        # @classmethod lets this act as an alternative constructor - it validates everything, writes to the database, and hands back a ready-to-use User object, so app.py doesn't have to manage any of that setup itself.

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
        
        salt = cls.generate_salt()
        password_hash = cls.hash_password(password, salt)
        
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # UserAccount holds login credentials, User holds progress data. I'm splitting them to keep authentication separate from application data and wrapping both inserts in one transaction so you can never end up with a UserAccount row that has no matching User row.
            cursor.execute('''
                INSERT INTO UserAccount (Username, PasswordHash, Salt)
                VALUES (?, ?, ?)
            ''', (username, password_hash, salt))
            
            user_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO User (UserID)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            print(f"✓ User '{username}' registered successfully")
            return cls(user_id, username)
            
        except sqlite3.IntegrityError:
            # IntegrityError specifically means the UNIQUE constraint on Username fired - i.e. that username is already taken rather than a general database error.
            conn.rollback()
            raise ValueError("Username already exists")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Registration failed: {e}")
        finally:
            conn.close()
    
    @staticmethod
    def validate_login(db_manager, username: str, entered_password: str) -> Optional['User']:
        try:
            user_data = db_manager.get_user_by_username(username)
            
            if user_data is None:
                return None
            
            stored_hash = user_data['password_hash']
            retrieved_salt = user_data['salt']
            
            # Re-hash the entered password with the same salt used at registration. If the result matches what's stored, the password is correct. The plain text password is never stored or compared directly.
            entered_hash = User.hash_password(entered_password, retrieved_salt)
            
            if entered_hash == stored_hash:
                user = User(user_data['user_id'], user_data['username'])
                
                # Load the user's progress data into the object on login so the rest of the app can read streak and points without extra DB calls.
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
                return None
                
        except Exception as e:
            print(f"Login validation error: {e}")
            return None
    
    def add_points(self, points: int) -> None:
        # Guard against negative values - a review should never subtract points, and catching it here means any upstream bug surfaces immediately.
        if points < 0:
            raise ValueError("Cannot add negative points")
        self._total_points += points
    
    def update_streak(self, db_manager) -> None:
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Update longest streak before the database write so both values stay in sync within the same UPDATE statement.
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
