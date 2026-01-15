"""
User model - Base class for Youth and Senior users
"""

class User:
    """Base User class for JOMGather platform."""
    
    def __init__(self, user_id=None, username=None, email=None, password_hash=None, 
                 user_type=None, created_at=None):
        self._user_id = user_id
        self._username = username
        self._email = email
        self._password_hash = password_hash
        self._user_type = user_type  # 'youth' or 'senior'
        self._created_at = created_at
    
    # Getters and Setters (Encapsulation)
    @property
    def user_id(self):
        return self._user_id
    
    @property
    def username(self):
        return self._username
    
    @username.setter
    def username(self, value):
        if len(value) < 3:
            raise ValueError("Username must be at least 3 characters long")
        self._username = value
    
    @property
    def email(self):
        return self._email
    
    @email.setter
    def email(self, value):
        if '@' not in value:
            raise ValueError("Invalid email address")
        self._email = value
    
    @property
    def user_type(self):
        return self._user_type
    
    @user_type.setter
    def user_type(self, value):
        if value not in ['youth', 'senior']:
            raise ValueError("User type must be 'youth' or 'senior'")
        self._user_type = value
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'user_id': self._user_id,
            'username': self._username,
            'email': self._email,
            'user_type': self._user_type,
            'created_at': self._created_at
        }
    
    def __repr__(self):
        return f"<User {self._username} ({self._user_type})>"


class Youth(User):
    """Youth user class - inherits from User."""
    
    def __init__(self, school=None, grade=None, volunteer_hours=0, **kwargs):
        super().__init__(**kwargs)
        self._user_type = 'youth'
        self._school = school
        self._grade = grade
        self._volunteer_hours = volunteer_hours
    
    @property
    def school(self):
        return self._school
    
    @school.setter
    def school(self, value):
        self._school = value
    
    @property
    def volunteer_hours(self):
        return self._volunteer_hours
    
    def add_volunteer_hours(self, hours):
        """Add volunteer hours to the youth's record."""
        if hours < 0:
            raise ValueError("Hours cannot be negative")
        self._volunteer_hours += hours
    
    def get_certificate_status(self):
        """Check if youth qualifies for certificate (min threshold)."""
        CERTIFICATE_THRESHOLD = 10  # hours
        return self._volunteer_hours >= CERTIFICATE_THRESHOLD


class Senior(User):
    """Senior user class - inherits from User."""
    
    def __init__(self, age=None, location=None, languages=None, peak_hours=None, **kwargs):
        super().__init__(**kwargs)
        self._user_type = 'senior'
        self._age = age
        self._location = location
        self._languages = languages or []
        self._peak_hours = peak_hours  # e.g., "9am-12pm"
    
    @property
    def age(self):
        return self._age
    
    @age.setter
    def age(self, value):
        if value < 55:
            raise ValueError("Senior must be at least 55 years old")
        self._age = value
    
    @property
    def languages(self):
        return self._languages
    
    def add_language(self, language):
        """Add a language the senior can speak."""
        if language not in self._languages:
            self._languages.append(language)
    
    @property
    def peak_hours(self):
        return self._peak_hours
    
    @peak_hours.setter
    def peak_hours(self, value):
        self._peak_hours = value
