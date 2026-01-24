from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# In-memory data storage (in production, use a database)
communities = [
    {
        'id': 1,
        'name': 'Tech Community',
        'members': 2345,
        'description': 'A place for tech enthusiasts to share knowledge, ask questions, and stay updated with the latest in technology.',
        'admins': [1],
        'moderators': [],
        'channels': [
            {
                'id': 1,
                'name': 'Announcements',
                'members': 1234,
                'private': False,
                'isAnnouncement': True,
                'messages': [
                    {
                        'id': 1,
                        'userId': 1,
                        'userName': 'You',
                        'text': 'Welcome to the community!',
                        'timestamp': datetime.now().isoformat(),
                        'reactions': {'👍': [2, 3], '❤️': [2]},
                        'readBy': [1, 2],
                        'attachments': []
                    }
                ]
            },
            {
                'id': 2,
                'name': 'General Discussion',
                'members': 856,
                'private': False,
                'isAnnouncement': False,
                'messages': [
                    {
                        'id': 2,
                        'userId': 2,
                        'userName': 'Alice',
                        'text': 'Hey everyone!',
                        'timestamp': datetime.now().isoformat(),
                        'reactions': {},
                        'readBy': [1, 2],
                        'attachments': []
                    }
                ]
            }
        ]
    }
]

notifications = [
    {
        'id': 1,
        'type': 'message',
        'text': 'New message in General Discussion',
        'timestamp': datetime.now().isoformat(),
        'read': False
    }
]

current_user = {'id': 1, 'name': 'You', 'isAdmin': True}

# Helper functions
def find_community(community_id):
    return next((c for c in communities if c['id'] == community_id), None)

def find_channel(community_id, channel_id):
    community = find_community(community_id)
    if community:
        return next((ch for ch in community['channels'] if ch['id'] == channel_id), None)
    return None

# API Routes

@app.route('/api/communities', methods=['GET'])
def get_communities():
    return jsonify(communities)

@app.route('/api/communities', methods=['POST'])
def create_community():
    data = request.json
    new_community = {
        'id': len(communities) + 1,
        'name': data['name'],
        'members': 1,
        'description': data.get('description', 'A new community space for discussions.'),
        'admins': [current_user['id']],
        'moderators': [],
        'channels': [
            {
                'id': 1,
                'name': 'General',
                'members': 1,
                'private': False,
                'isAnnouncement': False,
                'messages': []
            }
        ]
    }
    communities.append(new_community)
    return jsonify(new_community), 201

@app.route('/api/communities/<int:community_id>', methods=['DELETE'])
def delete_community(community_id):
    global communities
    community = find_community(community_id)
    if not community:
        return jsonify({'error': 'Community not found'}), 404
    
    if current_user['id'] not in community['admins']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    communities = [c for c in communities if c['id'] != community_id]
    return jsonify({'success': True})

