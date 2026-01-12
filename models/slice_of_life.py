"""
Slice of Life model - Collaborative storytelling displays
"""

from datetime import datetime

class SliceOfLife:
    """Slice of Life display - collaborative storytelling between pairs."""
    
    def __init__(self, display_id=None, pair_id=None, prompt_image=None,
                 youth_story=None, senior_story=None, is_public=True,
                 created_at=None):
        self._display_id = display_id
        self._pair_id = pair_id
        self._prompt_image = prompt_image
        self._youth_story = youth_story
        self._senior_story = senior_story
        self._is_public = is_public
        self._created_at = created_at or datetime.now()
        self._likes = 0
        self._comments = []
    
    @property
    def display_id(self):
        return self._display_id
    
    @property
    def prompt_image(self):
        return self._prompt_image
    
    @property
    def youth_story(self):
        return self._youth_story
    
    @youth_story.setter
    def youth_story(self, value):
        if len(value) > 2000:
            raise ValueError("Story cannot exceed 2000 characters")
        self._youth_story = value
    
    @property
    def senior_story(self):
        return self._senior_story
    
    @senior_story.setter
    def senior_story(self, value):
        if len(value) > 2000:
            raise ValueError("Story cannot exceed 2000 characters")
        self._senior_story = value
    
    @property
    def is_complete(self):
        """Check if both stories have been submitted."""
        return self._youth_story is not None and self._senior_story is not None
    
    @property
    def likes(self):
        return self._likes
    
    def like(self):
        """Add a like to the display."""
        self._likes += 1
    
    def add_comment(self, comment):
        """Add a comment to the display."""
        self._comments.append(comment)
    
    def to_dict(self):
        """Convert display to dictionary."""
        return {
            'display_id': self._display_id,
            'pair_id': self._pair_id,
            'prompt_image': self._prompt_image,
            'youth_story': self._youth_story,
            'senior_story': self._senior_story,
            'is_public': self._is_public,
            'is_complete': self.is_complete,
            'likes': self._likes,
            'comment_count': len(self._comments),
            'created_at': str(self._created_at)
        }
    
    def __repr__(self):
        status = "complete" if self.is_complete else "in progress"
        return f"<SliceOfLife {self._display_id} ({status})>"
