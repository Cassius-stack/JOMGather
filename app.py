"""
JOMGather - Intergenerational Connection Platform
Main Flask Application Entry Point
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before anything else

from flask import Flask, render_template, render_template_string
from flask_socketio import SocketIO
from config import config



# Import route blueprints
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.activities import activities_bp
from routes.messaging import messaging_bp
from routes.social import social_bp
from routes.support_swap import support_swap_bp
from routes.rewards import rewards_bp
from routes.slice_of_life import slice_of_life_bp
from routes.community import community_bp
from routes.jukebox import jukebox_bp

# Import SocketIO instance from extensions (Singleton pattern)
from extensions import socketio

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize SocketIO with the app
    # Using async_mode='threading' to avoid conflict with Supabase's httpx
    # (eventlet monkey-patching breaks httpx)
    socketio.init_app(app, 
                      cors_allowed_origins="*", 
                      async_mode='threading',
                      ping_timeout=60,  # seconds to wait for pong (increased for ngrok)
                      ping_interval=25)  # seconds between pings
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(activities_bp, url_prefix='/activities')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    app.register_blueprint(social_bp, url_prefix='/social')
    app.register_blueprint(support_swap_bp, url_prefix='/support-swap')
    app.register_blueprint(rewards_bp, url_prefix='/rewards')
    app.register_blueprint(slice_of_life_bp, url_prefix='/slice-of-life')
    app.register_blueprint(community_bp, url_prefix='/social/community')
    app.register_blueprint(jukebox_bp, url_prefix='/jukebox')
    
    # Import and register socket events
    from routes.chat_events import register_chat_events
    register_chat_events(socketio)
    
    # Register BOOMERang video chat events
    from routes.boomerang_events import register_boomerang_events
    register_boomerang_events(socketio)
    
    # Start background scheduler (only in main process to avoid duplicates with reloader)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        from utils.scheduler import start_scheduler
        start_scheduler(socketio)
    
    # Track user activity (throttled to avoid excessive DB calls)
    @app.before_request
    def update_last_seen():
        from flask import session
        import datetime
        import time
        from utils.supabase_db import get_supabase
        
        user_id = session.get('user_id')
        if user_id:
            # Throttle: only update last_seen once every 5 minutes
            last_update = session.get('_last_seen_update', 0)
            current_time = time.time()
            
            if current_time - last_update > 300:  # 5 minutes = 300 seconds
                try:
                    now = datetime.datetime.now().isoformat()
                    get_supabase().table('users').update({'last_seen': now}).eq('user_id', user_id).execute()
                    session['_last_seen_update'] = current_time
                except Exception as e:
                    # Don't break the app if tracking fails
                    print(f"Error updating last_seen: {e}")

    # Context Processor for Notifications (CACHED for performance)
    @app.context_processor
    def inject_notifications():
        from flask import session
        import time as _time
        
        # Default ICE servers for WebRTC NAT traversal
        ice_servers = [
            {'urls': 'stun:stun.l.google.com:19302'},
            {'urls': 'stun:stun1.l.google.com:19302'},
            {'urls': 'stun:stun2.l.google.com:19302'},
            {'urls': 'stun:stun3.l.google.com:19302'},
            {'urls': 'stun:stun4.l.google.com:19302'},
        ]
        ice_servers.extend([
            {
                'urls': 'turn:global.relay.metered.ca:3478',
                'username': 'a6706b430a8936a5959d6f72',
                'credential': '2C9gDd/WzYF+j37q'
            },
            {
                'urls': 'turns:global.relay.metered.ca:443?transport=tcp',
                'username': 'a6706b430a8936a5959d6f72',
                'credential': '2C9gDd/WzYF+j37q'
            }
        ])
        
        if session.get('user_id'):
            now = _time.time()
            cache_ttl = 60  # seconds
            last_fetch = session.get('_notif_cache_time', 0)
            
            # Use cached data if fresh enough
            if (now - last_fetch) < cache_ttl and '_cached_notifs' in session:
                return dict(
                    notifications=session.get('_cached_notifs', []),
                    unread_notifications_count=session.get('_cached_unread', 0),
                    total_coins=session.get('_cached_coins', 0),
                    ice_servers=ice_servers
                )
            
            # Cache expired or first load — fetch from DB
            try:
                from utils.supabase_db import get_supabase
                supabase = get_supabase()
                response = supabase.table('notifications').select('*').eq('user_id', session.get('user_id')).order('created_at', desc=True).limit(20).execute()
                notifications = response.data
                unread_count = sum(1 for n in notifications if not n['is_read'])
                
                coin_res = supabase.table('coins').select('total_coins').eq('user_id', session.get('user_id')).execute()
                total_coins = coin_res.data[0]['total_coins'] if coin_res.data else 0
                
                # Store in session cache
                session['_cached_notifs'] = notifications
                session['_cached_unread'] = unread_count
                session['_cached_coins'] = total_coins
                session['_notif_cache_time'] = now
                
                return dict(notifications=notifications, unread_notifications_count=unread_count, total_coins=total_coins, ice_servers=ice_servers)
            except Exception as e:
                print(f"Error fetching notifications/coins: {e}")
                return dict(notifications=[], unread_notifications_count=0, total_coins=0, ice_servers=ice_servers)
        
        return dict(notifications=[], unread_notifications_count=0, total_coins=0, ice_servers=ice_servers)

    # Home route
    @app.route('/')
    def index():
        from flask import session
        online_friends = []
        recent_friends = []
        suggested_friends = []
        if session.get('user_id'):
            try:
                # Get online friends list
                from utils.supabase_db import get_supabase
                import datetime
                
                supabase = get_supabase()
                current_user_id = session.get('user_id')
                
                # Fetch accepted friendships
                friends_ids = []
                sent = supabase.table('friendships').select('user_id_2').eq('user_id_1', current_user_id).eq('status', 'accepted').execute()
                for i in sent.data: friends_ids.append(i['user_id_2'])
                    
                received = supabase.table('friendships').select('user_id_1').eq('user_id_2', current_user_id).eq('status', 'accepted').execute()
                for i in received.data: friends_ids.append(i['user_id_1'])
                
                if friends_ids:
                    # Fetch all friends with last_seen
                    response = supabase.table('users').select('user_id, username, last_seen').in_('user_id', friends_ids).execute()
                    all_friends = response.data
                    
                    five_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat()
                    
                    for friend in all_friends:
                        # Check if online (active in last 5 mins)
                        is_online = friend.get('last_seen') and friend['last_seen'] > five_mins_ago
                        friend['is_online'] = is_online
                        
                        if is_online:
                            online_friends.append(friend)
                        else:
                            recent_friends.append(friend)
                    
                    # Sort recent friends by last_seen (most recent first)
                    recent_friends.sort(key=lambda x: x.get('last_seen') or '', reverse=True)

                # --- SUGGESTED FRIENDS LOGIC ---
                from utils.supabase_db import fetch_one, fetch_all
                me = fetch_one('users', user_id=current_user_id)
                if me:
                    # Handle Hobbies (could be string from old data or list from Zongrong's system)
                    my_hobbies = me.get('hobbies') or []
                    if isinstance(my_hobbies, str):
                        my_hobbies = [h.strip() for h in my_hobbies.split(',') if h.strip()]
                    
                    # Handle Skills (Zongrong's addition)
                    my_skills = me.get('skills') or []
                    if isinstance(my_skills, str):
                        my_skills = [s.strip() for s in my_skills.split(',') if s.strip()]
                        
                    my_region = me.get('region')
                    
                    # IDs to exclude (me + friends) - friendships check
                    excluded_ids = [current_user_id]
                    try:
                        all_f = supabase.table('friendships').select('*').or_(f"user_id_1.eq.{current_user_id},user_id_2.eq.{current_user_id}").execute().data
                        for f in all_f:
                            excluded_ids.append(f['user_id_1'] if f['user_id_1'] != current_user_id else f['user_id_2'])
                    except:
                        pass
                    
                    # Fetch other users and score them
                    other_users = fetch_all('users')
                    for u in other_users:
                        if u['user_id'] in excluded_ids:
                            continue
                        
                        score = 0
                        # 1. Region Match (High Weight)
                        if my_region and u.get('region') == my_region:
                            score += 5
                        
                        # 2. Hobbies Match
                        u_hobbies = u.get('hobbies') or []
                        if isinstance(u_hobbies, str):
                            u_hobbies = [h.strip() for h in u_hobbies.split(',') if h.strip()]
                        common_hobbies = set(h.lower() for h in my_hobbies) & set(h.lower() for h in u_hobbies)
                        score += len(common_hobbies) * 2
                        
                        # 3. Skills Match (Zongrong's System)
                        u_skills = u.get('skills') or []
                        if isinstance(u_skills, str):
                            u_skills = [s.strip() for s in u_skills.split(',') if s.strip()]
                        common_skills = set(s.lower() for s in my_skills) & set(s.lower() for s in u_skills)
                        score += len(common_skills) * 3  # Higher weight for skills to encourage learning/teaching
                        
                        if score > 0:
                            u['score'] = score
                            suggested_friends.append(u)
                    
                    # Sort and limit
                    suggested_friends.sort(key=lambda x: x['score'], reverse=True)
                    suggested_friends = suggested_friends[:4]
                # -------------------------------
                    
            except Exception as e:
                print(f"Error fetching dashboard data: {e}")
                
        else:
            # Not logged in? Show landing page
            return render_template('landing.html')
                
        return render_template('index.html', 
                             online_friends=online_friends, 
                             recent_friends=recent_friends,
                             suggested_friends=suggested_friends,
                             sol_streak=me.get('sol_streak', 0) if 'me' in locals() and me else 0)

    # Global Access Control Hook
    @app.before_request
    def check_access_control():
        from flask import session, request, redirect, url_for
        
        # List of protected path prefixes
        protected_prefixes = [
            '/profile', '/activities', '/social', '/rewards', 
            '/messaging', '/support-swap', '/slice-of-life', '/jukebox'
        ]
        
        # Allow static (css/js/img), auth (login/register), and specific open routes
        if request.path.startswith('/static') or request.path.startswith('/auth') or request.path == '/' or request.path == '/skeleton' or request.path == '/health':
            return
            
        # If user is trying to access a protected area and is NOT logged in
        if not session.get('user_id'):
            # Check if current path starts with any of the guarded prefixes
            for prefix in protected_prefixes:
                if request.path.startswith(prefix):
                    # Redirect to login directly instead of index/landing to force a clean state
                    # This prevents the "not found" or double-action issue
                    return redirect(url_for('auth.login'))
    
    # Health check endpoint (for Render + monitoring)
    @app.route('/health')
    def health_check():
        """Health check endpoint — verifies DB connectivity."""
        try:
            from utils.supabase_db import get_supabase
            # Quick lightweight query to verify connection
            get_supabase().table('users').select('user_id').limit(1).execute()
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 503
    
    # Skeleton template preview (for development only)
    @app.route('/skeleton')
    def skeleton():
        return render_template('skeleton.html')
    
    # ============================================
    # GLOBAL ERROR HANDLERS
    # ============================================
    
    @app.errorhandler(500)
    def internal_error(error):
        """Friendly 500 error page with auto-retry."""
        import traceback
        traceback.print_exc()
        return render_template_string(ERROR_500_TEMPLATE), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Friendly 404 error page."""
        return render_template_string(ERROR_404_TEMPLATE), 404
    
    return app


