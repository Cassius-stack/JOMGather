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