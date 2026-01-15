"""
Skill model - Skills Marketplace
"""

from datetime import datetime

class Skill:
    """Skill class for the Skills Marketplace."""
    
    def __init__(self, skill_id=None, name=None, category=None, description=None):
        self._skill_id = skill_id
        self._name = name
        self._category = category  # e.g., 'digital', 'craft', 'cooking', 'music'
        self._description = description
    
    @property
    def skill_id(self):
        return self._skill_id
    
    @property
    def name(self):
        return self._name
    
    @property
    def category(self):
        return self._category
    
    def to_dict(self):
        """Convert skill to dictionary."""
        return {
            'skill_id': self._skill_id,
            'name': self._name,
            'category': self._category,
            'description': self._description
        }


class UserSkill:
    """Association between User and Skill - what skills a user has or wants to learn."""
    
    def __init__(self, user_id=None, skill_id=None, skill_type=None, proficiency=None):
        self._user_id = user_id
        self._skill_id = skill_id
        self._skill_type = skill_type  # 'offering' or 'seeking'
        self._proficiency = proficiency  # 'beginner', 'intermediate', 'expert'
    
    @property
    def skill_type(self):
        return self._skill_type
    
    @skill_type.setter
    def skill_type(self, value):
        if value not in ['offering', 'seeking']:
            raise ValueError("Skill type must be 'offering' or 'seeking'")
        self._skill_type = value


class SkillMatch:
    """Match between two users for skill exchange."""
    
    def __init__(self, match_id=None, requester_id=None, provider_id=None,
                 skill_id=None, status='pending', scheduled_date=None):
        self._match_id = match_id
        self._requester_id = requester_id
        self._provider_id = provider_id
        self._skill_id = skill_id
        self._status = status  # 'pending', 'accepted', 'declined', 'completed'
        self._scheduled_date = scheduled_date
        self._created_at = datetime.now()
    
    @property
    def match_id(self):
        return self._match_id
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        valid_statuses = ['pending', 'accepted', 'declined', 'completed']
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        self._status = value
    
    def accept(self):
        """Accept the skill match request."""
        self._status = 'accepted'
    
    def decline(self):
        """Decline the skill match request."""
        self._status = 'declined'
    
    def complete(self):
        """Mark the skill exchange as completed."""
        self._status = 'completed'
    
    def to_dict(self):
        """Convert match to dictionary."""
        return {
            'match_id': self._match_id,
            'requester_id': self._requester_id,
            'provider_id': self._provider_id,
            'skill_id': self._skill_id,
            'status': self._status,
            'scheduled_date': str(self._scheduled_date) if self._scheduled_date else None,
            'created_at': str(self._created_at)
        }
