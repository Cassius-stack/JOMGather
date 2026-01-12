"""
Rewards routes - Leaderboard, Points, Vouchers
"""

from flask import Blueprint, render_template, request, redirect, url_for

rewards_bp = Blueprint('rewards', __name__)

@rewards_bp.route('/leaderboard')
def leaderboard():
    """View the leaderboard."""
    # TODO: Fetch top users from database
    return render_template('rewards/leaderboard.html')

@rewards_bp.route('/my-points')
def my_points():
    """View current user's points and badges."""
    # TODO: Fetch user's rewards from database
    return render_template('rewards/my_points.html')

@rewards_bp.route('/vouchers')
def vouchers():
    """Browse available vouchers."""
    # TODO: Fetch vouchers from database
    return render_template('rewards/vouchers.html')

@rewards_bp.route('/redeem/<int:voucher_id>', methods=['POST'])
def redeem_voucher(voucher_id):
    """Redeem a voucher."""
    # TODO: Deduct points and mark voucher as redeemed
    return redirect(url_for('rewards.vouchers'))
