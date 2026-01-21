from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

# Import my custom modules
from database.db_manager import DatabaseManager
from models.user import User
from models.flashcard import Flashcard
from models.vocabulary import VocabularyCache, VocabularyWord
from services.flashcard_service import FlashcardService, ReviewQueue
from services.analytics_service import AnalyticsService
from services.leaderboard_service import LeaderboardService

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize database and services
db_manager = DatabaseManager()
flashcard_service = FlashcardService(db_manager)
analytics_service = AnalyticsService(db_manager)
leaderboard_service = LeaderboardService(db_manager)

# Initialize vocabulary cache
vocab_cache = VocabularyCache()

# Flask login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class UserLogin:
    # Wrapper class for Flask-Login compatibility
    def __init__(self, user):
        self.user = user
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.user.user_id)

@login_manager.user_loader
def load_user(user_id):
    # Load user for Flask-Login
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ua.UserID, ua.Username
            FROM UserAccount ua
            WHERE ua.UserID = ?
        ''', (int(user_id),))
        
        result = cursor.fetchone()
        if result:
            user = User(result[0], result[1])
            return UserLogin(user)
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    finally:
        conn.close()


@app.route('/')
def index():
    # Home page - redirects to dashboard if logged in, otherwise to login
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login page and handler
    GET: Display login form
    POST: Process login credentials
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        # Validate credentials
        user = User.validate_login(db_manager, username, password)
        
        if user:
            # Successful login
            user_login = UserLogin(user)
            login_user(user_login, remember=True)
            flash(f'Welcome back, {username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration page and handler
    GET: Display registration form
    POST: Process new user registration
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('login.html')
        
        try:
            # Attempt registration
            user = User.register(db_manager, username, password)
            
            if user:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
        
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash('An error occurred during registration', 'error')
            print(f"Registration error: {e}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Log out current user
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Main dashboard showing user statistics and due cards.
    user_id = current_user.user.user_id
    
    # Get user statistics
    stats = analytics_service.get_user_statistics(user_id)
    
    # Get weekly forecast
    forecast = analytics_service.get_weekly_forecast(user_id, days=7)
    
    # Get user's rank
    rank_info = leaderboard_service.get_user_rank(user_id)
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         forecast=forecast,
                         rank=rank_info)

@app.route('/review')
@login_required
def review():
    """
    Flashcard review session page.
    Gets cards due for review and presents them to user.
    """
    user_id = current_user.user.user_id
    
    # Get user's daily goal
    stats = analytics_service.get_user_statistics(user_id)
    daily_goal = stats.get('daily_goal', 20)
    
    # Get due cards (limited by daily goal)
    due_cards = flashcard_service.get_due_cards(user_id, limit=daily_goal)
    
    if not due_cards:
        flash('No cards due for review! Great job staying on top of your studies.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('review.html', cards=due_cards)

@app.route('/api/review_card', methods=['POST'])
@login_required
def review_card():
    # API endpoint to process card review.
    data = request.get_json()
    card_id = data.get('card_id')
    score = data.get('score')
    
    if not card_id or not score:
        return jsonify({'success': False, 'error': 'Missing card_id or score'}), 400
    
    if score not in [1, 2, 3, 4]:
        return jsonify({'success': False, 'error': 'Invalid score'}), 400
    
    # Update card
    success = flashcard_service.update_card_after_review(card_id, score)
    
    if success:
        # Award points based on score
        points_earned = score * 10  # 10, 20, 30, or 40 points
        
        # Update user points and streak
        user_id = current_user.user.user_id
        current_user.user.add_points(points_earned)
        current_user.user.update_streak(db_manager)
        analytics_service.update_user_streak(user_id)
        
        return jsonify({
            'success': True,
            'points_earned': points_earned,
            'new_total': current_user.user.total_points
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to update card'}), 500

@app.route('/leaderboard')
@login_required
def leaderboard():
    """
    Leaderboard page showing top users.
    Uses mergesort algorithm for O(n log n) sorting.
    """
    # Get top 10 users
    top_users = leaderboard_service.get_ranked_leaderboard(limit=10)
    
    # Get current user's rank
    user_id = current_user.user.user_id
    user_rank = leaderboard_service.get_user_rank(user_id)
    
    return render_template('leaderboard.html', 
                         top_users=top_users,
                         user_rank=user_rank)

@app.route('/sets')
@login_required
def sets():
    """
    Page showing user's flashcard sets.
    """
    user_id = current_user.user.user_id
    
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get all sets for this user
        cursor.execute('''
            SELECT 
                s.SetID,
                s.SetName,
                s.CreationDate,
                COUNT(f.CardID) as card_count,
                SUM(CASE WHEN f.IsMastered = 1 THEN 1 ELSE 0 END) as mastered_count
            FROM FlashcardSet s
            LEFT JOIN Flashcard f ON s.SetID = f.SetID AND f.UserID = ?
            WHERE s.UserID = ? OR s.UserID IS NULL
            GROUP BY s.SetID
            ORDER BY s.CreationDate DESC
        ''', (user_id, user_id))
        
        sets_data = []
        for row in cursor.fetchall():
            sets_data.append({
                'set_id': row[0],
                'set_name': row[1],
                'creation_date': row[2],
                'card_count': row[3],
                'mastered_count': row[4]
            })
        
        return render_template('sets.html', sets=sets_data)
        
    except Exception as e:
        print(f"Error loading sets: {e}")
        flash('Error loading flashcard sets', 'error')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


def initialize_sample_data():
    """
    Initializes database with sample vocabulary data.
    Only runs if VocabularyWord table is empty.
    """
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check if we already have vocabulary
        cursor.execute('SELECT COUNT(*) FROM VocabularyWord')
        if cursor.fetchone()[0] > 0:
            print("✓ Vocabulary data already exists")
            return
        
        # Sample Arabic vocabulary
        sample_vocab = [
            ('كتاب', 'book', 'General Nouns'),
            ('قلم', 'pen', 'General Nouns'),
            ('مدرسة', 'school', 'General Nouns'),
            ('بيت', 'house', 'General Nouns'),
            ('ماء', 'water', 'General Nouns'),
            ('طعام', 'food', 'General Nouns'),
            ('يذهب', 'to go', 'Verbs'),
            ('يأكل', 'to eat', 'Verbs'),
            ('يشرب', 'to drink', 'Verbs'),
            ('يكتب', 'to write', 'Verbs'),
            ('كبير', 'big', 'Adjectives'),
            ('صغير', 'small', 'Adjectives'),
            ('جميل', 'beautiful', 'Adjectives'),
            ('البصير', 'the All-Seeing', 'Quranic'),
            ('السميع', 'the All-Hearing', 'Quranic'),
            ('العليم', 'the All-Knowing', 'Quranic'),
            ('الخالق', 'the Creator', 'Quranic'),
            ('رب', 'Lord', 'Quranic')
        ]
        
        cursor.executemany('''
            INSERT INTO VocabularyWord (ArabicTerm, EnglishTranslation, Category)
            VALUES (?, ?, ?)
        ''', sample_vocab)
        
        # Create a default "Basic Arabic" set
        cursor.execute('''
            INSERT INTO FlashcardSet (UserID, SetName)
            VALUES (NULL, 'Basic Arabic Vocabulary')
        ''')
        
        conn.commit()
        print(f"✓ Initialized {len(sample_vocab)} sample vocabulary words")
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 50)
    print("Arabic Learning App - Starting...")
    print("=" * 50)
    
    # Initialize sample data
    initialize_sample_data()
    
    print("\n✓ Application ready!")
    print("➜ Open your browser and go to: http://127.0.0.1:5000")
    print("=" * 50)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
