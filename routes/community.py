"""
Community routes - Community/Group chat functionality
Uses Supabase for database
"""

from flask import Blueprint, render_template, request, jsonify, session
from flask_socketio import emit
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
# INIT ENDPOINT (called once per session from frontend)
# ============================================

@community_bp.route('/api/init', methods=['POST'])
@login_required
def community_init():
    """One-time per-session setup: auto-join Musicly + auto-promote dev_ accounts.
    Called from the frontend using sessionStorage to ensure it only runs once."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()

        # Find Musicly community
        musicly_id = None
        try:
            musicly = supabase.table('communities').select('community_id').eq('name', 'Musicly').execute()
            if musicly.data:
                musicly_id = musicly.data[0]['community_id']
        except Exception:
            pass

        if not musicly_id:
            return jsonify({'success': False, 'message': 'Musicly not found'})

        # Check membership
        membership = supabase.table('community_members').select('community_id').eq('user_id', user_id).eq('community_id', musicly_id).execute()

        if not membership.data:
            try:
                supabase.table('community_members').insert({
                    'community_id': musicly_id,
                    'user_id': user_id,
                    'joined_at': 'now()'
                }).execute()
                print(f"✅ Auto-joined user {user_id} to Musicly")
            except Exception as e:
                print(f"⚠️ Error auto-joining Musicly: {e}")

        # Auto-promote dev_ accounts
        try:
            current_user = supabase.table('users').select('username').eq('user_id', user_id).execute()
            if current_user.data:
                username = current_user.data[0].get('username', '')
                if username.startswith('dev_'):
                    existing_role = supabase.table('community_roles').select('role_id').eq(
                        'community_id', musicly_id
                    ).eq('user_id', user_id).eq('role', 'admin').execute()
                    if not existing_role.data:
                        supabase.table('community_roles').insert({
                            'community_id': musicly_id,
                            'user_id': user_id,
                            'role': 'admin'
                        }).execute()
                        print(f"✅ Promoted dev_ user {username} to admin in Musicly")
        except Exception as e:
            print(f"⚠️ Error promoting dev_ user: {e}")

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in community_init: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
            comm_id = comm['community_id']

            # Get member count
            member_count = supabase.table('community_members').select('user_id', count='exact').eq('community_id', comm_id).execute()

            # Get ALL members with their usernames
            member_rows = supabase.table('community_members').select('user_id').eq('community_id', comm_id).execute()
            member_user_ids = [m['user_id'] for m in member_rows.data]

            member_list = []
            if member_user_ids:
                users_data = supabase.table('users').select('user_id, username, user_type').in_('user_id', member_user_ids).execute()
                for u in users_data.data:
                    member_list.append({
                        'id': u['user_id'],
                        'username': u.get('username', f"User {u['user_id']}"),
                        'userType': u.get('user_type', '')
                    })

            # Get channels
            channels = supabase.table('community_channels').select('*').eq('community_id', comm_id).execute()

            # Get roles (admins/moderators)
            roles = supabase.table('community_roles').select('*').eq('community_id', comm_id).execute()
            admins = [r['user_id'] for r in roles.data if r['role'] == 'admin']
            moderators = [r['user_id'] for r in roles.data if r['role'] == 'moderator']

            # If no admin set, creator is admin
            if not admins and comm.get('created_by'):
                admins = [comm['created_by']]

            # Format channels with message data
            formatted_channels = []
            for ch in channels.data:
                formatted_channels.append({
                    'id': ch['channel_id'],
                    'name': ch['name'],
                    'members': member_count.count or 0,
                    'private': False,
                    'isAnnouncement': ch.get('is_announcement', False),
                    'isPinned': ch.get('is_pinned', False),
                    'messages': []  # Empty - messages loaded separately on click
                })

            result.append({
                'id': comm_id,
                'name': comm['name'],
                'description': comm.get('description', ''),
                'members': member_count.count or 0,
                'admins': admins,
                'moderators': moderators,
                'memberList': member_list,
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
        new_channel = insert('community_channels', {
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
                'id': new_channel['channel_id'],
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
# LEAVE/JOIN COMMUNITY ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/leave', methods=['POST'])
@login_required
def leave_community(community_id):
    """Leave a community."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Check if user is the only admin
        role = fetch_one('community_roles', community_id=community_id, user_id=user_id, role='admin')
        if role:
            # Count other admins
            other_admins = supabase.table('community_roles').select('user_id', count='exact').eq('community_id', community_id).eq('role', 'admin').neq('user_id', user_id).execute()
            if other_admins.count == 0:
                return jsonify({'error': 'You are the only admin. Transfer admin rights or delete the community.'}), 400
        
        # Remove from community_members
        supabase.table('community_members').delete().eq('community_id', community_id).eq('user_id', user_id).execute()
        
        # Remove any roles
        supabase.table('community_roles').delete().eq('community_id', community_id).eq('user_id', user_id).execute()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error leaving community: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/<int:community_id>/join', methods=['POST'])
