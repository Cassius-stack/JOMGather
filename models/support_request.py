"""
Support Request model - Support Swaps (Micro-Assistance)
"""

from datetime import datetime

class SupportRequest:
    """Support Swap / Micro-Assistance Request class."""
    
    # Predefined request types for safety
    VALID_REQUEST_TYPES = [
        'organize_photos',
        'organize_books',
        'pickup_item',
        'setup_device',
        'walk_pet',
        'water_plants',
        'change_lightbulb',
        'grocery_help',
        'other'
    ]
    
    def __init__(self, request_id=None, elder_id=None, student_id=None,
                 request_type=None, description=None, status='pending',
                 estimated_duration=30, created_at=None):
        self._request_id = request_id
        self._elder_id = elder_id
        self._student_id = student_id
        self._request_type = request_type
        self._description = description
        self._status = status  # 'pending', 'accepted', 'in_progress', 'completed', 'declined'
        self._estimated_duration = estimated_duration  # in minutes, max 30
        self._created_at = created_at or datetime.now()
        self._completed_at = None
    
    @property
    def request_id(self):
        return self._request_id
    
    @property
    def request_type(self):
        return self._request_type
    
    @request_type.setter
    def request_type(self, value):
        if value not in self.VALID_REQUEST_TYPES:
            raise ValueError(f"Invalid request type. Must be one of {self.VALID_REQUEST_TYPES}")
        self._request_type = value
    
    @property
    def status(self):
        return self._status
    
    @property
    def estimated_duration(self):
        return self._estimated_duration
    
    @estimated_duration.setter
    def estimated_duration(self, value):
        if value > 30:
            raise ValueError("Support swaps must be under 30 minutes")
        if value < 5:
            raise ValueError("Minimum duration is 5 minutes")
        self._estimated_duration = value
    
    def accept(self):
        """Accept the support request."""
        self._status = 'accepted'
    
    def decline(self):
        """Decline the support request."""
        self._status = 'declined'
    
    def start(self):
        """Mark request as in progress."""
        self._status = 'in_progress'
    
    def complete(self):
        """Mark request as completed."""
        self._status = 'completed'
        self._completed_at = datetime.now()
    
    def to_dict(self):
        """Convert request to dictionary."""
        return {
            'request_id': self._request_id,
            'elder_id': self._elder_id,
            'student_id': self._student_id,
            'request_type': self._request_type,
            'description': self._description,
            'status': self._status,
            'estimated_duration': self._estimated_duration,
            'created_at': str(self._created_at),
            'completed_at': str(self._completed_at) if self._completed_at else None
        }
    
    def __repr__(self):
        return f"<SupportRequest {self._request_id} - {self._request_type} ({self._status})>"
