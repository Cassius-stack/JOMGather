"""
BOOMERang Socket.IO Events
Real-time video chat matching and signaling
"""

from flask_socketio import emit, join_room, leave_room
from flask import request
import uuid
import datetime
from utils.supabase_db import insert

# Queue of users waiting to be matched: {socket_id: user_info}
boomerang_queue = {}

# Active rooms: {room_id: {user1_sid, user2_sid}}
active_rooms = {}

# Metadata for rooms: {room_id: {'start_time': datetime, 'users': {sid: user_id}}}
room_metadata = {}

# Map socket_id to room_id
user_room_map = {}


def register_boomerang_events(socketio):
    """Register all BOOMERang-related Socket.IO events."""
    
    @socketio.on('boomerang_join_queue')
    def handle_join_queue(data):
        """User joins the matching queue."""
        sid = request.sid
        user_name = data.get('name', 'Anonymous')
        user_id = data.get('user_id')

        # Check for active ban
        if user_id:
            try:
                from utils.supabase_db import fetch_one
                user_record = fetch_one('users', 'boomerang_banned_until', user_id=user_id)
                if user_record and user_record.get('boomerang_banned_until'):
                    banned_until_str = user_record['boomerang_banned_until']
                    try:
                        banned_until = datetime.datetime.fromisoformat(banned_until_str.replace('Z', '+00:00'))
                        if datetime.datetime.now(datetime.timezone.utc) < banned_until:
                            # User is currently banned
                            print(f"[BOOMERang] Blocked banned user {user_name} ({sid}) from joining queue.")
                            emit('boomerang_queue_status', {
                                'status': 'banned',
                                'reason': f"You are banned from BOOMERang until {banned_until.strftime('%b %d, %Y')} due to multiple reports."
                            })
                            return
                    except Exception as e:
                        print(f"[BOOMERang] Error parsing ban date: {e}")
            except Exception as e:
                print(f"[BOOMERang] Error checking ban status: {e}")

        print(f"[BOOMERang] {user_name} ({sid}) joining queue")
        
        # Fetch user's hobbies and skills for matchmaking
        user_interests = set()
        if user_id:
            try:
                from utils.supabase_db import fetch_one
                profile_record = fetch_one('users', 'hobbies,skills', user_id=user_id)
                if profile_record:
                    hobbies = profile_record.get('hobbies') or []
                    skills = profile_record.get('skills') or []
                    # Combine into lowercased set for easy intersection
                    user_interests = set(str(item).lower() for item in hobbies + skills)
            except Exception as e:
                print(f"[BOOMERang] Error fetching interests for {user_id}: {e}")
        
        # Check if there's someone waiting to be matched
        if boomerang_queue:
            best_match_sid = None
            best_match_info = None
            best_shared_interests = []
            max_intersection_size = -1
            
            # Find the best match
            for q_sid, q_info in boomerang_queue.items():
                q_interests = q_info.get('interests', set())
                # Calculate shared interests (intersection)
                shared = user_interests.intersection(q_interests)
                
                if len(shared) > max_intersection_size:
                    max_intersection_size = len(shared)
                    best_match_sid = q_sid
                    best_match_info = q_info
                    best_shared_interests = list(shared)
            
            # Use the best match found (or the first one evaluated if none had overlap, as max_intersection_size will be >= 0)
            partner_sid = best_match_sid
            partner_info = best_match_info
            
            # Format shared interests nicely (capitalize words)
            formatted_shared_interests = [s.title() for s in best_shared_interests]
            
            del boomerang_queue[partner_sid]
            
            # Create a room for them
            room_id = f"boomerang_{uuid.uuid4().hex[:8]}"
            
            # Track the room
            active_rooms[room_id] = {sid, partner_sid}
            room_metadata[room_id] = {
                'start_time': datetime.datetime.now(),
                'users': {
                    sid: user_id,
                    partner_sid: partner_info.get('user_id')
                }
            }
            user_room_map[sid] = room_id
            user_room_map[partner_sid] = room_id
            
            # Both users join the Socket.IO room
            join_room(room_id, sid=sid)
            join_room(room_id, sid=partner_sid)
            
            print(f"[BOOMERang] Matched! {user_name} with {partner_info['name']} in room {room_id}. Shared: {formatted_shared_interests}")
            
            # Notify both users they're matched
            # User 1 (the one already waiting) is the initiator
            emit('boomerang_matched', {
                'room_id': room_id,
                'partner_name': user_name,
                'partner_id': user_id,
                'is_initiator': True,
                'shared_interests': formatted_shared_interests
            }, room=partner_sid)
            
            # User 2 (the one who just joined) waits for offer
            emit('boomerang_matched', {
                'room_id': room_id,
                'partner_name': partner_info['name'],
                'partner_id': partner_info.get('user_id'),
                'is_initiator': False,
                'shared_interests': formatted_shared_interests
            }, room=sid)
        else:
            # Add to queue
            boomerang_queue[sid] = {
                'name': user_name,
                'user_id': user_id,
                'sid': sid,
                'interests': user_interests
            }
            print(f"[BOOMERang] {user_name} added to queue. Queue size: {len(boomerang_queue)}")
            emit('boomerang_queue_status', {'status': 'waiting', 'position': len(boomerang_queue)})
    
    @socketio.on('boomerang_leave_queue')
    def handle_leave_queue():
        """User cancels their search."""
        sid = request.sid
        if sid in boomerang_queue:
            del boomerang_queue[sid]
            print(f"[BOOMERang] User {sid} left queue")
    
    @socketio.on('boomerang_join_room')
    def handle_join_room(data):
        """User joins an existing room (for Meetup page)."""
        sid = request.sid
        room_id = data.get('room_id')
        user_name = data.get('name', 'Anonymous')
        
        if not room_id:
            print(f"[BOOMERang] Join room failed: no room_id")
            return
        
        # Create room if it doesn't exist (first user to join meetup)
        if room_id not in active_rooms:
            active_rooms[room_id] = set()
        
        # Add user to room
        active_rooms[room_id].add(sid)
        user_room_map[sid] = room_id
        join_room(room_id)
        
        print(f"[BOOMERang] {user_name} ({sid}) joined room {room_id}. Users in room: {len(active_rooms[room_id])}")
        
        # Notify others in room that someone joined
        emit('boomerang_user_joined', {
            'name': user_name,
            'sid': sid,
            'room_size': len(active_rooms[room_id])
        }, room=room_id, include_self=False)
    
    @socketio.on('boomerang_offer')
    def handle_offer(data):
        """Relay WebRTC offer to partner."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            # Send to everyone in room except sender
            emit('boomerang_offer', {
                'offer': data.get('offer'),
                'from': sid
            }, room=room_id, include_self=False)
            print(f"[BOOMERang] Offer relayed in room {room_id}")
    
    @socketio.on('boomerang_answer')
    def handle_answer(data):
        """Relay WebRTC answer to partner."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            emit('boomerang_answer', {
                'answer': data.get('answer'),
                'from': sid
            }, room=room_id, include_self=False)
            print(f"[BOOMERang] Answer relayed in room {room_id}")
    
    @socketio.on('boomerang_ice_candidate')
    def handle_ice_candidate(data):
        """Relay ICE candidate to partner."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            emit('boomerang_ice_candidate', {
                'candidate': data.get('candidate'),
                'from': sid
            }, room=room_id, include_self=False)
    
    @socketio.on('boomerang_chat')
    def handle_chat(data):
        """Relay chat message to partner."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            emit('boomerang_chat', {
                'message': data.get('message'),
                'from': sid,
                'name': data.get('name', 'Anonymous')
            }, room=room_id, include_self=False)
    
    @socketio.on('boomerang_friend_request')
    def handle_friend_request(data):
        """Relay friend request to partner in the room."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            emit('boomerang_friend_request', {
                'from_name': data.get('from_name', 'Someone'),
                'from_id': data.get('from_id')
            }, room=room_id, include_self=False)
    
    @socketio.on('boomerang_friend_response')
    def handle_friend_response(data):
        """Relay friend request response to partner in the room."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            emit('boomerang_friend_response', {
                'accepted': data.get('accepted', False),
                'from_name': data.get('from_name', 'Partner')
            }, room=room_id, include_self=False)

    @socketio.on('boomerang_report_user')
    def handle_report_user(data):
        """Handle user reporting their partner."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in room_metadata:
            meta = room_metadata[room_id]
            users_dict = meta.get('users', {})
            
            # Find the partner's sid and user_id by looking for the other SID in the room
            partner_sid = next((s for s in users_dict if s != sid), None)
            
            if partner_sid:
                partner_id = users_dict[partner_sid]
                
                try:
                    # Fetch partner's current reports count
                    from utils.supabase_db import fetch_one, update
                    partner_record = fetch_one('users', 'reports', user_id=partner_id)
                    current_reports = partner_record.get('reports', 0) if partner_record else 0
                    
                    new_reports = current_reports + 1
                    
                    if new_reports >= 3:
                        # Ban for 1 day
                        banned_until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()
                        update('users', {
                            'reports': 0,
                            'boomerang_banned_until': banned_until
                        }, user_id=partner_id)
                        print(f"[BOOMERang] User {partner_id} banned globally until {banned_until} due to 3 reports.")
                        
                        # Emit a targeted socket event to force logout on the partner's client
                        emit('boomerang_global_ban', {'reason': 'You have been suspended for 24 hours due to multiple community reports.'}, room=partner_sid)
                    else:
                        # Increment reports
                        update('users', {'reports': new_reports}, user_id=partner_id)
                        print(f"[BOOMERang] User {users_dict.get(sid)} reported {partner_id}. Total reports: {new_reports}")
                    
                except Exception as e:
                    print(f"[BOOMERang] Error processing report: {e}")
                    
            # We don't need to manually disconnect them here because the frontend
            # calls `cleanup()` immediately after emitting this event, which 
            # triggers `boomerang_end_call`.
    
    @socketio.on('boomerang_end_call')
    def handle_end_call():
        """User ends the call (leave or next)."""
        sid = request.sid
        room_id = user_room_map.get(sid)
        
        if room_id and room_id in active_rooms:
            # Notify partner
            emit('boomerang_partner_left', {}, room=room_id, include_self=False)
            
            # Clean up
            if sid in user_room_map:
                del user_room_map[sid]
            
            # Remove user from room
            leave_room(room_id, sid=sid)
            
            # If room is now empty or has one user, clean it up
            if room_id in active_rooms:
                # Save history if this is the first person leaving (meaning call ended)
                if room_id in room_metadata:
                    meta = room_metadata[room_id]
                    # Check if we have two valid user IDs to save history
                    uids = list(meta['users'].values())
                    if len(uids) == 2 and all(uids):
                        try:
                            duration = (datetime.datetime.now() - meta['start_time']).total_seconds()
                            insert('meetup_history', {
                                'user1_id': uids[0],
                                'user2_id': uids[1],
                                'duration_seconds': int(duration)
                            })
                            print(f"[BOOMERang] Saved history for room {room_id}, duration {int(duration)}s")
                        except Exception as e:
                            print(f"[BOOMERang] Failed to save history: {e}")
                    
                    # Clean up metadata
                    del room_metadata[room_id]

                active_rooms[room_id].discard(sid)
                if len(active_rooms[room_id]) == 0:
                    del active_rooms[room_id]
            
            print(f"[BOOMERang] User {sid} ended call in room {room_id}")
    
    # NOTE: We don't add a @socketio.on('disconnect') here because
    # chat_events.py already has one, and having two causes conflicts.
    # BOOMERang cleanup is handled by boomerang_end_call event instead.
