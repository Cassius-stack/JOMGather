"""
Community routes - Community/Group chat functionality
Uses Supabase for database
"""

from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_db import get_supabase, fetch_all, fetch_one, insert, update, delete
from utils.auth_middleware import login_required
from datetime import datetime
import traceback

community_bp = Blueprint('community', __name__)


def get_current_user_id():
    """Get current user ID from session."""
    return session.get('user_id')


def get_current_username():
    """Get current username from session."""
    return session.get('username', 'Unknown')


# ============================================
# MAIN PAGE ROUTE
# ============================================

@community_bp.route('/')
@login_required
def community_hub():
    """Main community/group chat page."""
    return render_template('social/community.html')


# ============================================
# COMMUNITY API ENDPOINTS
# ============================================

@community_bp.route('/api/communities', methods=['GET'])
@login_required
def get_communities():
    """Get all communities the user is a member of."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get communities user is a member of
        memberships = supabase.table('community_members').select('community_id').eq('user_id', user_id).execute()
        community_ids = [m['community_id'] for m in memberships.data]
        
        if not community_ids:
            return jsonify([])
        
        # Fetch community details
        communities = supabase.table('communities').select('*').in_('community_id', community_ids).execute()
        
        result = []
        for comm in communities.data:
            # Get member count
            member_count = supabase.table('community_members').select('user_id', count='exact').eq('community_id', comm['community_id']).execute()
            
            # Get channels
            channels = supabase.table('community_channels').select('*').eq('community_id', comm['community_id']).execute()
            
            # Get roles (admins/moderators)
            roles = supabase.table('community_roles').select('*').eq('community_id', comm['community_id']).execute()
            admins = [r['user_id'] for r in roles.data if r['role'] == 'admin']
            moderators = [r['user_id'] for r in roles.data if r['role'] == 'moderator']
            
            # If no admin set, creator is admin
            if not admins and comm.get('created_by'):
                admins = [comm['created_by']]
            
            # Format channels with message data
            formatted_channels = []
            for ch in channels.data:
                # Get messages for this channel
                messages = supabase.table('community_messages').select('*').eq('channel_id', ch['channel_id']).order('created_at').execute()
                
                formatted_messages = []
                for msg in messages.data:
                    # Get user info
                    user = fetch_one('users', 'user_id, username', user_id=msg['user_id'])
                    
                    # Get reactions
                    reactions_data = supabase.table('community_message_reactions').select('*').eq('message_id', msg['message_id']).execute()
                    reactions = {}
                    for r in reactions_data.data:
                        if r['emoji'] not in reactions:
                            reactions[r['emoji']] = []
                        reactions[r['emoji']].append(r['user_id'])
                    
                    formatted_messages.append({
                        'id': msg['message_id'],
                        'userId': msg['user_id'],
                        'userName': user['username'] if user else 'Unknown',
                        'text': msg['content'],
                        'timestamp': msg['created_at'],
                        'reactions': reactions,
                        'replyTo': msg.get('reply_to_id'),
                        'edited': msg.get('is_edited', False)
                    })
                
                formatted_channels.append({
                    'id': ch['channel_id'],
                    'name': ch['name'],
                    'members': member_count.count or 0,
                    'private': False,
                    'isAnnouncement': ch.get('is_announcement', False),
                    'messages': formatted_messages
                })
            
            result.append({
                'id': comm['community_id'],
                'name': comm['name'],
                'description': comm.get('description', ''),
                'members': member_count.count or 0,
                'admins': admins,
                'moderators': moderators,
                'channels': formatted_channels
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching communities: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities', methods=['POST'])
@login_required
def create_community():
    """Create a new community."""
    try:
        user_id = get_current_user_id()
        data = request.json
        supabase = get_supabase()
        
        # Create community
        new_community = insert('communities', {
            'name': data['name'],
            'description': data.get('description', 'A new community space for discussions.'),
            'created_by': user_id
        })
        
        community_id = new_community['community_id']
        
        # Add creator as member
        insert('community_members', {
            'community_id': community_id,
            'user_id': user_id
        })
        
        # Add creator as admin
        insert('community_roles', {
            'community_id': community_id,
            'user_id': user_id,
            'role': 'admin'
        })
        
        # Create default General channel
        insert('community_channels', {
            'community_id': community_id,
            'name': 'General',
            'is_announcement': False,
            'created_by': user_id
        })
        
        return jsonify({
            'id': community_id,
            'name': new_community['name'],
            'description': new_community.get('description', ''),
            'members': 1,
            'admins': [user_id],
            'moderators': [],
            'channels': [{
                'id': 1,
                'name': 'General',
                'members': 1,
                'private': False,
                'isAnnouncement': False,
                'messages': []
            }]
        }), 201
    except Exception as e:
        print(f"Error creating community: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>', methods=['DELETE'])
@login_required
def delete_community(community_id):
    """Delete a community (admin only)."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Check if user is admin
        role = fetch_one('community_roles', community_id=community_id, user_id=user_id, role='admin')
        community = fetch_one('communities', community_id=community_id)
        
        if not role and community.get('created_by') != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete community (cascade will handle related tables)
        delete('communities', community_id=community_id)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting community: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CHANNEL API ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/channels', methods=['POST'])
