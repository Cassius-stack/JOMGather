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
        if not user_id or not other_user_id:
            return  # Skip if either ID is missing
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
    
    @socketio.on('edit_message')
    def handle_edit_message(data):
        """
        Called when a user edits their message.
        1. Verify ownership
        2. Update in Supabase
        3. Emit to the chat room AND personal rooms
        """
        message_id = data.get('message_id')
        user_id = data.get('user_id')
        new_content = data.get('new_content')
        
        if not message_id or not user_id or not new_content:
            return
        
        # Convert to int (JavaScript sends as string)
        try:
            message_id = int(message_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"[Socket.IO] Invalid message_id or user_id")
            return
        
        # Import here to avoid circular imports
        from utils.supabase_db import fetch_one, update
        
        # Verify the user owns this message
        message = fetch_one('messages', message_id=message_id)
        if not message or message.get('sender_id') != user_id:
            print(f"[Socket.IO] Edit denied: user {user_id} doesn't own message {message_id}")
            return
        
        # Update in database (only update content, not 'edited' flag to avoid column errors)
        try:
            update('messages', {'content': new_content}, message_id=message_id)
        except Exception as e:
            print(f"[Socket.IO] Error updating message: {e}")
            return
        
        # Get receiver_id for room name
        receiver_id = message.get('receiver_id')
        room = get_room_name(user_id, receiver_id)
        
        edit_data = {
            'message_id': message_id,
            'new_content': new_content,
            'sender_id': user_id,
            'receiver_id': receiver_id
        }
        
        # Emit to chat room (for users currently viewing this chat)
        emit('message_edited', edit_data, room=room)
        
        # Also emit to both users' personal rooms (for inbox preview updates)
        emit('message_edited', edit_data, room=f"user_{user_id}")
        emit('message_edited', edit_data, room=f"user_{receiver_id}")
        
        print(f"[Socket.IO] Message {message_id} edited by user {user_id}")
    
    @socketio.on('delete_message')
    def handle_delete_message(data):
        """
        Called when a user deletes their message.
        1. Verify ownership
        2. Delete from Supabase
        3. Emit to the chat room AND personal rooms
        """
        message_id = data.get('message_id')
        user_id = data.get('user_id')
        
        if not message_id or not user_id:
            return
        
        # Convert to int (JavaScript sends as string)
        try:
            message_id = int(message_id)
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"[Socket.IO] Invalid message_id or user_id")
            return
        
        # Import here to avoid circular imports
        from utils.supabase_db import fetch_one, delete
        
        # Verify the user owns this message
        message = fetch_one('messages', message_id=message_id)
        if not message or message.get('sender_id') != user_id:
            print(f"[Socket.IO] Delete denied: user {user_id} doesn't own message {message_id}")
            return
        
        # Get receiver_id before deleting
        receiver_id = message.get('receiver_id')
        room = get_room_name(user_id, receiver_id)
        
        # Delete from database
        try:
            delete('messages', message_id=message_id)
        except Exception as e:
            print(f"[Socket.IO] Error deleting message: {e}")
            return
        
        delete_data = {
            'message_id': message_id,
            'sender_id': user_id,
            'receiver_id': receiver_id
        }
        
        print(f"[Socket.IO] DELETE - Emitting to room: {room}")
        print(f"[Socket.IO] DELETE - Emitting to user_{user_id} and user_{receiver_id}")
        print(f"[Socket.IO] DELETE - Data: {delete_data}")
        
        # Emit to chat room
        emit('message_deleted', delete_data, room=room)
        
        # Also emit to both users' personal rooms
        emit('message_deleted', delete_data, room=f"user_{user_id}")
        emit('message_deleted', delete_data, room=f"user_{receiver_id}")
        
        print(f"[Socket.IO] Message {message_id} deleted by user {user_id} - EMITS COMPLETE")


def get_room_name(user1_id, user2_id):
    """Create a consistent room name for two users."""
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"

