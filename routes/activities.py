"""
Activities routes - Activity Suite (Brandon's feature)
TikTok Challenges, Puzzle Challenges, Virtual Games, Photo Streak
"""

from flask import Blueprint, render_template, request, redirect, url_for, session
from utils.supabase_db import get_supabase, fetch_one, fetch_all

activities_bp = Blueprint('activities', __name__)

@activities_bp.route('/')
def activity_list():
    """List all available activities."""
    return render_template('activities/activity_list.html')

@activities_bp.route('/tiktok-challenge')
def tiktok_challenge():
    """TikTok video challenges."""
    return render_template('activities/tiktok_challenge.html')

@activities_bp.route('/tiktok-challenge/create', methods=['GET', 'POST'])
def create_tiktok_challenge():
    """Create a new TikTok challenge."""
    if request.method == 'POST':
        # TODO: Save challenge to database
        pass
    return render_template('activities/tiktok_challenge.html')

@activities_bp.route('/puzzle-challenge')
def puzzle_challenge():
    """Cooperative puzzle/brain games."""
    return render_template('activities/puzzle_challenge.html')

@activities_bp.route('/photo-streak')
def photo_streak():
    """Daily photo exchange streak."""
    return render_template('activities/photo_streak.html')

@activities_bp.route('/photo-streak/upload', methods=['POST'])
def upload_photo():
    """Upload a photo for the streak."""
    # TODO: Handle photo upload
    return redirect(url_for('activities.photo_streak'))


@activities_bp.route('/boomerang')
def boomerang():
    """BOOMERang - Entry Transition."""
    return render_template('activities/Boomerang/Transition.html')


@activities_bp.route('/boomerang/home')
def boomerang_home():
    """BOOMERang - Description/Setup page."""
    user_id = session.get('user_id')
    recent_chats = []
    friends = []
    
    if user_id:
        supabase = get_supabase()
        
        # 0. Fetch All Meetup Partner IDs (for filtering friends later)
        meetup_partner_ids = set()
        try:
             # Fetch ALL history for this user to know who they met
            all_history = supabase.table('meetup_history').select('*').or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").execute()
            for h in all_history.data:
                pid = h['user2_id'] if h['user1_id'] == user_id else h['user1_id']
                meetup_partner_ids.add(pid)
        except Exception as e:
            print(f"Error fetching meetup history for filtering: {e}")

        # 1. Fetch Recent Chats
        try:
            # Fetch last 3 meetups
            response = supabase.table('meetup_history').select('*').or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").order('met_at', desc=True).limit(3).execute()
            history_items = response.data
            
            for item in history_items:
                # Determine partner
                is_user1 = item['user1_id'] == user_id
                partner_id = item['user2_id'] if is_user1 else item['user1_id']
                
                # Fetch partner name
                partner_name = "Unknown"
                try:
                    partner = fetch_one('users', user_id=partner_id)
                    if partner:
                        partner_name = partner['username']
                except:
                    pass

                # Calculate duration string
                duration_sec = item.get('duration_seconds', 0)
                mins = duration_sec // 60
                duration_str = f"{mins} min chat"
                
                # Check if already friends
                is_friend = False
                try:
                    friend_res = supabase.table('friendships').select('status').or_(
                        f"and(user_id_1.eq.{user_id},user_id_2.eq.{partner_id}),and(user_id_1.eq.{partner_id},user_id_2.eq.{user_id})"
                    ).eq('status', 'accepted').execute()
                    if friend_res.data:
                        is_friend = True
                except:
                    pass

                recent_chats.append({
                    'partner_id': partner_id,
                    'partner_name': partner_name,
                    'duration': duration_str,
                    'is_friend': is_friend
                })
        except Exception as e:
            print(f"Error fetching recent chats: {e}")

        # 2. Fetch Friends
        try:
            # Get accepted friendships
            friendships = fetch_all('friendships', status='accepted')
            friend_ids = []
            for f in friendships:
                if f['user_id_1'] == user_id:
                    friend_ids.append(f['user_id_2'])
                elif f['user_id_2'] == user_id:
                    friend_ids.append(f['user_id_1'])
            
            # Fetch user details
            for fid in friend_ids:
                f_user = fetch_one('users', user_id=fid)
                if f_user:
                    # Check online
                    is_online = False
                    last_seen = f_user.get('last_seen')
                    if last_seen:
                        try: # Check valid ISO format
                           from datetime import datetime, timedelta
                           dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                           # Simple 5 min threshold - careful with timezones, assume server time consistency
                           # reusing logic from social.py might be safer but this is quick check
                           is_online = True # Placeholder, real logic needs consistent TZ
                        except: pass

                    friends.append({
                            'user_id': fid,
                            'username': f_user['username'],
                            'profile_picture': f_user.get('profile_picture'),
                            'is_online': is_online, # Simplified for now
                            'wb_avatar': f_user['username'][0].upper() if f_user.get('username') else '?'
                        })
        except Exception as e:
            print(f"Error fetching friends for boomerang: {e}")

    return render_template('activities/Boomerang/Description.html', recent_chats=recent_chats, friends=friends)


