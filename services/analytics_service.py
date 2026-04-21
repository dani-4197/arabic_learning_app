from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3

class AnalyticsService:
    """
    Handles analytics and progress tracking for users.
    Provides metrics for dashboard display and progress monitoring.
    """
    
    def __init__(self, db_manager):
        # Initialize analytics service.
        self.db_manager = db_manager
    
    def get_user_statistics(self, user_id: int) -> Dict:
        # Retrieves comprehensive statistics for a user.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Total cards
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard WHERE UserID = ?
            ''', (user_id,))
            total_cards = cursor.fetchone()[0]
            
            # Cards due today
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard 
                WHERE UserID = ? AND date(NextReviewDate) <= date('now')
            ''', (user_id,))
            cards_due = cursor.fetchone()[0]
            
            # Mastered cards (Box 5)
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard 
                WHERE UserID = ? AND IsMastered = 1
            ''', (user_id,))
            mastered_cards = cursor.fetchone()[0]
            
            # Cards by box level
            cursor.execute('''
                SELECT BoxLevel, COUNT(*) as count
                FROM Flashcard
                WHERE UserID = ?
                GROUP BY BoxLevel
                ORDER BY BoxLevel
            ''', (user_id,))
            
            box_distribution = {}
            for row in cursor.fetchall():
                box_distribution[f'box_{row[0]}'] = row[1]
            
            # Average recall percentage
            cursor.execute('''
                SELECT WeightedScore, TotalReviews
                FROM Flashcard
                WHERE UserID = ? AND TotalReviews > 0
            ''', (user_id,))
            
            total_weighted = 0
            total_reviews = 0
            for row in cursor.fetchall():
                weighted_score = row[0]
                reviews = row[1]
                # Normalize each card's score
                normalized = weighted_score + (reviews * 2)
                max_possible = reviews * 4
                total_weighted += normalized
                total_reviews += max_possible
            
            avg_recall = (total_weighted / total_reviews * 100) if total_reviews > 0 else 0
            
            # User preferences
            cursor.execute('''
                SELECT CurrentStreak, TotalPoints, DailyCardGoal, LongestStreak
                FROM User WHERE UserID = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            return {
                'total_cards': total_cards,
                'cards_due': cards_due,
                'mastered_cards': mastered_cards,
                'box_distribution': box_distribution,
                'average_recall': round(avg_recall, 1),
                'current_streak': user_data[0] if user_data else 0,
                'total_points': user_data[1] if user_data else 0,
                'daily_goal': user_data[2] if user_data else 20,
                'longest_streak': user_data[3] if user_data else 0
            }
            
        except sqlite3.Error as e:
            print(f"Error getting statistics: {e}")
            return {}
        finally:
            conn.close()
    
    def get_weekly_forecast(self, user_id: int, days: int = 7) -> List[Dict]:
        # Forecasts cards due for the next N days.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            forecast = []
            
            for day_offset in range(days):
                target_date = datetime.now() + timedelta(days=day_offset)
                date_str = target_date.strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT COUNT(*) FROM Flashcard
                    WHERE UserID = ? AND date(NextReviewDate) = date(?)
                ''', (user_id, date_str))
                
                count = cursor.fetchone()[0]
                
                forecast.append({
                    'date': date_str,
                    'day_name': target_date.strftime('%A'),
                    'cards_due': count
                })
            
            return forecast
            
        except sqlite3.Error as e:
            print(f"Error getting forecast: {e}")
            return []
        finally:
            conn.close()
    
    def update_user_streak(self, user_id: int) -> bool:
        """
        Updates user's study streak based on review activity.
        Streak increments if user reviewed cards today.
        Streak resets to 0 if user didn't review yesterday.
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Check if user reviewed any cards today
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard
                WHERE UserID = ? AND date(LastReviewed) = date('now')
            ''', (user_id,))
            
            reviewed_today = cursor.fetchone()[0] > 0
            
            if not reviewed_today:
                return False  # No activity today, don't update
            
            # Check if user reviewed yesterday
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard
                WHERE UserID = ? AND date(LastReviewed) = date('now', '-1 day')
            ''', (user_id,))
            
            reviewed_yesterday = cursor.fetchone()[0] > 0
            
            # Get current streak
            cursor.execute('''
                SELECT CurrentStreak, LongestStreak
                FROM User WHERE UserID = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            current_streak = result[0] if result else 0
            longest_streak = result[1] if result else 0
            
            # Update streak
            if reviewed_yesterday:
                new_streak = current_streak + 1
            else:
                new_streak = 1  # Start new streak
            
            # Update longest if necessary
            new_longest = max(longest_streak, new_streak)
            
            cursor.execute('''
                UPDATE User
                SET CurrentStreak = ?, LongestStreak = ?
                WHERE UserID = ?
            ''', (new_streak, new_longest, user_id))
            
            conn.commit()
            print(f"✓ Streak updated: {new_streak} days")
            return True
            
        except sqlite3.Error as e:
            print(f"Error updating streak: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def calculate_weighted_progress(self, user_id: int) -> float:
        # Calculates overall weighted progress percentage for user.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(WeightedScore), SUM(TotalReviews)
                FROM Flashcard
                WHERE UserID = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            total_weighted = result[0] if result[0] else 0
            total_reviews = result[1] if result[1] else 0
            
            if total_reviews == 0:
                return 0.0
            
            # Normalize score (worst possible = 0%, best possible = 100%)
            normalized_score = total_weighted + (total_reviews * 2)
            max_normalized = total_reviews * 4
            
            percentage = (normalized_score / max_normalized) * 100
            return round(percentage, 2)
            
        except sqlite3.Error as e:
            print(f"Error calculating progress: {e}")
            return 0.0
        finally:
            conn.close()
