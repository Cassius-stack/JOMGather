"""
Socket.IO Event Handlers for Real-Time Chat
Now using Supabase for database
"""

from flask_socketio import emit, join_room, leave_room
from utils.supabase_db import insert, fetch_one, update, delete
from models.reward import add_coins

# Scenario correct answers (same as frontend cyberScenarios)
SCENARIO_ANSWERS = {
    1: 'scam',  # SingTel Support phishing
    2: 'scam',  # Government of Singapore urgent message
    3: 'safe',  # Bank official statement  
}

# Track online users: {user_id: socket_id}
online_users = {}


def register_chat_events(socketio):
    """Register all chat-related Socket.IO events."""
    
    # Catch-all handler to debug ALL incoming events
    @socketio.on('*')
    def catch_all(event, data):
        print(f"[Socket.IO DEBUG] Event received: {event}", flush=True)
    
    @socketio.on('connect')
    def handle_connect():
        """Called when a client connects to the WebSocket."""
        print(f"[Socket.IO] Client connected")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Called when a client disconnects."""
        from flask import request
        sid = request.sid
        print(f"[Socket.IO] Client disconnected: {sid}")
        
        # Clean up BOOMERang state if applicable
        try:
            from routes.boomerang_events import boomerang_queue, user_room_map, active_rooms
            
            # Remove from queue if waiting
            if sid in boomerang_queue:
                del boomerang_queue[sid]
            
            # End any active call
            room_id = user_room_map.get(sid)
            if room_id:
                emit('boomerang_partner_left', {}, room=room_id, include_self=False)
                if sid in user_room_map:
                    del user_room_map[sid]
                if room_id in active_rooms:
                    active_rooms[room_id].discard(sid)
                    if len(active_rooms[room_id]) == 0:
                        del active_rooms[room_id]
        except Exception as e:
            print(f"[Socket.IO] BOOMERang cleanup error: {e}")
    
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
            print(f"[Socket.IO] Skipping join_chat - missing user_id ({user_id}) or contact_id ({other_user_id})")
            return
        room = get_room_name(user_id, other_user_id)
        if room:
            join_room(room)
            print(f"[Socket.IO] User {user_id} joined room: {room}")
    
    @socketio.on('leave_chat')
    def handle_leave_chat(data):
        """Called when a user switches to a different chat."""
        user_id = data.get('user_id')
        other_user_id = data.get('contact_id')
        
        # Guard: don't try to leave if either ID is missing
        if not user_id or not other_user_id:
            print(f"[Socket.IO] Skipping leave_chat - missing user_id ({user_id}) or contact_id ({other_user_id})")
            return
            
        room = get_room_name(user_id, other_user_id)
        if room:
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
        content = data.get('content', '').strip()  # Trim whitespace
        image_url = data.get('image_url')
        is_cyber_challenge = data.get('is_cyber_challenge', False)
        scenario_id = data.get('scenario_id', 1)  # Default to scenario 1
        
        # Validation with user-friendly error messages
        if not sender_id or not receiver_id:
            emit('validation_error', {'error': 'Invalid sender or receiver'})
            return
        
        # Allow empty content if there is an image
        if not content and not image_url:
            emit('validation_error', {'error': 'Message cannot be empty'})
            return
        
        if content and len(content) > 500:
            emit('validation_error', {'error': 'Message cannot exceed 500 characters'})
            return
        
        # Save to Supabase
        message_data = {
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'content': content
        }
        
        if image_url:
            message_data['image_url'] = image_url
            
        new_message = insert('messages', message_data)
        
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
        
        response_data = {
            'id': new_message['message_id'],
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'text': content,
            'image_url': image_url,
            'is_cyber_challenge': is_cyber_challenge,
            'challenge_id': challenge_id,
            'scenario_id': scenario_id
        }
        
        # Emit to the chat room (both users in the conversation)
        room = get_room_name(sender_id, receiver_id)
        emit('new_message', response_data, room=room)
        
        # Also emit to receiver's personal room (for notifications)
        receiver_room = f"user_{receiver_id}"
        emit('new_message', response_data, room=receiver_room)
        
        print(f"[Socket.IO] Message from {sender_id} to {receiver_id} (img={bool(image_url)})")
    
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
        answer = data.get('answer', '').strip().lower()  # 'safe' or 'scam'
        
        # Validation with user-friendly error messages
        if not challenge_id:
            emit('validation_error', {'error': 'Challenge ID is required'})
            print(f"[Socket.IO] Invalid cyber answer data: missing challenge_id")
            return
        
        if not user_id:
            emit('validation_error', {'error': 'User ID is required'})
            print(f"[Socket.IO] Invalid cyber answer data: missing user_id")
            return
        
        if not answer:
            emit('validation_error', {'error': 'Please select an answer'})
            print(f"[Socket.IO] Invalid cyber answer data: missing answer")
            return
        
        # Validate answer is one of the allowed values
        if answer not in ['safe', 'scam']:
            emit('validation_error', {'error': 'Answer must be either "Safe" or "Scam"'})
            print(f"[Socket.IO] Invalid cyber answer: {answer}")
            return

        
        user_id = int(user_id)
        
        # Handle both numeric and string (msg_X) challenge IDs
        challenge = None
        if str(challenge_id).startswith('msg_'):
            # Fallback ID using message_id
            message_id = int(challenge_id.replace('msg_', ''))
            challenge = fetch_one('cyber_challenges', message_id=message_id)
        else:
            challenge_id = int(challenge_id)
            challenge = fetch_one('cyber_challenges', challenge_id=challenge_id)
        
        if not challenge:
            print(f"[Socket.IO] Challenge {challenge_id} not found")
            return
        
        # Use the actual challenge_id from database
        challenge_id = challenge['challenge_id']
        
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
            
            # Check if both users got it correct and award coins
            correct_answer = SCENARIO_ANSWERS.get(scenario_id, 'scam')
            user1_correct = user1_answer == correct_answer
            user2_correct = user2_answer == correct_answer
            
            if user1_correct and user2_correct:
                # Both correct - award 15 coins to each user
                add_coins(user1_id, 15)
                add_coins(user2_id, 15)
                print(f"[Socket.IO] Cyber challenge {challenge_id}: BOTH CORRECT! Awarded 15 coins to user {user1_id} and user {user2_id}")
            else:
                print(f"[Socket.IO] Cyber challenge {challenge_id}: user1={user1_answer}({'✓' if user1_correct else '✗'}), user2={user2_answer}({'✓' if user2_correct else '✗'}) - correct was '{correct_answer}'")
            
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


    @socketio.on('mark_read')
    def handle_mark_read(data):
        """
        Called when a user opens a chat or reads messages.
        1. Update messages in Supabase to read=True
        2. Emit 'messages_read' to the sender (so they see blue ticks)
        """
        user_id = data.get('user_id')          # The reader
        sender_id = data.get('sender_id')      # The person who sent the messages
        
        if not user_id or not sender_id:
            return

        user_id = int(user_id)
        sender_id = int(sender_id)

        # Import here to avoid circular imports
        from utils.supabase_db import get_supabase
        supabase = get_supabase()

        try:
            # Update DB: Mark all messages from sender_id to user_id as read
            supabase.table('messages').update({'read': True}).eq('sender_id', sender_id).eq('receiver_id', user_id).eq('read', False).execute()
            
            # Emit to the SENDER that their messages have been read
            # Use the sender's personal room
            print(f"[Socket.IO] User {user_id} read messages from {sender_id}")
            emit('messages_read', {'reader_id': user_id, 'contact_id': sender_id}, room=f"user_{sender_id}")
            
        except Exception as e:
            print(f"[Socket.IO] Error marking read: {e}")

    # ========== VIDEO/VOICE CALL SIGNALING ==========
    
    @socketio.on('call_user')
    def handle_call_user(data):
        """
        Called when a user initiates a call.
        Emit incoming_call to the receiver.
        """
        caller_id = data.get('caller_id')
        callee_id = data.get('callee_id')
        call_type = data.get('call_type', 'voice')  # 'voice' or 'video'
        caller_name = data.get('caller_name', 'Unknown')
        
        if not caller_id or not callee_id:
            print("[Socket.IO] call_user: missing caller_id or callee_id")
            return
        
        print(f"[Socket.IO] Call initiated: {caller_id} -> {callee_id} ({call_type})")
        
        # Emit to callee's personal room
        emit('incoming_call', {
            'caller_id': caller_id,
            'caller_name': caller_name,
            'call_type': call_type
        }, room=f"user_{callee_id}")
    
    @socketio.on('call_answer')
    def handle_call_answer(data):
        """
        Called when callee accepts the call.
        Notify caller to start WebRTC negotiation.
        """
        print(f"[Socket.IO] *** call_answer event received! Data: {data}", flush=True)
        caller_id = data.get('caller_id')
        callee_id = data.get('callee_id')
        callee_name = data.get('callee_name', 'Unknown')
        
        if not caller_id or not callee_id:
            print(f"[Socket.IO] call_answer: missing caller_id ({caller_id}) or callee_id ({callee_id})", flush=True)
            return
        
        target_room = f"user_{caller_id}"
        print(f"[Socket.IO] Call answered: {callee_id} accepted call from {caller_id}", flush=True)
        print(f"[Socket.IO] Emitting call_accepted to room: {target_room}", flush=True)
        
        # Notify caller that call was accepted
        emit('call_accepted', {
            'callee_id': callee_id,
            'callee_name': callee_name
        }, room=target_room)
    
    @socketio.on('call_decline')
    def handle_call_decline(data):
        """
        Called when callee declines the call.
        Saves a missed call message for the caller.
        """
        import json
        
        caller_id = data.get('caller_id')
        callee_id = data.get('callee_id')
        call_type = data.get('call_type', 'voice')
        
        if not caller_id or not callee_id:
            return
        
        print(f"[Socket.IO] Call declined: {callee_id} rejected {call_type} call from {caller_id}")
        
        emit('call_declined', {
            'callee_id': callee_id
        }, room=f"user_{caller_id}")
        
        # Save missed call message (from callee's perspective as a "missed" notification for caller)
        call_content = json.dumps({
            'type': 'call',
            'call_type': call_type,
            'status': 'missed',
            'duration': 0
        })
        
        # Message is from caller (who initiated) to callee (who missed/declined)
        message_data = {
            'sender_id': caller_id,
            'receiver_id': callee_id,
            'content': call_content
        }
        
        new_message = insert('messages', message_data)
        
        if new_message:
            print(f"[Socket.IO] Saved missed call message: {call_type}")
            
            # Emit to both users' personal rooms
            response_data = {
                'id': new_message['message_id'],
                'sender_id': caller_id,
                'receiver_id': callee_id,
                'text': call_content,
                'is_call_message': True
            }
            
            emit('new_message', response_data, room=f"user_{caller_id}")
            emit('new_message', response_data, room=f"user_{callee_id}")
    
    @socketio.on('call_end')
    def handle_call_end(data):
        """
        Called when either user ends the call.
        Saves a call message to the database and notifies both users.
        """
        import json
        
        user_id = data.get('user_id')
        other_user_id = data.get('other_user_id')
        call_type = data.get('call_type', 'voice')
        was_connected = data.get('was_connected', False)
        duration = data.get('duration', 0)
        is_initiator = data.get('is_initiator', True)  # Who initiated the call
        
        if not user_id or not other_user_id:
            return
        
        # Determine who initiated the call (caller) and who received (callee)
        if is_initiator:
            caller_id = user_id
            callee_id = other_user_id
        else:
            caller_id = other_user_id
            callee_id = user_id
        
        print(f"[Socket.IO] Call ended - caller: {caller_id}, callee: {callee_id}, type: {call_type}, connected: {was_connected}, duration: {duration}s")
        
        # Notify the other user that call ended
        emit('call_ended', {
            'user_id': user_id
        }, room=f"user_{other_user_id}")
        
        # Only save call message if it was connected (completed call)
        if was_connected and duration > 0:
            # Create call message content as JSON
            call_content = json.dumps({
                'type': 'call',
                'call_type': call_type,
                'status': 'completed',
                'duration': duration
            })
            
            # Sender is who INITIATED the call (caller), not who ended it
            message_data = {
                'sender_id': caller_id,
                'receiver_id': callee_id,
                'content': call_content
            }
            
            new_message = insert('messages', message_data)
            
            if new_message:
                print(f"[Socket.IO] Saved completed call message: {call_type}, {duration}s")
                
                # Emit to both users so their chats update
                response_data = {
                    'id': new_message['message_id'],
                    'sender_id': caller_id,
                    'receiver_id': callee_id,
                    'text': call_content,
                    'is_call_message': True
                }
                
                # Send to both users' personal rooms
                emit('new_message', response_data, room=f"user_{caller_id}")
                emit('new_message', response_data, room=f"user_{callee_id}")
    
    @socketio.on('webrtc_offer')
    def handle_webrtc_offer(data):
        """
        Forward WebRTC offer (SDP) to the callee.
        """
        caller_id = data.get('caller_id')
        callee_id = data.get('callee_id')
        offer = data.get('offer')
        
        if not caller_id or not callee_id or not offer:
            return
        
        print(f"[Socket.IO] WebRTC offer from {caller_id} to {callee_id}")
        
        emit('webrtc_offer', {
            'caller_id': caller_id,
            'offer': offer
        }, room=f"user_{callee_id}")
    
    @socketio.on('webrtc_answer')
    def handle_webrtc_answer(data):
        """
        Forward WebRTC answer (SDP) to the caller.
        """
        caller_id = data.get('caller_id')
        callee_id = data.get('callee_id')
        answer = data.get('answer')
        
        if not caller_id or not callee_id or not answer:
            return
        
        print(f"[Socket.IO] WebRTC answer from {callee_id} to {caller_id}")
        
        emit('webrtc_answer', {
            'callee_id': callee_id,
            'answer': answer
        }, room=f"user_{caller_id}")
    
    @socketio.on('ice_candidate')
    def handle_ice_candidate(data):
        """
        Called when a peer has a new ICE candidate.
        Forward it to the other peer.
        """
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        candidate = data.get('candidate')
        
        if not from_user_id or not to_user_id:
            return
        
        emit('ice_candidate', {
            'from_user_id': from_user_id,
            'candidate': candidate
        }, room=f"user_{to_user_id}")
    
    @socketio.on('mute_status')
    def handle_mute_status(data):
        """
        Called when a user mutes/unmutes their microphone.
        Relay the status to the other user.
        """
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        is_muted = data.get('is_muted', False)
        
        if not from_user_id or not to_user_id:
            return
        
        print(f"[Socket.IO] User {from_user_id} mute status: {is_muted}")
        
        emit('mute_status', {
            'from_user_id': from_user_id,
            'is_muted': is_muted
        }, room=f"user_{to_user_id}")
    
    @socketio.on('camera_status')
    def handle_camera_status(data):
        """
        Called when a user turns their camera on/off.
        Relay the status to the other user.
        """
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        is_camera_off = data.get('is_camera_off', False)
        
        if not from_user_id or not to_user_id:
            return
        
        print(f"[Socket.IO] User {from_user_id} camera status: {'OFF' if is_camera_off else 'ON'}")
        
        emit('camera_status', {
            'from_user_id': from_user_id,
            'is_camera_off': is_camera_off
        }, room=f"user_{to_user_id}")
    
    @socketio.on('mic_status')
    def handle_mic_status(data):
        """
        Called when a user mutes/unmutes their microphone.
        Relay the status to the other user.
        """
        from_user_id = data.get('from_user_id')
        to_user_id = data.get('to_user_id')
        is_muted = data.get('is_muted', False)
        
        if not from_user_id or not to_user_id:
            return
        
        print(f"[Socket.IO] User {from_user_id} mic status: {'MUTED' if is_muted else 'UNMUTED'}")
        
        emit('mic_status', {
            'from_user_id': from_user_id,
            'is_muted': is_muted
        }, room=f"user_{to_user_id}")


def get_room_name(user1_id, user2_id):
    """Create a consistent room name for two users."""
    ids = sorted([int(user1_id), int(user2_id)])

