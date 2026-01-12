"""
Profile model - User profile with interests and availability
"""

class Profile:
    """User profile with interests and social information."""
    
    def __init__(self, profile_id=None, user_id=None, bio=None, profile_picture=None,
                 interests=None, availability=None):
        self._profile_id = profile_id
        self._user_id = user_id
        self._bio = bio
        self._profile_picture = profile_picture
        self._interests = interests or []
        self._availability = availability or {}  # e.g., {'monday': '9am-5pm'}
    
    @property
    def profile_id(self):
        return self._profile_id
    
    @property
    def user_id(self):
        return self._user_id
    
    @property
    def bio(self):
        return self._bio
    
    @bio.setter
    def bio(self, value):
        if len(value) > 500:
            raise ValueError("Bio cannot exceed 500 characters")
        self._bio = value
    
    @property
    def interests(self):
        return self._interests
    
    def add_interest(self, interest):
        """Add an interest to the profile."""
        if interest not in self._interests:
            self._interests.append(interest)
    
    def remove_interest(self, interest):
        """Remove an interest from the profile."""
        if interest in self._interests:
            self._interests.remove(interest)
    
    @property
    def availability(self):
        return self._availability
    
    def set_availability(self, day, time_slot):
        """Set availability for a specific day."""
        self._availability[day] = time_slot
    
    def get_matching_interests(self, other_profile):
        """Find common interests with another profile."""
        return list(set(self._interests) & set(other_profile.interests))
    
    def to_dict(self):
        """Convert profile to dictionary."""
        return {
            'profile_id': self._profile_id,
            'user_id': self._user_id,
            'bio': self._bio,
            'profile_picture': self._profile_picture,
            'interests': self._interests,
            'availability': self._availability
        }
    
    def __repr__(self):
        return f"<Profile user_id={self._user_id}>"
