"""
Supabase client utility for database operations.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

# Create Supabase client
supabase: Client = None

def get_supabase_client() -> Client:
    """Get or create Supabase client instance."""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and Key must be set in .env file")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


# Question operations
def create_question(title: str, content: str, category: str, author_name: str, 
                   author_type: str = 'grandparent', is_anonymous: bool = False) -> dict:
    """Create a new question."""
    client = get_supabase_client()
    data = {
        'title': title,
        'content': content,
        'category': category,
        'author_name': 'Anonymous' if is_anonymous else author_name,
        'author_type': author_type,
        'is_anonymous': is_anonymous
    }
    result = client.table('questions').insert(data).execute()
    return result.data[0] if result.data else None


def get_all_questions(category: str = None, author_type: str = None) -> list:
    """Get all questions with optional filtering."""
    client = get_supabase_client()
    query = client.table('questions').select('*').order('created_at', desc=True)
    
    if category and category != 'all':
        query = query.eq('category', category)
    if author_type:
        query = query.eq('author_type', author_type)
    
    result = query.execute()
    return result.data if result.data else []


def get_question_by_id(question_id: str) -> dict:
    """Get a single question by ID."""
    client = get_supabase_client()
    result = client.table('questions').select('*').eq('id', question_id).single().execute()
    return result.data if result.data else None


def delete_question(question_id: str) -> bool:
    """Delete a question by ID."""
    client = get_supabase_client()
    try:
        result = client.table('questions').delete().eq('id', question_id).execute()
        print(f"Delete result: {result}")  # Debug output
        # Check if deletion was successful
        if result.data is not None:
            return True
        return True  # Supabase returns empty data on successful delete
    except Exception as e:
        print(f"Error deleting question: {e}")
        return False


# Reply operations
def create_reply(question_id: str, content: str, author_name: str, 
                author_type: str = 'student') -> dict:
    """Create a reply to a question."""
    client = get_supabase_client()
    data = {
        'question_id': question_id,
        'content': content,
        'author_name': author_name,
        'author_type': author_type
    }
    result = client.table('replies').insert(data).execute()
    
    # Update replies count on the question
    if result.data:
        client.rpc('increment_replies_count', {'q_id': question_id}).execute()
    
    return result.data[0] if result.data else None


def get_replies_for_question(question_id: str) -> list:
    """Get all replies for a question."""
    client = get_supabase_client()
    result = client.table('replies').select('*').eq('question_id', question_id).order('created_at').execute()
    return result.data if result.data else []


# Like operations
def like_question(question_id: str, user_id: str) -> bool:
    """Like a question."""
    client = get_supabase_client()
    try:
        client.table('question_likes').insert({
            'question_id': question_id,
            'user_id': user_id
        }).execute()
        # Increment likes count
        client.rpc('increment_question_likes', {'q_id': question_id}).execute()
        return True
    except Exception:
        return False


def like_reply(reply_id: str, user_id: str) -> bool:
    """Like a reply (awards points to the replier)."""
    client = get_supabase_client()
    try:
        client.table('reply_likes').insert({
            'reply_id': reply_id,
            'user_id': user_id
        }).execute()
        # Increment likes count
        client.rpc('increment_reply_likes', {'r_id': reply_id}).execute()
        return True
    except Exception:
        return False
