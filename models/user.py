import hashlib
import secrets

class User:
    """
    Represents a user with secure authentication
    Demonstrates defensive programming and encapsulation
    """
    
    def __init__(self, user_id, username):
        self._user_id = user_id        # Private attribute
        self._username = username
        self._daily_goal = 20
        self._current_streak = 0
        self._total_points = 0
    
    # Getters (encapsulation)
    @property
    def user_id(self):
        return self._user_id
    
    @property
    def username(self):
        return self._username
    
    @property
    def total_points(self):
        return self._total_points
    
    @staticmethod
    def generate_salt(length=16):
        """
        Generates cryptographically secure random salt
        Time complexity: O(1)
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def hash_password(plain_password, salt):
        """
        Hashes password with SHA-256
        One-way function prevents password recovery
        Time complexity: O(1)
        """
        salted = plain_password + salt
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()
    
    @classmethod
    def register(cls, db_manager, username, password):
        """
        Factory method for user registration
        Demonstrates defensive programming with validation
        """
        # Input validation
        if len(username) < 4:
            raise ValueError("Username must be at least 4 characters")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain uppercase letter")
        
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain a number")
        
        # Generate salt and hash
        salt = cls.generate_salt()
        password_hash = cls.hash_password(password, salt)
        
        # Insert into database
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # UserAccount table
            cursor.execute('''
                INSERT INTO UserAccount (Username, PasswordHash, Salt)
                VALUES (?, ?, ?)
            ''', (username, password_hash, salt))
            
            user_id = cursor.lastrowid
            
            # User table
            cursor.execute('''
                INSERT INTO User (UserID)
                VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            return cls(user_id, username)
            
        except sqlite3.IntegrityError:
            raise ValueError("Username already exists")
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Registration failed: {e}")
        finally:
            conn.close()
    
    def add_points(self, points):
        """
        Adds points to user total
        Validates input to prevent negative points
        """
        if points < 0:
            raise ValueError("Cannot add negative points")
        
        self._total_points += points
