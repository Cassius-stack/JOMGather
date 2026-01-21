"""
Rewards routes - Redeem, Coins
"""

from flask import Blueprint, render_template
from models.reward import get_user_coins

rewards_bp = Blueprint('rewards', __name__)

@rewards_bp.route('/redeem')
def redeem():
    """View redeem page."""
    user_id = 1  # TODO: Get from session after login
    user_coins = get_user_coins(user_id)
    return render_template('rewards/redeem.html', coins=user_coins)