@app.route('/api/communities/<int:community_id>/channels', methods=['POST'])
def create_channel(community_id):
    community = find_community(community_id)
    if not community:
        return jsonify({'error': 'Community not found'}), 404
    
    data = request.json
    new_channel = {
        'id': len(community['channels']) + 1,
        'name': data['name'],
        'members': 0,
        'private': False,
        'isAnnouncement': data.get('isAnnouncement', False),
        'messages': []
    }
    community['channels'].append(new_channel)
    return jsonify(new_channel), 201

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>', methods=['DELETE'])
def delete_channel(community_id, channel_id):
    community = find_community(community_id)
    if not community:
        return jsonify({'error': 'Community not found'}), 404
    
    if current_user['id'] not in community['admins'] and current_user['id'] not in community['moderators']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    community['channels'] = [ch for ch in community['channels'] if ch['id'] != channel_id]
    return jsonify({'success': True})

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages', methods=['GET'])
def get_messages(community_id, channel_id):
    channel = find_channel(community_id, channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    return jsonify(channel['messages'])

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages', methods=['POST'])
def send_message(community_id, channel_id):
    community = find_community(community_id)
    channel = find_channel(community_id, channel_id)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    # Check permissions for announcement channels
    if channel['isAnnouncement'] and current_user['id'] not in community['admins']:
        return jsonify({'error': 'Only admins can post in announcement channels'}), 403
    
    data = request.json
    new_message = {
        'id': len(channel['messages']) + 1,
        'userId': current_user['id'],
        'userName': current_user['name'],
        'text': data.get('text', ''),
        'timestamp': datetime.now().isoformat(),
        'reactions': {},
        'readBy': [current_user['id']],
        'replyTo': data.get('replyTo'),
        'attachments': data.get('attachments', []),
        'edited': False
    }
    channel['messages'].append(new_message)
    
    # Create notification
    notifications.append({
        'id': len(notifications) + 1,
        'type': 'message',
        'text': f'New message in {channel["name"]}',
        'timestamp': datetime.now().isoformat(),
        'read': False
    })
    
    return jsonify(new_message), 201

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>', methods=['PUT'])
def edit_message(community_id, channel_id, message_id):
    channel = find_channel(community_id, channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    message = next((m for m in channel['messages'] if m['id'] == message_id), None)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    if message['userId'] != current_user['id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    message['text'] = data['text']
    message['edited'] = True
    return jsonify(message)

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
def delete_message(community_id, channel_id, message_id):
    community = find_community(community_id)
    channel = find_channel(community_id, channel_id)
    
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    message = next((m for m in channel['messages'] if m['id'] == message_id), None)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    # Check permissions
    is_author = message['userId'] == current_user['id']
    is_mod = current_user['id'] in community['admins'] or current_user['id'] in community['moderators']
    
    if not (is_author or is_mod):
        return jsonify({'error': 'Unauthorized'}), 403
    
    channel['messages'] = [m for m in channel['messages'] if m['id'] != message_id]
    return jsonify({'success': True})

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>/reactions', methods=['POST'])
def add_reaction(community_id, channel_id, message_id):
    channel = find_channel(community_id, channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    message = next((m for m in channel['messages'] if m['id'] == message_id), None)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    data = request.json
    emoji = data['emoji']
    
    if emoji not in message['reactions']:
        message['reactions'][emoji] = []
    
    if current_user['id'] in message['reactions'][emoji]:
        message['reactions'][emoji].remove(current_user['id'])
        if len(message['reactions'][emoji]) == 0:
            del message['reactions'][emoji]
    else:
        message['reactions'][emoji].append(current_user['id'])
        
        # Create notification if reacting to someone else's message
        if message['userId'] != current_user['id']:
            notifications.append({
                'id': len(notifications) + 1,
                'type': 'reaction',
                'text': f'{current_user["name"]} reacted {emoji} to your message',
                'timestamp': datetime.now().isoformat(),
                'read': False
            })
    
    return jsonify(message['reactions'])

@app.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>/read', methods=['POST'])
def mark_message_read(community_id, channel_id, message_id):
    channel = find_channel(community_id, channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    message = next((m for m in channel['messages'] if m['id'] == message_id), None)
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    if current_user['id'] not in message['readBy']:
        message['readBy'].append(current_user['id'])
    
    return jsonify(message['readBy'])

@app.route('/api/communities/<int:community_id>/roles', methods=['POST'])
def manage_roles(community_id):
    community = find_community(community_id)
    if not community:
        return jsonify({'error': 'Community not found'}), 404
    
    if current_user['id'] not in community['admins']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    user_id = data['userId']
    role = data['role']
    
    if role == 'admin':
        if user_id in community['admins']:
            community['admins'].remove(user_id)
        else:
            community['admins'].append(user_id)
    elif role == 'moderator':
        if user_id in community['moderators']:
            community['moderators'].remove(user_id)
        else:
            community['moderators'].append(user_id)
    
    return jsonify(community)

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    return jsonify(notifications)

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    notif = next((n for n in notifications if n['id'] == notif_id), None)
    if notif:
        notif['read'] = True
    return jsonify(notif)

@app.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    for notif in notifications:
        notif['read'] = True
    return jsonify({'success': True})

@app.route('/api/user', methods=['GET'])
def get_current_user():
    return jsonify(current_user)

if __name__ == '__main__':
    app.run(debug=True, port=5000)