# JOMGather Database & Musicly Setup Instructions

## 🎯 Overview
This guide will help you recreate your database and set up the default "Musicly" community that all users automatically join.

## 📋 Step-by-Step Instructions

### Step 1: Run the Database Schema

1. Open your **Supabase Dashboard**
2. Go to the **SQL Editor** tab
3. Open the file: `database/complete_schema.sql`
4. Copy all the SQL code from that file
5. Paste it into the Supabase SQL Editor
6. Click **Run** to execute the script
7. ✅ All tables will be created in your database

### Step 2: Create the Musicly Community

After creating the tables, you need to seed the Musicly community:

```powershell
# Run from your project root directory
python database/seed_musicly.py
```

This script will:
- ✅ Create the "Musicly" community
- ✅ Add ALL existing users to Musicly automatically
- ✅ Create default channels (announcements, general, song-recommendations, jukebox)
- ✅ Add welcome messages to channels

### Step 3: Auto-Add New Users to Musicly (Future Users)

To automatically add new users to Musicly when they register, you need to update your registration route.

**Find your registration file** (likely `routes/auth.py` or similar) and add this code after a user is created:

```python
# After user is created and inserted into database
try:
    # Get the Musicly community
    musicly = fetch_one('communities', name='Musicly', is_default=True)
    if musicly:
        # Add new user to Musicly
        insert('community_members', {
            'community_id': musicly['community_id'],
            'user_id': new_user['user_id']
        })
        print(f"✅ Added new user to Musicly community")
except Exception as e:
    print(f"⚠️ Could not add user to Musicly: {e}")
```

## 🎵 Jukebox Button

The Jukebox button has been added to the community page! It will:
- ✅ Appear in the **top right corner** of the chat header
- ✅ Only show when you're viewing the **Musicly community**
- ✅ Navigate to `/jukebox` when clicked
- ✅ Include a music note icon 🎵

## 🧪 Testing Checklist

After setup, verify everything works:

### Database Verification
- [ ] Open Supabase and check that all tables exist
- [ ] Verify `communities` table has a "Musicly" entry
- [ ] Check `community_members` table shows all users are in Musicly
- [ ] Verify `community_channels` table has the 4 default channels

### Application Testing  
- [ ] Log in to JOMGather
- [ ] Navigate to Communities page
- [ ] Verify you see "Musicly" in your community list
- [ ] Click on Musicly and verify you can see channels
- [ ] Check that the **Jukebox** button appears in the top right
- [ ] Click the Jukebox button and verify it navigates to `/jukebox`

## 📁 Files Reference

- **Database Schema**: `database/complete_schema.sql`
- **Musicly Seed Script**: `database/seed_musicly.py`
- **Community Page**: `templates/social/community.html` (modified with Jukebox button)

## ❓ Troubleshooting

### "No users found" error when running seed script
- Make sure you have created at least one user account first
- The script needs at least 1 user to act as the Musicly creator

### Jukebox button not showing
- Make sure you're viewing the Musicly community (not another community)
- Check browser console for JavaScript errors
- Verify the community name is exactly "Musicly" (case-sensitive)

### Users not auto-joining Musicly
- Run the seed script again: `python database/seed_musicly.py`
- The script will check for existing members and only add missing ones
- Make sure Step 3 (auto-add code) is added to your registration route

## 🎉 Success!

Once everything is set up:
- All existing users are in Musicly ✅
- New users will auto-join Musicly on registration ✅  
- Jukebox button is available in Musicly ✅
- Users can share music and interact ✅
