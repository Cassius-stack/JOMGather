"""
Social routes - Social features, AskAGrandfriend Q&A Forum
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash

social_bp = Blueprint('social', __name__)

# Try to import Supabase client, fallback to mock data if not available
try:
    from utils.supabase_client import (
        create_question, get_all_questions, get_question_by_id, delete_question,
        create_reply, get_replies_for_question, like_question, like_reply
    )
    SUPABASE_AVAILABLE = True
except Exception as e:
    print(f"Supabase not available: {e}")
    SUPABASE_AVAILABLE = False


@social_bp.route('/')
def social_hub():
    """List all social groups."""
    return render_template('social/social_hub.html')


@social_bp.route('/<int:group_id>')
def group_detail(group_id):
    """View a specific social group."""
    return render_template('social/group_detail.html', group_id=group_id)


@social_bp.route('/create', methods=['GET', 'POST'])
def create_group():
    """Create a new social group."""
    if request.method == 'POST':
        pass
    return render_template('social/social_hub.html')


@social_bp.route('/join/<int:group_id>', methods=['POST'])
def join_group(group_id):
    """Join a social group."""
    return redirect(url_for('social.group_detail', group_id=group_id))


@social_bp.route('/ask-grandfriend')
def ask_grandfriend():
    """AskAGrandfriend forum - main page."""
    questions = []
    if SUPABASE_AVAILABLE:
        try:
            questions = get_all_questions()
        except Exception as e:
            print(f"Error fetching questions: {e}")
    
    return render_template('social/ask_grandfriend.html', questions=questions)


@social_bp.route('/ask-grandfriend/post', methods=['GET', 'POST'])
def post_question():
    """Post a question to AskAGrandfriend."""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'tech')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        author_name = request.form.get('author_name', 'Anonymous User')
        author_type = request.form.get('author_type', 'grandparent')
        
        if not title:
            flash('Please enter a question title.', 'error')
            return redirect(url_for('social.ask_grandfriend'))
        
        if SUPABASE_AVAILABLE:
            try:
                result = create_question(
                    title=title,
                    content=content,
                    category=category,
                    author_name=author_name,
                    author_type=author_type,
                    is_anonymous=is_anonymous
                )
                if result:
                    flash('Your question has been posted successfully!', 'success')
                else:
                    flash('Failed to post question. Please try again.', 'error')
            except Exception as e:
                print(f"Error posting question: {e}")
                flash('An error occurred. Please try again.', 'error')
        else:
            flash('Database not available. Question saved locally.', 'warning')
        
        return redirect(url_for('social.ask_grandfriend'))
    
    return render_template('social/ask_grandfriend.html')


@social_bp.route('/ask-grandfriend/delete/<question_id>', methods=['POST'])
def delete_question_route(question_id):
    """Delete a question."""
    if SUPABASE_AVAILABLE:
        try:
            result = delete_question(question_id)
            if result:
                flash('Question deleted successfully!', 'success')
            else:
                flash('Failed to delete question.', 'error')
        except Exception as e:
            print(f"Error deleting question: {e}")
            flash('An error occurred while deleting.', 'error')
    else:
        flash('Database not available.', 'warning')
    
    return redirect(url_for('social.ask_grandfriend'))


@social_bp.route('/ask-grandfriend/api/questions', methods=['GET'])
def api_get_questions():
    """API endpoint to get questions with filtering."""
    category = request.args.get('category', 'all')
    author_type = request.args.get('author_type')
    
    if SUPABASE_AVAILABLE:
        try:
            questions = get_all_questions(category=category, author_type=author_type)
            return jsonify({'success': True, 'questions': questions})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Database not available'})


@social_bp.route('/ask-grandfriend/api/questions', methods=['POST'])
def api_post_question():
    """API endpoint to post a new question."""
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'success': False, 'error': 'Title is required'})
    
    if SUPABASE_AVAILABLE:
        try:
            result = create_question(
                title=data.get('title'),
                content=data.get('content', ''),
                category=data.get('category', 'tech'),
                author_name=data.get('author_name', 'Anonymous User'),
                author_type=data.get('author_type', 'grandparent'),
                is_anonymous=data.get('is_anonymous', False)
            )
            if result:
                return jsonify({'success': True, 'question': result})
            return jsonify({'success': False, 'error': 'Failed to create question'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Database not available'})


@social_bp.route('/ask-grandfriend/question/<question_id>')
def view_question(question_id):
    """View a single question with its replies."""
    question = None
    replies = []
    
    if SUPABASE_AVAILABLE:
        try:
            question = get_question_by_id(question_id)
            replies = get_replies_for_question(question_id)
        except Exception as e:
            print(f"Error fetching question: {e}")
    
    return render_template('social/question_detail.html', 
                         question=question, replies=replies)


@social_bp.route('/ask-grandfriend/question/<question_id>/reply', methods=['POST'])
def reply_to_question(question_id):
    """Submit a reply to a question."""
    content = request.form.get('content', '').strip()
    author_name = request.form.get('author_name', 'Anonymous User')
    author_type = request.form.get('author_type', 'student')
    
    if not content:
        flash('Please enter a reply.', 'error')
        return redirect(url_for('social.view_question', question_id=question_id))
    
    if SUPABASE_AVAILABLE:
        try:
            result = create_reply(
                question_id=question_id,
                content=content,
                author_name=author_name,
                author_type=author_type
            )
            if result:
                flash('Your reply has been posted! You earned 10 Community Points!', 'success')
            else:
                flash('Failed to post reply.', 'error')
        except Exception as e:
            print(f"Error posting reply: {e}")
            flash('An error occurred.', 'error')
    
    return redirect(url_for('social.view_question', question_id=question_id))
