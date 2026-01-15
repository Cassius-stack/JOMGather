"""
JOMGather - Intergenerational Connection Platform
Main Flask Application Entry Point
"""

from flask import Flask, render_template
from config import config

# Import route blueprints
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.activities import activities_bp
from routes.messaging import messaging_bp
from routes.community import community_bp
from routes.support_swap import support_swap_bp
from routes.support import support_bp
from routes.rewards import rewards_bp
from routes.slice_of_life import slice_of_life_bp

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(activities_bp, url_prefix='/activities')
    app.register_blueprint(messaging_bp, url_prefix='/messaging')
    app.register_blueprint(community_bp, url_prefix='/community')
    app.register_blueprint(support_swap_bp, url_prefix='/support-swap')
    app.register_blueprint(support_bp, url_prefix='/support')
    app.register_blueprint(rewards_bp, url_prefix='/rewards')
    app.register_blueprint(slice_of_life_bp, url_prefix='/slice-of-life')
    
    # Home route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app

# Create the application instance
app = create_app('development')

if __name__ == '__main__':
    app.run(debug=True)