# ============================================
# ERROR PAGE TEMPLATES (inline to avoid missing template issues)
# ============================================

ERROR_500_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Something went wrong - MySavvyGranny</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .error-card { text-align: center; background: white; border-radius: 24px; padding: 48px 40px; max-width: 480px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); }
        .error-icon { font-size: 4rem; color: #1e3a5f; margin-bottom: 16px; }
        h1 { color: #1e3a5f; font-size: 1.5rem; margin-bottom: 8px; }
        p { color: #64748b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; }
        .retry-btn { display: inline-flex; align-items: center; gap: 8px; background: linear-gradient(135deg, #1e3a5f, #2563eb); color: white; border: none; padding: 12px 32px; border-radius: 50px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; text-decoration: none; }
        .retry-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(30,58,95,0.3); color: white; }
        .home-link { display: block; margin-top: 16px; color: #64748b; text-decoration: none; font-size: 0.85rem; }
        .home-link:hover { color: #1e3a5f; }
        .countdown { font-size: 0.8rem; color: #94a3b8; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="error-card">
        <div class="error-icon"><i class="bi bi-cloud-lightning"></i></div>
        <h1>Oops! Something went wrong</h1>
        <p>Our servers hit a small bump. This usually resolves itself in a moment — please try again.</p>
        <a href="javascript:location.reload()" class="retry-btn">
            <i class="bi bi-arrow-clockwise"></i> Try Again
        </a>
        <a href="/" class="home-link"><i class="bi bi-house me-1"></i>Back to Home</a>
        <p class="countdown">Auto-retrying in <span id="timer">5</span>s...</p>
    </div>
    <script>
        let seconds = 5;
        const timer = document.getElementById('timer');
        const interval = setInterval(() => {
            seconds--;
            timer.textContent = seconds;
            if (seconds <= 0) {
                clearInterval(interval);
                location.reload();
            }
        }, 1000);
    </script>
</body>
</html>
"""

ERROR_404_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page not found - MySavvyGranny</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .error-card { text-align: center; background: white; border-radius: 24px; padding: 48px 40px; max-width: 480px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); }
        .error-icon { font-size: 4rem; color: #1e3a5f; margin-bottom: 16px; }
        h1 { color: #1e3a5f; font-size: 1.5rem; margin-bottom: 8px; }
        p { color: #64748b; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; }
        .home-btn { display: inline-flex; align-items: center; gap: 8px; background: linear-gradient(135deg, #1e3a5f, #2563eb); color: white; border: none; padding: 12px 32px; border-radius: 50px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; text-decoration: none; }
        .home-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(30,58,95,0.3); color: white; }
    </style>
</head>
<body>
    <div class="error-card">
        <div class="error-icon"><i class="bi bi-compass"></i></div>
        <h1>Page not found</h1>
        <p>The page you're looking for doesn't exist or may have been removed.</p>
        <a href="/" class="home-btn">
            <i class="bi bi-house"></i> Go Home
        </a>
    </div>
</body>
</html>
"""

# Create the application instance
app = create_app('development')

if __name__ == '__main__':
    # Use socketio.run() instead of app.run() for WebSocket support
    # host='0.0.0.0' allows connections from other devices on the same network
    # Your friend can connect using your computer's IP address (e.g., 192.168.x.x:5000)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
