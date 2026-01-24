"""
BOOMERang Socket.IO Events
Real-time video chat matching and signaling
"""

from flask_socketio import emit, join_room, leave_room
from flask import request
import uuid

# Queue of users waiting to be matched: {socket_id: user_info}
boomerang_queue = {}

# Active rooms: {room_id: {user1_sid, user2_sid}}
active_rooms = {}

# Map socket_id to room_id
user_room_map = {}


def register_boomerang_events(socketio):
    """Register all BOOMERang-related Socket.IO events."""
    
    @socketio.on('boomerang_join_queue')
    def handle_join_queue(data):
        """User joins the matching queue."""
        sid = request.sid
        user_name = data.get('name', 'Anonymous')
        
        print(f"[BOOMERang] {user_name} ({sid}) joining queue")
        
        # Check if there's someone waiting to be matched
        if boomerang_queue:
            # Get the first waiting user
            partner_sid, partner_info = next(iter(boomerang_queue.items()))
            del boomerang_queue[partner_sid]
            
            # Create a room for them
            room_id = f"boomerang_{uuid.uuid4().hex[:8]}"
            
            # Track the room
            active_rooms[room_id] = {sid, partner_sid}
            user_room_map[sid] = room_id
            user_room_map[partner_sid] = room_id
            
            # Both users join the Socket.IO room
            join_room(room_id, sid=sid)
            join_room(room_id, sid=partner_sid)
            
            print(f"[BOOMERang] Matched! {user_name} with {partner_info['name']} in room {room_id}")
            
            # Notify both users they're matched
            # User 1 (the one already waiting) is the initiator
            emit('boomerang_matched', {
                'room_id': room_id,
                'partner_name': user_name,
                'is_initiator': True
            }, room=partner_sid)
            
            # User 2 (the one who just joined) waits for offer
            emit('boomerang_matched', {
                'room_id': room_id,
                'partner_name': partner_info['name'],
                'is_initiator': False
            }, room=sid)
        else:
            # Add to queue
            boomerang_queue[sid] = {
                'name': user_name,
                'sid': sid
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
                active_rooms[room_id].discard(sid)
                if len(active_rooms[room_id]) == 0:
                    del active_rooms[room_id]
            
            print(f"[BOOMERang] User {sid} ended call in room {room_id}")
    
    # NOTE: We don't add a @socketio.on('disconnect') here because
    # chat_events.py already has one, and having two causes conflicts.
    # BOOMERang cleanup is handled by boomerang_end_call event instead.
