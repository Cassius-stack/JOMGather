"""
Reward model - Points, Badges, Vouchers
"""

from datetime import datetime

class Points:
    """Points tracking for a user."""
    
    def __init__(self, user_id=None, total_points=0, weekly_points=0, 
                 lifetime_points=0):
        self._user_id = user_id
        self._total_points = total_points  # Current redeemable points
        self._weekly_points = weekly_points  # Points earned this week
        self._lifetime_points = lifetime_points  # All-time total
    
    @property
    def total_points(self):
        return self._total_points
    
    def add_points(self, amount, reason=None):
        """Add points to user's balance."""
        if amount < 0:
            raise ValueError("Points must be positive")
        self._total_points += amount
        self._weekly_points += amount
        self._lifetime_points += amount
    
    def redeem_points(self, amount):
        """Redeem points for rewards."""
        if amount > self._total_points:
            raise ValueError("Not enough points")
        self._total_points -= amount
    
    def reset_weekly(self):
        """Reset weekly points (called at end of week)."""
        self._weekly_points = 0
    
    def to_dict(self):
        """Convert points to dictionary."""
        return {
            'user_id': self._user_id,
            'total_points': self._total_points,
            'weekly_points': self._weekly_points,
            'lifetime_points': self._lifetime_points
        }


class Badge:
    """Badge/Achievement class."""
    
    def __init__(self, badge_id=None, name=None, description=None, 
                 icon=None, requirement=None):
        self._badge_id = badge_id
        self._name = name
        self._description = description
        self._icon = icon
        self._requirement = requirement  # e.g., "Complete 5 meetups"
    
    @property
    def badge_id(self):
        return self._badge_id
    
    @property
    def name(self):
        return self._name
    
    def to_dict(self):
        """Convert badge to dictionary."""
        return {
            'badge_id': self._badge_id,
            'name': self._name,
            'description': self._description,
            'icon': self._icon,
            'requirement': self._requirement
        }


class Voucher:
    """Voucher/Reward that can be redeemed with points."""
    
    def __init__(self, voucher_id=None, name=None, description=None,
                 points_required=None, quantity_available=None, expiry_date=None):
        self._voucher_id = voucher_id
        self._name = name
        self._description = description
        self._points_required = points_required
        self._quantity_available = quantity_available
        self._expiry_date = expiry_date
    
    @property
    def voucher_id(self):
        return self._voucher_id
    
    @property
    def name(self):
        return self._name
    
    @property
    def points_required(self):
        return self._points_required
    
    @property
    def is_available(self):
        """Check if voucher is still available."""
        if self._quantity_available is not None and self._quantity_available <= 0:
            return False
        if self._expiry_date and datetime.now() > self._expiry_date:
            return False
        return True
    
    def redeem(self):
        """Redeem one voucher (decrease quantity)."""
        if not self.is_available:
            raise ValueError("Voucher is no longer available")
        if self._quantity_available is not None:
            self._quantity_available -= 1
    
    def to_dict(self):
        """Convert voucher to dictionary."""
        return {
            'voucher_id': self._voucher_id,
            'name': self._name,
            'description': self._description,
            'points_required': self._points_required,
            'quantity_available': self._quantity_available,
            'expiry_date': str(self._expiry_date) if self._expiry_date else None,
            'is_available': self.is_available
        }
