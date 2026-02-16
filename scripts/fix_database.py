"""
Database recovery script after user deletion.
Fixes foreign key constraints and recreates Musicly community.
"""

from utils.supabase_db import get_supabase

def fix_database():
    """Fix database after all users were deleted."""
    supabase = get_supabase()
    
    print("🔧 Starting database recovery...")
    
    try:
        # Step 1: Check if Musicly exists
        print("\n1️⃣  Checking for Musicly community...")
        existing = supabase.table('communities').select('*').eq('name', 'Musicly').execute()
        
        if existing.data:
            print(f"   ✅ Musicly exists (ID: {existing.data[0]['community_id']})")
            musicly_id = existing.data[0]['community_id']
        else:
            # Step 2: Create Musicly community
            print("\n2️⃣  Creating Musicly community...")
            community = supabase.table('communities').insert({
                'name': 'Musicly',
                'description': 'A community for music lovers to share and discover songs across generations. Share your favorite music in song-recommendations!',
                'created_by': None,  # NULL since users were deleted
            }).execute()
            
            musicly_id = community.data[0]['community_id']
            print(f"   ✅ Musicly created (ID: {musicly_id})")
        
        # Step 3: Check for channels
        print("\n3️⃣  Checking channels...")
        channels = supabase.table('community_channels').select('*').eq('community_id', musicly_id).execute()
        
        existing_channels = {ch['name']: ch for ch in channels.data}
        
        # Step 4: Create song-recommendations channel if missing
        if 'song-recommendations' not in existing_channels:
            print("   📝 Creating song-recommendations channel...")
            supabase.table('community_channels').insert({
                'community_id': musicly_id,
                'name': 'song-recommendations',
                'description': 'Share your favorite songs! Format: Song Name: <title>\nArtist: <artist>\nYear Released: <year>\nWhy they like this song: <reason>',
                'is_announcement': False
            }).execute()
            print("   ✅ song-recommendations created")
        else:
            print("   ✅ song-recommendations exists")
        
        # Step 5: Create general channel if missing
        if 'general' not in existing_channels:
            print("   📝 Creating general channel...")
            supabase.table('community_channels').insert({
                'community_id': musicly_id,
                'name': 'general',
                'description': 'General discussion about music',
                'is_announcement': False
            }).execute()
            print("   ✅ general created")
        else:
            print("   ✅ general exists")
        
        print("\n✅ Database recovery complete!")
        print(f"\nMusicly Community ID: {musicly_id}")
        print("\nNext steps:")
        print("1. Create at least one user account")
        print("2. Join the Musicly community")
        print("3. Post songs to song-recommendations channel")
        print("4. Test the jukebox!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf you see foreign key errors, run this SQL in Supabase:")
        print("ALTER TABLE communities ALTER COLUMN created_by DROP NOT NULL;")
        return False

if __name__ == '__main__':
    fix_database()
