"""
Community model - Interest communities and groups
"""

from datetime import datetime

class Community:
    """Community/Interest group class."""
    
    def __init__(self, community_id=None, name=None, description=None,
                 category=None, created_by=None, created_at=None):
        self._community_id = community_id
        self._name = name
        self._description = description
        self._category = category
        self._created_by = created_by
        self._created_at = created_at or datetime.now()
        self._members = []
    
    @property
    def community_id(self):
        return self._community_id
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        if len(value) < 3:
            raise ValueError("Community name must be at least 3 characters")
        self._name = value
    
    @property
    def description(self):
        return self._description
    
    @description.setter
    def description(self, value):
        if len(value) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        self._description = value
    
    @property
    def members(self):
        return self._members
    
    def add_member(self, user_id):
        """Add a member to the community."""
        if user_id not in self._members:
            self._members.append(user_id)
    
    def remove_member(self, user_id):
        """Remove a member from the community."""
        if user_id in self._members:
            self._members.remove(user_id)
    
    def get_member_count(self):
        """Get total number of members."""
        return len(self._members)
    
    def to_dict(self):
        """Convert community to dictionary."""
        return {
            'community_id': self._community_id,
            'name': self._name,
            'description': self._description,
            'category': self._category,
            'created_by': self._created_by,
            'created_at': str(self._created_at),
            'member_count': len(self._members)
        }


class ForumPost:
    """AskAGrandfriend forum post class."""
    
    def __init__(self, post_id=None, author_id=None, title=None, content=None,
                 created_at=None):
        self._post_id = post_id
        self._author_id = author_id
        self._title = title
        self._content = content
        self._created_at = created_at or datetime.now()
        self._answers = []
        self._likes = 0
    
    @property
    def post_id(self):
        return self._post_id
    
    @property
    def title(self):
        return self._title
    
    def add_answer(self, answer):
        """Add an answer to the post."""
        self._answers.append(answer)
    
    def like(self):
        """Increment like count."""
        self._likes += 1
    
    def get_answer_count(self):
        """Get number of answers."""
        return len(self._answers)
    
    def to_dict(self):
        """Convert post to dictionary."""
        return {
            'post_id': self._post_id,
            'author_id': self._author_id,
            'title': self._title,
            'content': self._content,
            'created_at': str(self._created_at),
            'answer_count': len(self._answers),
            'likes': self._likes
        }
