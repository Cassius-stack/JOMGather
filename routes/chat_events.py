"""
Socket.IO Event Handlers for Real-Time Chat
Now using Supabase for database
"""

from flask_socketio import emit, join_room, leave_room
from utils.supabase_db import insert, fetch_one, update, delete

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
        is_cyber_challenge = data.get('is_cyber_challenge', False)
        scenario_id = data.get('scenario_id', 1)  # Default to scenario 1
        
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
        
        challenge_id = None
        
        # If this is a cyber challenge, create a challenge record
        if is_cyber_challenge:
            challenge = insert('cyber_challenges', {
                'message_id': new_message['message_id'],
                'scenario_id': scenario_id,
                'user1_id': sender_id,
                'user2_id': receiver_id,
                'status': 'pending'
            })
            if challenge:
                challenge_id = challenge['challenge_id']
                print(f"[Socket.IO] Created cyber challenge {challenge_id} for message {new_message['message_id']}")
        
        message_data = {
            'id': new_message['message_id'],
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'text': content,
            'is_cyber_challenge': is_cyber_challenge,
            'challenge_id': challenge_id,
            'scenario_id': scenario_id
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
    
    @socketio.on('submit_cyber_answer')
    def handle_submit_cyber_answer(data):
        """
        Called when a user submits their answer to a cyber challenge.
        1. Save their answer to the correct column (user1 or user2)
        2. Check if both users have answered
        3. If both answered, emit challenge_complete with results
        4. Otherwise, emit answer_submitted to notify the other user
        """
        challenge_id = data.get('challenge_id')
        user_id = data.get('user_id')
        answer = data.get('answer')  # 'safe' or 'scam'
        
        if not challenge_id or not user_id or not answer:
            print(f"[Socket.IO] Invalid cyber answer data: {data}")
            return
        
        challenge_id = int(challenge_id)
        user_id = int(user_id)
        
        # Get the challenge record
        challenge = fetch_one('cyber_challenges', challenge_id=challenge_id)
        if not challenge:
            print(f"[Socket.IO] Challenge {challenge_id} not found")
            return
        
        user1_id = challenge['user1_id']
        user2_id = challenge['user2_id']
        
        # Determine which user is answering
        if user_id == user1_id:
            update('cyber_challenges', {'user1_answer': answer}, challenge_id=challenge_id)
            my_answer = answer
            other_answer = challenge.get('user2_answer')
            other_user_id = user2_id
        elif user_id == user2_id:
            update('cyber_challenges', {'user2_answer': answer}, challenge_id=challenge_id)
            my_answer = answer
            other_answer = challenge.get('user1_answer')
            other_user_id = user1_id
        else:
            print(f"[Socket.IO] User {user_id} is not part of challenge {challenge_id}")
            return
        
        room = get_room_name(user1_id, user2_id)
        scenario_id = challenge['scenario_id']
        
        # Check if both have answered
        if other_answer:
            # Both users have answered - mark complete and send results
            update('cyber_challenges', {'status': 'completed'}, challenge_id=challenge_id)
            
            # Re-fetch to get updated answers
            updated_challenge = fetch_one('cyber_challenges', challenge_id=challenge_id)
            user1_answer = updated_challenge['user1_answer']
            user2_answer = updated_challenge['user2_answer']
            
            result_data = {
                'challenge_id': challenge_id,
                'scenario_id': scenario_id,
                'user1_id': user1_id,
                'user2_id': user2_id,
                'user1_answer': user1_answer,
                'user2_answer': user2_answer,
                'status': 'completed'
            }
            
            # Emit to both users
            emit('cyber_challenge_complete', result_data, room=room)
            emit('cyber_challenge_complete', result_data, room=f"user_{user1_id}")
            emit('cyber_challenge_complete', result_data, room=f"user_{user2_id}")
            
            print(f"[Socket.IO] Cyber challenge {challenge_id} completed: user1={user1_answer}, user2={user2_answer}")
        else:
            # Only one user has answered - notify the submitter
            answer_data = {
                'challenge_id': challenge_id,
                'scenario_id': scenario_id,
                'user_id': user_id,
                'other_user_id': other_user_id,
                'status': 'waiting'
            }
            
            # Emit to the room so both users know
            emit('cyber_answer_submitted', answer_data, room=room)
            emit('cyber_answer_submitted', answer_data, room=f"user_{user1_id}")
            emit('cyber_answer_submitted', answer_data, room=f"user_{user2_id}")
            
            print(f"[Socket.IO] User {user_id} answered challenge {challenge_id}, waiting for user {other_user_id}")


def get_room_name(user1_id, user2_id):
    """Create a consistent room name for two users."""
    ids = sorted([int(user1_id), int(user2_id)])
    return f"chat_{ids[0]}_{ids[1]}"

