"""
Rewards routes - Redeem, Coins, My Rewards
"""

from flask import Blueprint, render_template, session, request, jsonify
from models.reward import (
    get_user_coins, 
    redeem_reward, 
    get_user_rewards, 
    mark_reward_redeemed,
    get_user_redeemed_reward_ids,
    get_all_rewards
)

rewards_bp = Blueprint('rewards', __name__)


@rewards_bp.route('/')
def redeem():
    """View redeem page."""
    try:
        user_id = session.get('user_id')
        user_coins = get_user_coins(user_id)
        rewards = get_all_rewards()
        
        # Get list of already redeemed reward IDs
        redeemed_ids = get_user_redeemed_reward_ids(user_id)
        
        # Add 'redeemed' flag to each reward
        rewards_with_status = []
        for reward in rewards:
            reward_copy = reward.copy()
            reward_copy['already_redeemed'] = reward['id'] in redeemed_ids
            rewards_with_status.append(reward_copy)
        
        return render_template('rewards/redeem.html', coins=user_coins, rewards=rewards_with_status)
    except Exception as e:
        print(f"[Rewards] Error loading redeem page: {e}")
        # Fallback: show page with 0 coins and no redeemed flags
        return render_template('rewards/redeem.html', coins=0, rewards=[])


@rewards_bp.route('/redeem', methods=['POST'])
def redeem_item():
    """API endpoint to redeem a reward."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Please log in to redeem rewards'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    reward_id = data.get('reward_id')
    
    # Validation with user-friendly error messages
    if reward_id is None:
        return jsonify({'success': False, 'error': 'Please select a reward to redeem'}), 400
    
    if not isinstance(reward_id, int) or reward_id < 1:
        return jsonify({'success': False, 'error': 'Invalid reward selection'}), 400
    
    # Find the reward from Supabase
    rewards = get_all_rewards()
    reward = next((r for r in rewards if r['id'] == reward_id), None)
    if not reward:
        return jsonify({'success': False, 'error': 'This reward is no longer available'}), 404
    
    try:
        # Check if user has enough coins
        user_coins = get_user_coins(user_id)
        if user_coins < reward['price']:
            return jsonify({'success': False, 'error': f'Not enough coins. You need {reward["price"]} coins but only have {user_coins}'}), 400
        
        # Check if already redeemed
        redeemed_ids = get_user_redeemed_reward_ids(user_id)
        if reward_id in redeemed_ids:
            return jsonify({'success': False, 'error': 'You have already redeemed this reward'}), 400
        
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
                'new_balance': new_balance,
                'message': f'Successfully redeemed {reward["name"]}!'
            })
        else:
            return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        print(f"[Rewards] Error redeeming reward: {e}")
        return jsonify({'success': False, 'error': 'Something went wrong. Please try again.'}), 500



@rewards_bp.route('/my')
def my_rewards():
    """View user's redeemed rewards."""
    try:
        user_id = session.get('user_id')
        user_rewards = get_user_rewards(user_id)
        user_coins = get_user_coins(user_id)
        
        return render_template('rewards/my_rewards.html', rewards=user_rewards, coins=user_coins)
    except Exception as e:
        print(f"[Rewards] Error loading my rewards: {e}")
        return render_template('rewards/my_rewards.html', rewards=[], coins=0)


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
    
    try:
        mark_reward_redeemed(record_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[Rewards] Error marking reward redeemed: {e}")
        return jsonify({'success': False, 'error': 'Something went wrong. Please try again.'}), 500
