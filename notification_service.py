from datetime import datetime, time
from typing import List, Dict, Optional
import sqlite3

class NotificationService:
    """
    Manages notification generation and scheduling for users.
    Handles daily reminders and achievement notifications.
    """
    
    def __init__(self, db_manager):
        # Initialize notification service.
        self.db_manager = db_manager
    
    def check_daily_reminder(self, user_id: int) -> Optional[Dict]:
        # Checks if user should receive daily reminder based on their notification time.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get user's notification preference
            cursor.execute('''
                SELECT NotificationTime FROM User WHERE UserID = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            notification_time = result[0]
            current_time = datetime.now().strftime('%H:%M')
            
            # Check if current time is equal to notification time
            if notification_time == current_time:
                # Get cards due today
                cursor.execute('''
                    SELECT COUNT(*) FROM Flashcard
                    WHERE UserID = ? AND date(NextReviewDate) <= date('now')
                ''', (user_id,))
                
                cards_due = cursor.fetchone()[0]
                
                if cards_due > 0:
                    return {
                        'type': 'daily_reminder',
                        'message': f'You have {cards_due} cards due for review!',
                        'cards_due': cards_due
                    }
            return None
            
        except sqlite3.Error as e:
            print(f"Error checking reminder: {e}")
            return None
        finally:
            conn.close()
    
    def generate_completion_notification(self, user_id: int, session_stats: Dict) -> Dict:
        # Generates notification after completing review session.
        cards_reviewed = session_stats.get('cards_reviewed', 0)
        points_earned = session_stats.get('points_earned', 0)
        
        # Checks if user met their daily goal
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DailyCardGoal FROM User WHERE UserID = ?
            ''', (user_id,))
            
            daily_goal = cursor.fetchone()[0]
            
            if cards_reviewed >= daily_goal:
                message = f"🎉 Congratulations! You completed your daily goal of {daily_goal} cards and earned {points_earned} points!"
                notification_type = 'goal_met'
            else:
                remaining = daily_goal - cards_reviewed
                message = f"Good work! You reviewed {cards_reviewed} cards and earned {points_earned} points. {remaining} cards remaining to meet your daily goal."
                notification_type = 'progress_update'
            
            return {
                'type': notification_type,
                'message': message,
                'cards_reviewed': cards_reviewed,
                'points_earned': points_earned
            }
            
        except sqlite3.Error as e:
            print(f"Error generating notification: {e}")
            return {
                'type': 'error',
                'message': 'Session completed but unable to calculate progress'
            }
        finally:
            conn.close()
    
    def check_streak_milestone(self, user_id: int) -> Optional[Dict]:
        # Checks if user reached a streak milestone.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT CurrentStreak FROM User WHERE UserID = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            streak = result[0]
            milestones = [7, 14, 30, 60, 100, , 200, 365]
            
            if streak in milestones:
                # Generates milestone message (e.g. 2 weeks, 1 month, 1 year)
                return {
                    'type': 'streak_milestone',
                    'message': f'🔥 Amazing! You reached a {streak}-day streak!',
                    'streak': streak
                }
            
            return None
            
        except sqlite3.Error as e:
            print(f"Error checking milestone: {e}")
            return None
        finally:
            conn.close()
    
    def check_mastery_achievement(self, user_id: int) -> Optional[Dict]:
        # Checks if user reached mastery milestones.
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM Flashcard
                WHERE UserID = ? AND IsMastered = 1
            ''', (user_id,))
            
            mastered_count = cursor.fetchone()[0]
            achievement_levels = [10, 25, 50, 100, 250, 500]
            
            if mastered_count in achievement_levels:
                return {
                    'type': 'mastery_achievement',
                    'message': f'🏆 Congratulations! You mastered {mastered_count} words!',
                    'mastered_count': mastered_count
                }
            return None
            
        except sqlite3.Error as e:
            print(f"Error checking mastery: {e}")
            return None
        finally:
            conn.close()
    
    def get_encouragement_message(self, user_id: int) -> str:
        # Generates encouraging message based on user progress.
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            # Get user stats
            cursor.execute('''
                SELECT 
                    u.CurrentStreak,
                    COUNT(f.CardID) as total_cards,
                    SUM(CASE WHEN f.IsMastered = 1 THEN 1 ELSE 0 END) as mastered
                FROM User u
                LEFT JOIN Flashcard f ON u.UserID = f.UserID
                WHERE u.UserID = ?
                GROUP BY u.UserID
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return "Keep up the great work! 🌟"
            
            streak, total_cards, mastered = result
            
            # Generate feedback message
            if streak == 0:
                return "Start your learning journey today! 🚀"
            elif streak < 7:
                return f"You're on a {streak}-day streak! Keep it going! 💪"
            elif mastered == 0:
                return "First cards are the hardest - you've got this! 🎯"
            elif mastered and total_cards:
                percentage = (mastered / total_cards) * 100
                if percentage < 25:
                    return "Great start! Every word learned is progress! 📚"
                elif percentage < 50:
                    return "You're making solid progress! Keep going! 🌱"
                elif percentage < 75:
                    return "Impressive progress! You're really learning! 🌟"
                else:
                    return "Outstanding! You're nearly fluent! 🏆"
            
            return "Keep up the excellent work! 🎉"
            
        except sqlite3.Error as e:
            print(f"Error: {e}")
            return "Keep learning! 📖"
        finally:
            conn.close()
    
    def schedule_reminder(self, user_id: int, reminder_time: str) -> bool:
        # Updates user's reminder notification time.
        try:
            hours, minutes = map(int, reminder_time.split(':'))
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                print("Invalid time format")
                return False
        except ValueError:
            print("Time must be in HH:MM format")
            return False
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE User
                SET NotificationTime = ?
                WHERE UserID = ?
            ''', (reminder_time, user_id))
            
            conn.commit()
            print(f"✓ Reminder scheduled for {reminder_time}")
            return True
            
        except sqlite3.Error as e:
            print(f"Error scheduling reminder: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_all_due_reminders(self) -> List[Dict]:
        # Gets all users who should receive reminders at current time.
        current_time = datetime.now().strftime('%H:%M')
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    u.UserID,
                    ua.Username,
                    COUNT(f.CardID) as cards_due
                FROM User u
                JOIN UserAccount ua ON u.UserID = ua.UserID
                LEFT JOIN Flashcard f ON u.UserID = f.UserID 
                    AND date(f.NextReviewDate) <= date('now')
                WHERE u.NotificationTime = ?
                GROUP BY u.UserID
                HAVING cards_due > 0
            ''', (current_time,))
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append({
                    'user_id': row[0],
                    'username': row[1],
                    'cards_due': row[2],
                    'message': f'Hello {row[1]}! You have {row[2]} cards waiting for review.'
                })
            
            return reminders
            
        except sqlite3.Error as e:
            print(f"Error getting reminders: {e}")
            return []
        finally:
            conn.close()
