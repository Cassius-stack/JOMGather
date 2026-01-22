"""
Socket.IO Event Handlers for Real-Time Chat
Now using Supabase for database
"""

from flask_socketio import emit, join_room, leave_room
from utils.supabase_db import insert

# Track online users: {user_id: socket_id}
online_users = {}


def register_chat_events(socketio):
    """Register all chat-related Socket.IO events."""
    
    @socketio.on('connect')
    def handle_connect():
        """Called when a client connects to the WebSocket."""
        print(f"[Socket.IO] Client connected")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Called when a client disconnects."""
        print(f"[Socket.IO] Client disconnected")
    
    @socketio.on('register_user')
    def handle_register_user(data):
        """
        Called when a user identifies themselves after connecting.
        Join a personal room so they can receive notifications.
        """
        user_id = data.get('user_id')
        online_users[user_id] = True
        
        # Join personal room for receiving all notifications
        personal_room = f"user_{user_id}"
        join_room(personal_room)
        
        print(f"[Socket.IO] User {user_id} registered and joined {personal_room}")
        emit('user_online', {'user_id': user_id}, broadcast=True)
    
    @socketio.on('join_chat')
    def handle_join_chat(data):
        """Called when a user opens a chat with someone."""
        user_id = data.get('user_id')
        other_user_id = data.get('contact_id')
        room = get_room_name(user_id, other_user_id)
        join_room(room)
        print(f"[Socket.IO] User {user_id} joined room: {room}")
    
    @socketio.on('leave_chat')
    def handle_leave_chat(data):
        """Called when a user switches to a different chat."""
        user_id = data.get('user_id')
        other_user_id = data.get('contact_id')
        room = get_room_name(user_id, other_user_id)
        leave_room(room)
        print(f"[Socket.IO] User {user_id} left room: {room}")
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Called when a user sends a message.
        1. Save to Supabase
        2. Emit to the chat room and receiver's personal room
        """
        sender_id = data.get('sender_id')
        receiver_id = data.get('receiver_id')
        content = data.get('content')
        
        if not sender_id or not receiver_id or not content:
            return
        
        # Save to Supabase
        new_message = insert('messages', {
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'content': content
        })
        
        if not new_message:
            print(f"[Socket.IO] Failed to save message to database")
            return
        
        message_data = {
            'id': new_message['message_id'],
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'text': content
        }
        
        # Emit to the chat room (both users in the conversation)
        room = get_room_name(sender_id, receiver_id)
        emit('new_message', message_data, room=room)
        
        # Also emit to receiver's personal room (for notifications)
        receiver_room = f"user_{receiver_id}"
        emit('new_message', message_data, room=receiver_room)
        
        print(f"[Socket.IO] Message from {sender_id} to {receiver_id}")
    
    @socketio.on('typing')
    def handle_typing(data):
        """Called when a user is typing."""
        user_id = data.get('user_id')
        receiver_id = data.get('receiver_id')
        room = get_room_name(user_id, receiver_id)
        emit('user_typing', {
            'user_id': user_id,
            'is_typing': data.get('is_typing', True)
        }, room=room, include_self=False)


def get_room_name(user1_id, user2_id):
    """Create a consistent room name for two users."""
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"