@activities_bp.route('/boomerang/meetup')
def boomerang_meetup():
    """BOOMERang - Video call meetup page."""
    return render_template('activities/Boomerang/Meetup.html')


@activities_bp.route('/boomerang/loading')
def boomerang_loading():
    """BOOMERang - Loading/matching page."""
    return render_template('activities/Boomerang/LoadingPage.html')


@activities_bp.route('/boomerang/history')
def boomerang_history():
    """BOOMERang - History of meetups."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    supabase = get_supabase()
    
    # Fetch history
    try:
        response = supabase.table('meetup_history').select('*').or_(f"user1_id.eq.{user_id},user2_id.eq.{user_id}").order('met_at', desc=True).execute()
        history_items = response.data
        
        # Format for display
        formatted_history = []
        import datetime
        for item in history_items:
            # Determine partner
            is_user1 = item['user1_id'] == user_id
            partner_id = item['user2_id'] if is_user1 else item['user1_id']
            
            # Fetch partner details
            partner_name = "Unknown"
            try:
                partner = fetch_one('users', user_id=partner_id)
                if partner:
                    partner_name = partner['username']
            except:
                pass
                
            # Check if friends
            is_friend = False
            try:
                friend_res = supabase.table('friendships').select('status').or_(
                    f"and(user_id_1.eq.{user_id},user_id_2.eq.{partner_id}),and(user_id_1.eq.{partner_id},user_id_2.eq.{user_id})"
                ).eq('status', 'accepted').execute()
                if friend_res.data:
                    is_friend = True
            except:
                pass

            # Calculate duration string
            duration_sec = item.get('duration_seconds', 0)
            mins = duration_sec // 60
            secs = duration_sec % 60
            duration_str = f"{mins}m {secs}s"
            
            # Format date
            date_str = item['met_at']
            date_display = "Unknown"
            if date_str:
                try:
                    dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_display = dt.strftime("%d %b %Y, %I:%M %p")
                except:
                    date_display = date_str[:16].replace('T', ' ')

            formatted_history.append({
                'partner_id': partner_id,
                'partner_name': partner_name,
                'date': date_display,
                'duration': duration_str,
                'is_friend': is_friend
            })
            
    except Exception as e:
        print(f"Error fetching history: {e}")
        formatted_history = []

    return render_template('activities/Boomerang/History.html', history=formatted_history)


# === Helper Functions ===
def search_activities_logic(query):
    """Search for activities matching the query."""
    activities = [
        {'name': 'Slice of Life', 'description': 'Share daily photo stories', 'url': url_for('slice_of_life.prompt'), 'icon': 'bi-camera', 'color': 'primary'},
        {'name': 'Support Swap', 'description': 'Exchange skills and help', 'url': url_for('support_swap.ss_dashboard'), 'icon': 'bi-lightbulb', 'color': 'warning'},
        {'name': 'Jukebox', 'description': 'Share songs and playlists', 'url': url_for('social.social_hub'), 'icon': 'bi-music-note-beamed', 'color': 'info'},
        {'name': 'Cyber Challenge', 'description': 'Digital literacy quiz', 'url': url_for('activities.puzzle_challenge'), 'icon': 'bi-shield-check', 'color': 'danger'},
        {'name': 'BOOMERang', 'description': 'Quick video chat', 'url': url_for('activities.boomerang'), 'icon': 'bi-camera-video', 'color': 'secondary'},
        {'name': 'Puzzle Challenge', 'description': 'Cooperative brain games', 'url': url_for('activities.puzzle_challenge'), 'icon': 'bi-puzzle', 'color': 'success'},
        {'name': 'TikTok Challenge', 'description': 'Viral video challenges', 'url': url_for('activities.tiktok_challenge'), 'icon': 'bi-tiktok', 'color': 'dark'}
    ]
    
    if not query:
        return []
        
    query = query.lower()
    return [a for a in activities if query in a['name'].lower() or query in a['description'].lower()]

