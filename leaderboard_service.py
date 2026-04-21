class LeaderboardSorter:
    # Implements Mergesort (O(n log n)) for leaderboard sorting
    
    def mergesort_leaderboard(self, users, sort_key="total_points"):
        """
        Recursive mergesort implementation      
        Time complexity: O(n log n)
        Space complexity: O(n)
        """
        # Base case: lists of 0 or 1 element are already sorted
        if len(users) <= 1:
            return users
        
        # Split list in half
        mid = len(users) // 2
        left_half = users[:mid]
        right_half = users[mid:]
        
        # Recursively sort both halves
        left_sorted = self.mergesort_leaderboard(left_half, sort_key)
        right_sorted = self.mergesort_leaderboard(right_half, sort_key)
        
        # Merge sorted halves
        return self._merge(left_sorted, right_sorted, sort_key)
    
    def _merge(self, left, right, sort_key):
        """
        Merges two sorted lists into one sorted list
        Time complexity: O(len(left) + len(right))
        """
        result = []
        i = j = 0
        
        # Compare elements from both lists
        while i < len(left) and j < len(right):
            # Sort in DESCENDING order (highest scores first)
            if left[i][sort_key] >= right[j][sort_key]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        
        # Append remaining elements
        result.extend(left[i:])
        result.extend(right[j:])
        
        return result
    
    def sort_by_multiple_criteria(self, users):
        # Multi-key sort: Primary by points, secondary by streak
        if len(users) <= 1:
            return users
        
        mid = len(users) // 2
        left = self.sort_by_multiple_criteria(users[:mid])
        right = self.sort_by_multiple_criteria(users[mid:])
        
        return self._merge_multi_key(left, right)
    
    def _merge_multi_key(self, left, right):
        # Merges with tie-breaking
        result = []
        i = j = 0
        
        while i < len(left) and j < len(right):
            # Primary: total_points
            if left[i]['total_points'] > right[j]['total_points']:
                result.append(left[i])
                i += 1
            elif left[i]['total_points'] < right[j]['total_points']:
                result.append(right[j])
                j += 1
            else:
                # Tie-breaker: current_streak
                if left[i]['current_streak'] >= right[j]['current_streak']:
                    result.append(left[i])
                    i += 1
                else:
                    result.append(right[j])
                    j += 1
        
        result.extend(left[i:])
        result.extend(right[j:])
        
        return result


class LeaderboardService:
    """
    Service for managing leaderboard functionality.
    Uses LeaderboardSorter for ranking users.
    """
    
    def __init__(self, db_manager):
        # Initialize service with database manager and sorter
        self.db_manager = db_manager
        self.sorter = LeaderboardSorter()
    
    def get_ranked_leaderboard(self, limit=10):
        """
        Retrieves top users sorted by points and streak.
        Uses custom mergesort algorithm for sorting.
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get all users with their stats
            cursor.execute('''
                SELECT 
                    ua.Username,
                    u.TotalPoints,
                    u.CurrentStreak,
                    u.LongestStreak
                FROM User u
                JOIN UserAccount ua ON u.UserID = ua.UserID
                WHERE u.TotalPoints > 0
                ORDER BY u.TotalPoints DESC
            ''')
            
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            users = []
            for row in results:
                users.append({
                    'username': row[0],
                    'total_points': row[1],
                    'current_streak': row[2],
                    'longest_streak': row[3]
                })
            
            # Sort using custom mergesort
            sorted_users = self.sorter.sort_by_multiple_criteria(users)
            
            # Return top N users
            return sorted_users[:limit]
            
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_rank(self, user_id):
        """
        Gets the rank of a specific user on the leaderboard.
        Returns user's position and stats.
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Get user's stats
            cursor.execute('''
                SELECT 
                    ua.Username,
                    u.TotalPoints,
                    u.CurrentStreak
                FROM User u
                JOIN UserAccount ua ON u.UserID = ua.UserID
                WHERE u.UserID = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            # Get total users with points
            cursor.execute('''
                SELECT COUNT(*) FROM User WHERE TotalPoints > 0
            ''')
            total_users = cursor.fetchone()[0]
            
            # Get users ranked above this user
            cursor.execute('''
                SELECT COUNT(*) FROM User
                WHERE TotalPoints > ?
                   OR (TotalPoints = ? AND CurrentStreak > ?)
            ''', (user_data[1], user_data[1], user_data[2]))
            
            users_above = cursor.fetchone()[0]
            rank = users_above + 1
            
            return {
                'username': user_data[0],
                'total_points': user_data[1],
                'current_streak': user_data[2],
                'rank': rank,
                'total_users': total_users
            }
            
        except Exception as e:
            print(f"Error getting user rank: {e}")
            return None
        finally:
            conn.close()