@login_required
def create_channel(community_id):
    """Create a new channel in a community."""
    try:
        user_id = get_current_user_id()
        data = request.json
        
        # Verify membership
        membership = fetch_one('community_members', community_id=community_id, user_id=user_id)
        if not membership:
            return jsonify({'error': 'Not a member of this community'}), 403
        
        new_channel = insert('community_channels', {
            'community_id': community_id,
            'name': data['name'],
            'is_announcement': data.get('isAnnouncement', False),
            'created_by': user_id
        })
        
        return jsonify({
            'id': new_channel['channel_id'],
            'name': new_channel['name'],
            'members': 0,
            'private': False,
            'isAnnouncement': new_channel.get('is_announcement', False),
            'messages': []
        }), 201
    except Exception as e:
        print(f"Error creating channel: {e}")
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>', methods=['DELETE'])
@login_required
def delete_channel(community_id, channel_id):
    """Delete a channel (admin/moderator only)."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Check if user has permission
        role = supabase.table('community_roles').select('role').eq('community_id', community_id).eq('user_id', user_id).execute()
        has_permission = any(r['role'] in ['admin', 'moderator'] for r in role.data)
        
        if not has_permission:
            return jsonify({'error': 'Unauthorized'}), 403
        
        delete('community_channels', channel_id=channel_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting channel: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# MESSAGE API ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages', methods=['GET'])
@login_required
def get_messages(community_id, channel_id):
    """Get messages from a channel."""
    try:
        supabase = get_supabase()
        messages = supabase.table('community_messages').select('*').eq('channel_id', channel_id).order('created_at').execute()
        
        result = []
        for msg in messages.data:
            user = fetch_one('users', 'user_id, username', user_id=msg['user_id'])
            reactions_data = supabase.table('community_message_reactions').select('*').eq('message_id', msg['message_id']).execute()
            
            reactions = {}
            for r in reactions_data.data:
                if r['emoji'] not in reactions:
                    reactions[r['emoji']] = []
                reactions[r['emoji']].append(r['user_id'])
            
            result.append({
                'id': msg['message_id'],
                'userId': msg['user_id'],
                'userName': user['username'] if user else 'Unknown',
                'text': msg['content'],
                'timestamp': msg['created_at'],
                'reactions': reactions,
                'replyTo': msg.get('reply_to_id'),
                'edited': msg.get('is_edited', False)
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages', methods=['POST'])
@login_required
def send_message(community_id, channel_id):
    """Send a message to a channel."""
    try:
        user_id = get_current_user_id()
        username = get_current_username()
        data = request.json
        supabase = get_supabase()
        
        # Check if announcement channel - only admins can post
        channel = fetch_one('community_channels', channel_id=channel_id)
        if channel and channel.get('is_announcement'):
            role = fetch_one('community_roles', community_id=community_id, user_id=user_id, role='admin')
            if not role:
                return jsonify({'error': 'Only admins can post in announcement channels'}), 403
        
        new_message = insert('community_messages', {
            'channel_id': channel_id,
            'user_id': user_id,
            'content': data.get('text', ''),
            'reply_to_id': data.get('replyTo')
        })
        
        return jsonify({
            'id': new_message['message_id'],
            'userId': user_id,
            'userName': username,
            'text': new_message['content'],
            'timestamp': new_message['created_at'],
            'reactions': {},
            'replyTo': new_message.get('reply_to_id'),
            'edited': False
        }), 201
    except Exception as e:
        print(f"Error sending message: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>', methods=['PUT'])
@login_required
def edit_message(community_id, channel_id, message_id):
    """Edit a message."""
    try:
        user_id = get_current_user_id()
        data = request.json
        
        message = fetch_one('community_messages', message_id=message_id)
        if not message or message['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        update('community_messages', {'content': data['text'], 'is_edited': True}, message_id=message_id)
        
        return jsonify({
            'id': message_id,
            'userId': user_id,
            'userName': get_current_username(),
            'text': data['text'],
            'timestamp': message['created_at'],
            'reactions': {},
            'edited': True
        })
    except Exception as e:
        print(f"Error editing message: {e}")
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(community_id, channel_id, message_id):
    """Delete a message."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        message = fetch_one('community_messages', message_id=message_id)
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Check if user is author or has mod permissions
        is_author = message['user_id'] == user_id
        role = supabase.table('community_roles').select('role').eq('community_id', community_id).eq('user_id', user_id).execute()
        is_mod = any(r['role'] in ['admin', 'moderator'] for r in role.data)
        
        if not (is_author or is_mod):
            return jsonify({'error': 'Unauthorized'}), 403
        
        delete('community_messages', message_id=message_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting message: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# REACTION API ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/messages/<int:message_id>/reactions', methods=['POST'])
@login_required
def toggle_reaction(community_id, channel_id, message_id):
    """Add or remove a reaction to a message."""
    try:
        user_id = get_current_user_id()
        data = request.json
        emoji = data['emoji']
        supabase = get_supabase()
        
        # Check if reaction already exists
        existing = supabase.table('community_message_reactions').select('*').eq('message_id', message_id).eq('user_id', user_id).eq('emoji', emoji).execute()
        
        if existing.data:
            # Remove reaction
            supabase.table('community_message_reactions').delete().eq('message_id', message_id).eq('user_id', user_id).eq('emoji', emoji).execute()
        else:
            # Add reaction
            insert('community_message_reactions', {
                'message_id': message_id,
                'user_id': user_id,
                'emoji': emoji
            })
        
        # Return updated reactions
        reactions_data = supabase.table('community_message_reactions').select('*').eq('message_id', message_id).execute()
        reactions = {}
        for r in reactions_data.data:
            if r['emoji'] not in reactions:
                reactions[r['emoji']] = []
            reactions[r['emoji']].append(r['user_id'])
        
        return jsonify(reactions)
    except Exception as e:
        print(f"Error toggling reaction: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ROLE MANAGEMENT API ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/roles', methods=['POST'])
@login_required
def manage_roles(community_id):
    """Manage user roles (admin only)."""
    try:
        user_id = get_current_user_id()
        data = request.json
        target_user_id = data['userId']
        role = data['role']
        supabase = get_supabase()
        
        # Check if current user is admin
        is_admin = fetch_one('community_roles', community_id=community_id, user_id=user_id, role='admin')
        community = fetch_one('communities', community_id=community_id)
        
        if not is_admin and community.get('created_by') != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if role exists
        existing = fetch_one('community_roles', community_id=community_id, user_id=target_user_id, role=role)
        
        if existing:
            delete('community_roles', community_id=community_id, user_id=target_user_id, role=role)
        else:
            insert('community_roles', {
                'community_id': community_id,
                'user_id': target_user_id,
                'role': role
            })
        
        # Return updated community info
        roles = supabase.table('community_roles').select('*').eq('community_id', community_id).execute()
        admins = [r['user_id'] for r in roles.data if r['role'] == 'admin']
        moderators = [r['user_id'] for r in roles.data if r['role'] == 'moderator']
        
        if not admins and community.get('created_by'):
            admins = [community['created_by']]
        
        return jsonify({
            'id': community_id,
            'admins': admins,
            'moderators': moderators
        })
    except Exception as e:
        print(f"Error managing roles: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# USER API ENDPOINT
# ============================================

@community_bp.route('/api/user', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info."""
    user_id = get_current_user_id()
    return jsonify({
        'id': user_id,
        'name': get_current_username(),
        'isAdmin': False  # Will be set per-community on frontend
    })


# ============================================
# NOTIFICATIONS (Community-specific)
# ============================================

@community_bp.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get community notifications (placeholder - returns empty for now)."""
    # TODO: Implement community-specific notifications
    return jsonify([])


@community_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark notification as read."""
    return jsonify({'success': True})


@community_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    return jsonify({'success': True})
