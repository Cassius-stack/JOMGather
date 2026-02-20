"""
Scheduler utilities for JOMGather.
Handles background tasks like the daily Cyber Challenge.
"""

import threading
import time
import datetime
import random
from utils.supabase_db import get_supabase, fetch_all, insert

def start_scheduler(socketio):
    """Start the background scheduler thread."""
    thread = threading.Thread(target=run_scheduler, args=(socketio,), daemon=True)
    thread.start()
    print("[Scheduler] Background scheduler started.")

def run_scheduler(socketio):
    """Main scheduler loop."""
    # Track if we've already sent challenges for the current day
    last_sent_date = None
    
    while True:
        try:
            # Current time in GMT+8
            # (Assuming server is in UTC, add 8 hours)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            now_gmt8 = now_utc + datetime.timedelta(hours=8)
            
            # Check if it's 12:00 PM
            if now_gmt8.hour == 12 and now_gmt8.minute == 00:
                current_date = now_gmt8.date()
                if last_sent_date != current_date:
                    print(f"[Scheduler] It's {now_gmt8.hour}:{now_gmt8.minute} GMT+8. Sending daily challenges...")
                    send_daily_cyber_challenges(socketio)
                    last_sent_date = current_date
            
            # Sleep for 30 seconds before checking again
            # Using 30s instead of 60s to avoid missing the specific minute
            time.sleep(30)
            
        except Exception as e:
            print(f"[Scheduler] Error in scheduler loop: {e}")
            time.sleep(60) # Sleep longer on error

def send_daily_cyber_challenges(socketio):
    """Identify Senior-Youth pairs and send a Cyber Challenge to each."""
    try:
        supabase = get_supabase()
        
        # 1. Fetch all accepted friendships
        friendships = fetch_all('friendships', status='accepted')
        if not friendships:
            print("[Scheduler] No accepted friendships found.")
            return
            
        # 2. Fetch all users to know their types
        users = fetch_all('users')
        user_type_map = {u['user_id']: u.get('user_type', 'youth') for u in users}
        
        # 3. Identify Senior-Youth pairs
        pairs = []
        for f in friendships:
            u1_id = f['user_id_1']
            u2_id = f['user_id_2']
            
            t1 = user_type_map.get(u1_id)
            t2 = user_type_map.get(u2_id)
            
            if (t1 == 'senior' and t2 == 'youth') or (t1 == 'youth' and t2 == 'senior'):
                pairs.append((u1_id, u2_id))
        
        print(f"[Scheduler] Found {len(pairs)} Senior-Youth pairs for daily challenges.")
        
        # 4. For each pair, send a challenge
        scenario_ids = [1, 2, 3] # Based on SCENARIO_ANSWERS in chat_events.py
        
        for sender_id, receiver_id in pairs:
            # We'll pick one as the "sender" (arbitrarily u1)
            # and send the challenge
            content = "!cyber"
            scenario_id = random.choice(scenario_ids)
            
            # Insert message
            new_message = insert('messages', {
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'content': content
            })
            
            if new_message:
                message_id = new_message['message_id']
                # Create challenge entry
                challenge = insert('cyber_challenges', {
                    'message_id': message_id,
                    'scenario_id': scenario_id,
                    'user1_id': sender_id,
                    'user2_id': receiver_id,
                    'status': 'pending'
                })
                
                if challenge:
                    challenge_id = challenge['challenge_id']
                    
                    # Prepare data for Socket.IO parity with handle_send_message
                    response_data = {
                        'id': message_id,
                        'sender_id': sender_id,
                        'receiver_id': receiver_id,
                        'text': content,
                        'image_url': None,
                        'is_cyber_challenge': True,
                        'challenge_id': challenge_id,
                        'scenario_id': scenario_id,
                        'sent_at': new_message.get('sent_at')
                    }
                    
                    # Emit to rooms
                    # Room name format: chat_minID_maxID
                    ids = sorted([int(sender_id), int(receiver_id)])
                    room = f"chat_{ids[0]}_{ids[1]}"
                    
                    # Global broadcast for background task to ensure reachability
                    response_data['is_broadcast'] = True
                    try:
                        # Explicitly specify namespace '/' to ensure reachability from background thread
                        socketio.emit('new_message', response_data, namespace='/')
                        # Add a global force refresh event as a secondary trigger
                        socketio.emit('FORCE_CHAT_REFRESH', {
                            'target_id': receiver_id,
                            'sender_id': sender_id
                        }, namespace='/')
                        
                        print(f"[Scheduler] Daily challenge and FORCE_REFRESH broadcast successful for pair ({sender_id}, {receiver_id})")
                    except Exception as emit_err:
                        print(f"[Scheduler] Global emit FAILED: {emit_err}")

    except Exception as e:
        print(f"[Scheduler] Critical error sending daily challenges: {e}")
