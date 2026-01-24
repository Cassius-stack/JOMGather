"""
JOMGather - Intergenerational Connection Platform
Main Flask Application Entry Point
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before anything else

from flask import Flask, render_template
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

# Create SocketIO instance (initialized later with app)
socketio = SocketIO()

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize SocketIO with the app
    # Using async_mode='threading' to avoid conflict with Supabase's httpx
    # (eventlet monkey-patching breaks httpx)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(activities_bp, url_prefix='/activities')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    app.register_blueprint(social_bp, url_prefix='/social')
    app.register_blueprint(support_swap_bp, url_prefix='/support-swap')
    app.register_blueprint(rewards_bp, url_prefix='/rewards')
    app.register_blueprint(slice_of_life_bp, url_prefix='/slice-of-life')
    
    # Import and register socket events
    from routes.chat_events import register_chat_events
    register_chat_events(socketio)
    
    # Home route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Skeleton template preview (for development only)
    @app.route('/skeleton')
    def skeleton():
        return render_template('skeleton.html')
    
    return app

# Create the application instance
app = create_app('development')

if __name__ == '__main__':
    # Use socketio.run() instead of app.run() for WebSocket support
    # host='0.0.0.0' allows connections from other devices on the same network
    # Your friend can connect using your computer's IP address (e.g., 192.168.x.x:5000)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
