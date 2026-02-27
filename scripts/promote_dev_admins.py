"""
One-time script: Promote all users with 'dev_' in their email to admin
in the Musicly community.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.supabase_db import get_supabase

def promote_dev_admins():
    supabase = get_supabase()

    # Find Musicly community
    musicly = supabase.table('communities').select('community_id').eq('name', 'Musicly').execute()
    if not musicly.data:
        print("❌ Musicly community not found.")
        return

    musicly_id = musicly.data[0]['community_id']
    print(f"✅ Found Musicly (ID: {musicly_id})")

    # Find all users whose email contains 'dev_'
    all_users = supabase.table('users').select('user_id, username, email').execute()
    dev_users = [u for u in all_users.data if u.get('email', '').startswith('dev_')]

    if not dev_users:
        print("⚠️  No dev_ email users found.")
        return

    print(f"🔍 Found {len(dev_users)} dev_ user(s): {[u['email'] for u in dev_users]}")

    promoted = 0
    for user in dev_users:
        uid = user['user_id']

        # Ensure they are a member of Musicly first
        membership = supabase.table('community_members').select('community_id').eq(
            'community_id', musicly_id
        ).eq('user_id', uid).execute()

        if not membership.data:
            supabase.table('community_members').insert({
                'community_id': musicly_id,
                'user_id': uid,
                'joined_at': 'now()'
            }).execute()
            print(f"   ➕ Added {user['email']} as member of Musicly")

        # Check if already admin
        existing_role = supabase.table('community_roles').select('role_id').eq(
            'community_id', musicly_id
        ).eq('user_id', uid).eq('role', 'admin').execute()

        if existing_role.data:
            print(f"   ✅ {user['email']} is already admin — skipped")
        else:
            supabase.table('community_roles').insert({
                'community_id': musicly_id,
                'user_id': uid,
                'role': 'admin'
            }).execute()
            print(f"   🎉 Promoted {user['email']} to admin in Musicly")
            promoted += 1

    print(f"\n✅ Done! Promoted {promoted} user(s) to admin.")

if __name__ == '__main__':
    promote_dev_admins()
