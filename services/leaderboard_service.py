class LeaderboardSorter:
    # Sorts the leaderboard using mergesort rather than Python's built-in sorted(); the built-in would technically work ok, but I used my own adaptation for a leaderboard that could grow to hundreds of users - the guaranteed O(n log n) performance is better than a sort with unpredictable worst-case behaviour
    
    def mergesort_leaderboard(self, users, sort_key="total_points"):
        # Base case — a list of 0 or 1 users is already sorted, so return it as-is - stops the recursion from going infinitely.
        if len(users) <= 1:
            return users
        
        # Split down the middle, sort each half independently, then merge, the recursion keeps halving until every sub-list hits the base case.
        mid = len(users) // 2
        left_sorted  = self.mergesort_leaderboard(users[:mid],  sort_key)
        right_sorted = self.mergesort_leaderboard(users[mid:], sort_key)
        
        return self._merge(left_sorted, right_sorted, sort_key)
    
    def _merge(self, left, right, sort_key):
        # Walk both sorted halves simultaneously, always picking the larger value first so the result comes out in descending order (highest points first).
        result = []
        i = j = 0
        
        while i < len(left) and j < len(right):
            if left[i][sort_key] >= right[j][sort_key]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        
        # Once one side is exhausted, append whatever's left in the other - already sorted so no further comparison is needed.
        result.extend(left[i:])
        result.extend(right[j:])
        
        return result
    
    def sort_by_multiple_criteria(self, users):
        # Same structure as mergesort_leaderboard but delegates to _merge_multi_key which adds a streak tiebreaker for users with equal points.
        if len(users) <= 1:
            return users
        
        mid = len(users) // 2
        left  = self.sort_by_multiple_criteria(users[:mid])
        right = self.sort_by_multiple_criteria(users[mid:])
        
        return self._merge_multi_key(left, right)
    
    def _merge_multi_key(self, left, right):
        result = []
        i = j = 0
        
        while i < len(left) and j < len(right):
            if left[i]['total_points'] > right[j]['total_points']:
                result.append(left[i])
                i += 1
            elif left[i]['total_points'] < right[j]['total_points']:
                result.append(right[j])
                j += 1
            else:
                # Points are equal - use current streak as the tiebreaker so consistent daily reviewers rank above users who did a lot of reviews in one burst
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
    # Retrieves leaderboard data from the database and passes it through, LeaderboardSorter before returning it to the route
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.sorter = LeaderboardSorter()
    
    def get_ranked_leaderboard(self, limit=10):
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Only fetch users who have at least 1 point - avoids showing empty accounts that registered but never reviewed any cards
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
            
            users = []
            for row in results:
                users.append({
                    'username': row[0],
                    'total_points': row[1],
                    'current_streak': row[2],
                    'longest_streak': row[3]
                })
            
            # Run through the custom mergesort with multi-key tiebreaking, then slice to the top N rather than using SQL LIMIT - this way the sort order is always controlled by our algorithm, not SQLite.
            sorted_users = self.sorter.sort_by_multiple_criteria(users)
            return sorted_users[:limit]
            
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_rank(self, user_id):
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
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
            
            cursor.execute('''
                SELECT COUNT(*) FROM User WHERE TotalPoints > 0
            ''')
            total_users = cursor.fetchone()[0]
            
            # Count how many users sit above this one using the same tiebreaking rule as the sort — points first, then streak, adding 1 gives a 1-based rank rather than 0-based
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
