"""
Rewards routes - Redeem, Coins
"""

from flask import Blueprint, render_template, session
from models.reward import get_user_coins

rewards_bp = Blueprint('rewards', __name__)

@rewards_bp.route('/')
def redeem():
    """View redeem page."""
    user_id = session.get('user_id')
    user_coins = get_user_coins(user_id)
    
    # DEBUG: Print to terminal to see what's happening
    print(f"DEBUG: user_id from session = {user_id}")
    print(f"DEBUG: coins retrieved = {user_coins}")
    
    # List of rewards (can be moved to database later)
    rewards = [
        {'id': 1, 'name': 'Welcome Gift', 'price': 200, 'image': 'giftbox.svg'},
        {'id': 2, 'name': 'Tote Bag', 'price': 500, 'image': 'bulb.svg'},
        {'id': 3, 'name': 'Bottled Water (1L)', 'price': 1000, 'image': 'giftbox.svg'},
        {'id': 4, 'name': 'Wallowing Willow', 'price': 1500, 'image': 'bulb.svg'},
        {'id': 5, 'name': 'Mystery Item (1 of 3)', 'price': 2000, 'image': 'giftbox.svg'},
        {'id': 6, 'name': 'iPhone 8 Plus', 'price': 3000, 'image': 'bulb.svg'},
    ]
    
    return render_template('rewards/redeem.html', coins=user_coins, rewards=rewards)