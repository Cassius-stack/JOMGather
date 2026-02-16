"""
Profile routes - View, Edit, Settings (Zongrong's feature)
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/view')
@profile_bp.route('/view/<int:user_id>')
def view_profile(user_id=None):
    """View a user's profile."""
    from utils.supabase_db import fetch_one
    
    # If no user_id provided, show current logged-in user's profile
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            flash("Please log in to view your profile.", "warning")
            return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    if not user:
        return "User not found", 404
    
    is_deleted = user.get('is_deleted', False)
    return render_template('profile/view_profile.html', user=user, is_deleted=is_deleted)

@profile_bp.route('/edit', methods=['GET', 'POST'])
def edit_personal():
    """Edit current user's personal info."""
    from utils.supabase_db import fetch_one, update
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username')
            email = request.form.get('email')
            age = request.form.get('age')
            
            # Determine user_type based on age
            try:
                user_age = int(age) if age else 0
                user_type = 'senior' if user_age > 55 else 'youth'
            except ValueError:
                user_type = 'youth'
            
            # Update database
            update('users', {
                'username': username,
                'email': email,
                'age': int(age) if age else None,
                'user_type': user_type
            }, user_id=user_id)
            
            # Update session
            session['username'] = username
            session['user_type'] = user_type
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            print(f"Profile Update Error: {e}")
            flash(f"Error updating profile: {e}", "danger")
    
    return render_template('profile/edit_personal.html', user=user)

@profile_bp.route('/edit-social', methods=['GET', 'POST'])
def edit_social():
    """Edit current user's social profile (region, hobbies, skills)."""
    from utils.supabase_db import fetch_one, update
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('auth.login'))
    
    user = fetch_one('users', user_id=user_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            region = request.form.get('region')
            hobbies_str = request.form.get('hobbies', '')
            skills_str = request.form.get('skills', '')
            
            # Convert comma-separated strings to lists
            hobbies = [h.strip() for h in hobbies_str.split(',') if h.strip()]
            skills = [s.strip() for s in skills_str.split(',') if s.strip()]
            
            # Update database
            update('users', {
                'region': region if region else None,
                'hobbies': hobbies,
                'skills': skills
            }, user_id=user_id)
            
            flash("Social profile updated successfully!", "success")
            return redirect(url_for('profile.view_profile'))
        except Exception as e:
            print(f"Social Profile Update Error: {e}")
            flash(f"Error updating profile: {e}", "danger")
    
    return render_template('profile/edit_social.html', user=user)

@profile_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings page - only accessible to logged-in user for their own settings."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to access settings.", "warning")
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # TODO: Update settings in database
        pass
    return render_template('profile/settings.html')

