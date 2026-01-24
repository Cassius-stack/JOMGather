"""
Reward model - Coins, Items
Uses Supabase for data storage
"""
from utils.supabase_db import get_supabase, fetch_one


def get_user_coins(user_id):
    """Get user's current coin balance from Supabase."""
    if not user_id:
        return 0
    result = fetch_one('coins', user_id=user_id)
    return result['total_coins'] if result else 0


def add_coins(user_id, amount):
    """Add coins to user's balance."""
    if not user_id or amount <= 0:
        return False
    
    supabase = get_supabase()
    # Check if user has coins record
    existing = fetch_one('coins', user_id=user_id)
    
    if existing:
        # Update existing record
        new_total = existing['total_coins'] + amount
        supabase.table('coins').update({'total_coins': new_total}).eq('user_id', user_id).execute()
    else:
        # Create new record
        supabase.table('coins').insert({'user_id': user_id, 'total_coins': amount}).execute()
    
    return True


def remove_coins(user_id, amount):
    """Remove coins from user's balance. Returns True if successful."""
    if not user_id or amount <= 0:
        return False
    
    existing = fetch_one('coins', user_id=user_id)
    
    if existing and existing['total_coins'] >= amount:
        supabase = get_supabase()
        new_total = existing['total_coins'] - amount
        supabase.table('coins').update({'total_coins': new_total}).eq('user_id', user_id).execute()
        return True
    
    return False


def generate_redemption_code():
    """Generate a unique redemption code."""
    import random
    import string
    return 'JOM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def redeem_reward(user_id, reward_id, reward_name, reward_image, price):
    """
    Redeem a reward for a user.
    Deducts coins and creates a redeemed record.
    Returns (success, code_or_error_message)
    """
    if not user_id:
        return False, "User not logged in"
    
    # Check if user has enough coins
    current_coins = get_user_coins(user_id)
    if current_coins < price:
        return False, "Not enough coins"
    
    # Deduct coins
    if not remove_coins(user_id, price):
        return False, "Failed to deduct coins"
    
    # Generate redemption code
    code = generate_redemption_code()
    
    # Create redeemed record
    supabase = get_supabase()
    supabase.table('user_redeemed_rewards').insert({
        'user_id': user_id,
        'reward_id': reward_id,
        'reward_name': reward_name,
        'reward_image': reward_image,
        'reward_code': code,
        'status': 'available'
    }).execute()
    
    return True, code


def get_user_rewards(user_id):
    """Get all rewards redeemed by a user, sorted: available first, then redeemed."""
    if not user_id:
        return []
    
    supabase = get_supabase()
    result = supabase.table('user_redeemed_rewards').select('*').eq('user_id', user_id).order('status', desc=False).order('redeemed_at', desc=True).execute()
    
    return result.data if result.data else []


def mark_reward_redeemed(reward_record_id, user_id):
    """Mark a redeemed reward as used."""
    supabase = get_supabase()
    supabase.table('user_redeemed_rewards').update({'status': 'redeemed'}).eq('id', reward_record_id).eq('user_id', user_id).execute()
    return True


def get_user_redeemed_reward_ids(user_id):
    """Get list of reward IDs that user has already redeemed (for showing 'Redeemed' button)."""
    if not user_id:
        return []
    
    supabase = get_supabase()
    result = supabase.table('user_redeemed_rewards').select('reward_id').eq('user_id', user_id).execute()
    
    return [r['reward_id'] for r in result.data] if result.data else []