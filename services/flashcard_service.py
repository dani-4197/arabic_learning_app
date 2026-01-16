from collections import deque

class ReviewQueue:
    """
    Queue (FIFO) for managing flashcard review order
    Demonstrates understanding of queue operations
    """
    
    def __init__(self):
        """
        Uses Python's deque for O(1) operations at both ends
        Superior to list which has O(n) for pop(0)
        """
        self._queue = deque()
    
    def enqueue(self, card):
        """
        Adds card to end of queue
        
        Time complexity: O(1)
        """
        if card is None:
            raise ValueError("Cannot enqueue None")
        
        self._queue.append(card)
    
    def dequeue(self):
        """
        Removes and returns card from front of queue
        
        Time complexity: O(1)
        Returns None if queue is empty (defensive programming)
        """
        if self.is_empty():
            return None
        
        return self._queue.popleft()
    
    def peek(self):
        """
        Views next card without removing
        
        Time complexity: O(1)
        """
        if self.is_empty():
            return None
        
        return self._queue[0]
    
    def is_empty(self):
        """Checks if queue has no elements"""
        return len(self._queue) == 0
    
    def size(self):
        """Returns number of cards in queue"""
        return len(self._queue)
    
    def clear(self):
        """Empties the queue"""
        self._queue.clear()
