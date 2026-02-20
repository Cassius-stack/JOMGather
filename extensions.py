from flask_socketio import SocketIO

# Create a shared SocketIO instance to be used across the app
# Initialized in app.py within create_app()
socketio = SocketIO()
