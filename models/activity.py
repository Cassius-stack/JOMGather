"""
Activity model - Activities, Challenges, Photo Streaks
"""

from datetime import datetime

class Activity:
    """Base Activity class."""
    
    def __init__(self, activity_id=None, title=None, description=None, 
                 activity_type=None, created_by=None, created_at=None):
        self._activity_id = activity_id
        self._title = title
        self._description = description
        self._activity_type = activity_type  # 'tiktok', 'puzzle', 'game', 'photo_streak'
        self._created_by = created_by
        self._created_at = created_at or datetime.now()
        self._participants = []
    
    @property
    def activity_id(self):
        return self._activity_id
    
    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        if len(value) < 3:
            raise ValueError("Title must be at least 3 characters")
        self._title = value
    
    @property
    def activity_type(self):
        return self._activity_type
    
    def add_participant(self, user_id):
        """Add a participant to the activity."""
        if user_id not in self._participants:
            self._participants.append(user_id)
    
    def get_participant_count(self):
        """Get number of participants."""
        return len(self._participants)
    
    def to_dict(self):
        """Convert activity to dictionary."""
        return {
            'activity_id': self._activity_id,
            'title': self._title,
            'description': self._description,
            'activity_type': self._activity_type,
            'created_by': self._created_by,
            'created_at': str(self._created_at),
            'participants': self._participants
        }


class PhotoStreak:
    """Photo Streak tracking between pairs."""
    
    def __init__(self, streak_id=None, user1_id=None, user2_id=None,
                 current_streak=0, longest_streak=0, last_photo_date=None):
        self._streak_id = streak_id
        self._user1_id = user1_id
        self._user2_id = user2_id
        self._current_streak = current_streak
        self._longest_streak = longest_streak
        self._last_photo_date = last_photo_date
    
    @property
    def current_streak(self):
        return self._current_streak
    
    def increment_streak(self):
        """Increment the streak by 1."""
        self._current_streak += 1
        if self._current_streak > self._longest_streak:
            self._longest_streak = self._current_streak
        self._last_photo_date = datetime.now()
    
    def reset_streak(self):
        """Reset the streak to 0."""
        self._current_streak = 0
    
    def get_streak_status(self):
        """Get current streak status."""
        return {
            'current': self._current_streak,
            'longest': self._longest_streak,
            'last_photo': str(self._last_photo_date) if self._last_photo_date else None
        }
