"""
Rewards routes - Redeem, Coins, My Rewards
"""

from flask import Blueprint, render_template, session, request, jsonify
from models.reward import (
    get_user_coins, 
    redeem_reward, 
    get_user_rewards, 
    mark_reward_redeemed,
    get_user_redeemed_reward_ids
)

rewards_bp = Blueprint('rewards', __name__)

# List of available rewards (can be moved to database later)
REWARDS = [
    {'id': 1, 'name': 'Welcome Gift', 'price': 200, 'image': 'giftbox.svg'},
    {'id': 2, 'name': 'NTUC: $10 Voucher', 'price': 1500, 'image': 'bulb.svg'},
    {'id': 3, 'name': 'Reusable Tote', 'price': 2000, 'image': 'giftbox.svg'},
    {'id': 4, 'name': 'Tiger Balm Plaster', 'price': 2500, 'image': 'bulb.svg'},
    {'id': 5, 'name': 'Pei Pa Koa: Nin Joim', 'price': 6767, 'image': 'giftbox.svg'},
    {'id': 6, 'name': 'Essence of Chicken (Pack of 6)', 'price': 22750, 'image': 'bulb.svg'},
]


@rewards_bp.route('/')
def redeem():
    """View redeem page."""
    user_id = session.get('user_id')
    user_coins = get_user_coins(user_id)
    
    # Get list of already redeemed reward IDs
    redeemed_ids = get_user_redeemed_reward_ids(user_id)
    
    # Add 'redeemed' flag to each reward
    rewards_with_status = []
    for reward in REWARDS:
        reward_copy = reward.copy()
        reward_copy['already_redeemed'] = reward['id'] in redeemed_ids
        rewards_with_status.append(reward_copy)
    
    return render_template('rewards/redeem.html', coins=user_coins, rewards=rewards_with_status)


@rewards_bp.route('/redeem', methods=['POST'])
def redeem_item():
    """API endpoint to redeem a reward."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    data = request.get_json()
    reward_id = data.get('reward_id')
    
    # Find the reward
    reward = next((r for r in REWARDS if r['id'] == reward_id), None)
    if not reward:
        return jsonify({'success': False, 'error': 'Reward not found'}), 404
    
    # Attempt to redeem
    success, result = redeem_reward(
        user_id=user_id,
        reward_id=reward_id,
        reward_name=reward['name'],
        reward_image=reward['image'],
        price=reward['price']
    )
    
    if success:
        new_balance = get_user_coins(user_id)
        return jsonify({
            'success': True, 
            'code': result,
            'new_balance': new_balance
        })
    else:
        return jsonify({'success': False, 'error': result}), 400


@rewards_bp.route('/my')
def my_rewards():
    """View user's redeemed rewards."""
    user_id = session.get('user_id')
    user_rewards = get_user_rewards(user_id)
    user_coins = get_user_coins(user_id)
    
    return render_template('rewards/my_rewards.html', rewards=user_rewards, coins=user_coins)


@rewards_bp.route('/mark-redeemed', methods=['POST'])
def mark_redeemed():
    """Mark a reward as redeemed (used)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    
    data = request.get_json()
    record_id = data.get('record_id')
    
    if not record_id:
        return jsonify({'success': False, 'error': 'Missing record_id'}), 400
    
    mark_reward_redeemed(record_id, user_id)
    return jsonify({'success': True})