@profile_bp.route('/delete-account', methods=['POST'])
def delete_account():
    """Delete user account — soft delete: anonymize user, preserve messages."""
    from utils.supabase_db import get_supabase
    
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for('auth.login'))
    
    try:
        supabase = get_supabase()
        
        # =====================================================
        # SOFT DELETE: Anonymize user instead of removing row.
        # This keeps messages intact (FK references stay valid)
        # but shows "Deleted Account" to other users.
        # =====================================================
        
        # 0. HANDLE COMMUNITIES (must happen BEFORE user update)
        try:
            # Remove user from community memberships
            supabase.table('community_members').delete().eq('user_id', user_id).execute()
        except:
            pass
        try:
            # Delete communities created by this user
            # First delete members/messages in those communities
            my_communities = supabase.table('communities').select('id').eq('created_by', user_id).execute()
            if my_communities.data:
                comm_ids = [c['id'] for c in my_communities.data]
                for comm_id in comm_ids:
                    try:
                        supabase.table('community_message_reactions').delete().eq('community_id', comm_id).execute()
                    except:
                        pass
                    try:
                        supabase.table('community_messages').delete().eq('community_id', comm_id).execute()
                    except:
                        pass
                    try:
                        supabase.table('community_members').delete().eq('community_id', comm_id).execute()
                    except:
                        pass
                supabase.table('communities').delete().eq('created_by', user_id).execute()
        except:
            pass
        
        # 1. ANONYMIZE USER RECORD (preserve user_id for FK integrity)
        supabase.table('users').update({
            'username': 'Deleted Account',
            'email': f'deleted_{user_id}@deleted.com',
            'password_hash': 'ACCOUNT_DELETED',
            'is_deleted': True,
            'age': None,
            'region': None,
            'hobbies': [],
            'skills': [],
        }).eq('user_id', user_id).execute()
        
        # Clear optional columns that may not exist in all deployments
        try:
            supabase.table('users').update({
                'sol_streak': 0,
                'last_sol_date': None
            }).eq('user_id', user_id).execute()
        except:
            pass
        
        # 2. DELETE PROFILE DATA (tables with ON DELETE CASCADE from users,
        #    but since we're not deleting the user row, we must delete manually)
        tables_to_clear = [
            ('profiles', 'user_id'),
            ('user_interests', 'user_id'),
            ('user_languages', 'user_id'),
            ('user_skills', 'user_id'),
            ('user_badges', 'user_id'),
            ('coins', 'user_id'),
            ('user_redeemed_rewards', 'user_id'),
            ('notifications', 'user_id'),
        ]
        for table, col in tables_to_clear:
            try:
                supabase.table(table).delete().eq(col, user_id).execute()
            except:
                pass
        
        # 3. DELETE SOCIAL CONNECTIONS
        try:
            supabase.table('friendships').delete().eq('user_id_1', user_id).execute()
            supabase.table('friendships').delete().eq('user_id_2', user_id).execute()
        except:
            pass
        try:
            supabase.table('friend_requests').delete().eq('sender_id', user_id).execute()
            supabase.table('friend_requests').delete().eq('receiver_id', user_id).execute()
        except:
            pass

        # 4. DELETE SUPPORT SWAP DATA
        try:
            supabase.table('support_matches').delete().eq('helper_id', user_id).execute()
            my_reqs = supabase.table('help_requests').select('id').eq('user_id', user_id).execute()
            if my_reqs.data:
                req_ids = [r['id'] for r in my_reqs.data]
                supabase.table('support_matches').delete().in_('request_id', req_ids).execute()
            supabase.table('help_requests').delete().eq('user_id', user_id).execute()
        except:
            pass

        # 5. DELETE SLICE OF LIFE DATA
        try:
            supabase.table('sol_submissions').delete().eq('user_id', user_id).execute()
            supabase.table('sol_invites').delete().eq('sender_id', user_id).execute()
            supabase.table('sol_invites').delete().eq('recipient_id', user_id).execute()
            supabase.table('sol_displays').delete().eq('creator_id', user_id).execute()
            supabase.table('sol_displays').delete().eq('partner_id', user_id).execute()
            supabase.table('sol_comments').delete().eq('user_id', user_id).execute()
            supabase.table('sol_likes').delete().eq('user_id', user_id).execute()
        except:
            pass

        # 6. DELETE OTHER ACTIVITY DATA
        try:
            supabase.table('meetup_history').delete().eq('user1_id', user_id).execute()
            supabase.table('meetup_history').delete().eq('user2_id', user_id).execute()
            supabase.table('cyber_challenges').delete().eq('user1_id', user_id).execute()
            supabase.table('cyber_challenges').delete().eq('user2_id', user_id).execute()
        except:
            pass

        # 7. HANDLE ASKAGRANDFRIEND DATA
        # Delete user's own questions (and all replies on them),
        # but anonymize their replies on other people's questions.
        try:
            # First, delete all replies on the user's OWN questions
            my_questions = supabase.table('questions').select('id').eq('user_id', user_id).execute()
            if my_questions.data:
                q_ids = [q['id'] for q in my_questions.data]
                for q_id in q_ids:
                    supabase.table('replies').delete().eq('question_id', q_id).execute()
            
            # Delete the user's own questions
            supabase.table('questions').delete().eq('user_id', user_id).execute()
            
            # Anonymize replies on OTHER people's questions
            supabase.table('replies').update({
                'author_name': 'Deleted Account'
            }).eq('user_id', user_id).execute()
        except:
            pass

        # 8. KEEP MESSAGES — do NOT delete from messages, community_messages,
        #    or community_message_reactions. The anonymized username
        #    ("Deleted Account") will show automatically when other users
        #    fetch the username from the users table.

        # Clear the session
        session.clear()
        
        flash("Your account has been deleted successfully.", "info")
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        print(f"Delete Account Error: {e}")
        flash(f"Error deleting account: {e}", "danger")
        return redirect(url_for('profile.settings'))

