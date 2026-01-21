class LeaderboardSorter:
    """
    Implements Mergesort (O(n log n)) for leaderboard sorting
    More efficient than bubble/insertion sort (O(n²))
    """
    
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