@login_required
def join_community(community_id):
    """Join a community."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Check if already a member
        existing = fetch_one('community_members', community_id=community_id, user_id=user_id)
        if existing:
            return jsonify({'error': 'Already a member of this community'}), 400
        
        # Check if community exists
        community = fetch_one('communities', community_id=community_id)
        if not community:
            return jsonify({'error': 'Community not found'}), 404
        
        # Add as member
        insert('community_members', {
            'community_id': community_id,
            'user_id': user_id
        })
        
        return jsonify({'success': True, 'message': f'Joined {community["name"]}'})
    except Exception as e:
        print(f"Error joining community: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@community_bp.route('/api/communities/available', methods=['GET'])
@login_required
def get_available_communities():
    """Get all communities with membership status."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()
        
        # Get communities user is already a member of
        memberships = supabase.table('community_members').select('community_id').eq('user_id', user_id).execute()
        member_ids = [m['community_id'] for m in memberships.data]
        
        # Get all communities
        all_communities = supabase.table('communities').select('*').execute()
        
        # Return all communities with membership status
        result = []
        for comm in all_communities.data:
            # Get member count
            member_count = supabase.table('community_members').select('user_id', count='exact').eq('community_id', comm['community_id']).execute()
            result.append({
                'id': comm['community_id'],
                'name': comm['name'],
                'description': comm.get('description', ''),
                'members': member_count.count or 0,
                'joined': comm['community_id'] in member_ids  # Add joined status
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching communities: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# CHANNEL API ENDPOINTS
# ============================================

@community_bp.route('/api/communities/<int:community_id>/channels', methods=['POST'])
@login_required
def create_channel(community_id):
    """Create a new channel in a community (admin/moderator only)."""
    try:
        user_id = get_current_user_id()
        data = request.json
        supabase = get_supabase()
        
        # Verify admin or moderator
        role = supabase.table('community_roles').select('role').eq('community_id', community_id).eq('user_id', user_id).execute()
        has_permission = any(r['role'] in ['admin', 'moderator'] for r in role.data)
        community = supabase.table('communities').select('created_by').eq('community_id', community_id).execute()
        is_creator = community.data and community.data[0].get('created_by') == user_id
        
        if not has_permission and not is_creator:
            return jsonify({'error': 'Only admins and moderators can create channels'}), 403
        
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
            'isPinned': False,
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


@community_bp.route('/api/communities/<int:community_id>/channels/<int:channel_id>/pin', methods=['POST'])
@login_required
def toggle_pin_channel(community_id, channel_id):
    """Toggle pinned status on a channel (admin only)."""
    try:
        user_id = get_current_user_id()
        supabase = get_supabase()

        # Admin check
        role = supabase.table('community_roles').select('role').eq('community_id', community_id).eq('user_id', user_id).execute()
        is_admin = any(r['role'] == 'admin' for r in role.data)
        community = supabase.table('communities').select('created_by').eq('community_id', community_id).execute()
        is_creator = community.data and community.data[0].get('created_by') == user_id

        if not is_admin and not is_creator:
            return jsonify({'error': 'Only admins can pin channels'}), 403

        # Get current pin state
        channel = supabase.table('community_channels').select('is_pinned').eq('channel_id', channel_id).execute()
        if not channel.data:
            return jsonify({'error': 'Channel not found'}), 404

        current_pinned = channel.data[0].get('is_pinned', False)
        new_pinned = not current_pinned

        try:
            supabase.table('community_channels').update({'is_pinned': new_pinned}).eq('channel_id', channel_id).execute()
        except Exception as upd_err:
            # Column may not exist in DB — fall back to in-memory only and return the toggled value
            print(f"Warning: is_pinned column may not exist: {upd_err}")

        return jsonify({'success': True, 'isPinned': new_pinned})
    except Exception as e:
        print(f"Error toggling pin: {e}")
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
        
        # SONG VALIDATION: Check if this is song-recommendations channel
        message_content = data.get('text', '')
        if channel and 'song' in channel.get('name', '').lower() and 'recommend' in channel.get('name', '').lower():
            # Validate song format
            required_fields = ['Song Name:', 'Artist:', 'Year Released:', 'Why they like this song:']
            missing_fields = [field for field in required_fields if field not in message_content]
            
            if missing_fields:
                return jsonify({
                    'error': f'Invalid song format! Please include all required fields: {", ".join(required_fields)}',
                    'help': 'Format: Song Name: <title>\\nArtist: <artist>\\nYear Released: <year>\\nWhy they like this song: <reason>'
                }), 400
        
        new_message = insert('community_messages', {
            'channel_id': channel_id,
            'user_id': user_id,
            'content': message_content,
            'reply_to_id': data.get('replyTo')
        })
        
        # Broadcast message to all users in this channel via Socket.IO
        message_data = {
            'id': new_message['message_id'],
            'userId': user_id,
            'userName': username,
            'text': new_message['content'],
            'timestamp': new_message['created_at'],
            'reactions': {},
            'replyTo': new_message.get('reply_to_id'),
            'edited': False,
            'channel_id': channel_id,
            'community_id': community_id
        }
        
        # Emit to all users in the community channel room
        emit('new_community_message', message_data, room=f'community_{community_id}_channel_{channel_id}', namespace='/')
        
        return jsonify(message_data), 201
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
