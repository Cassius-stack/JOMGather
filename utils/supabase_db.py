"""
Supabase Database Helper for JOMGather
Provides connection and query utilities for Supabase (PostgreSQL)
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from httpx import Timeout

# Load environment variables from .env
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')  # Service role key for admin operations

# Timeout config: 15s to connect, 30s to read response
_SUPABASE_TIMEOUT = Timeout(connect=15.0, read=30.0, write=30.0, pool=15.0)

# Create Supabase client (singleton)
_supabase_client: Client = None
_supabase_admin_client: Client = None


def get_supabase() -> Client:
    """Get the Supabase client instance with timeout and auto-reconnect."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _create_client()
    return _supabase_client


def _create_client() -> Client:
    """Create a new Supabase client with proper timeout configuration."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Apply timeout to the internal httpx client used by PostgREST
    try:
        if hasattr(client, 'postgrest') and hasattr(client.postgrest, 'session'):
            client.postgrest.session.timeout = _SUPABASE_TIMEOUT
    except Exception:
        pass  # Some versions may not expose this — fail silently
    
    return client


def reconnect_supabase() -> Client:
    """Force-recreate the Supabase clients (useful after connection errors)."""
    global _supabase_client, _supabase_admin_client
    _supabase_client = _create_client()
    _supabase_admin_client = None  # Reset admin client too so it's recreated on next use
    return _supabase_client


def get_supabase_admin() -> Client:
    """Get a Supabase admin client using the service role key (bypasses RLS).
    Falls back to the anon client if no service key is set."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        if SUPABASE_URL and SUPABASE_SERVICE_KEY:
            _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            # Apply timeout to admin client just like the regular client
            try:
                if hasattr(_supabase_admin_client, 'postgrest') and hasattr(_supabase_admin_client.postgrest, 'session'):
                    _supabase_admin_client.postgrest.session.timeout = _SUPABASE_TIMEOUT
            except Exception:
                pass
        else:
            # Fallback: use anon client (coins updates may fail if RLS is restrictive)
            print("[WARNING] SUPABASE_SERVICE_KEY not set. Falling back to anon key for admin operations.")
            return get_supabase()
    return _supabase_admin_client


# ============================================
# DATABASE QUERY HELPERS
# ============================================

import time
from functools import wraps

def retry_query(max_retries=3, delay=1):
    """Decorator to retry Supabase queries on network errors with auto-reconnect."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    import traceback
                    # Check for transient network/socket errors
                    error_str = str(e).lower()
                    retryable = any(kw in error_str for kw in [
                        "10035", "timeout", "transport", "read",
                        "connection", "reset", "502", "503", "504",
                        "temporarily", "unavailable", "eof", "closed",
                        "pool", "httpx"
                    ])
                    if retryable:
                        print(f"[Supabase] Retry {attempt+1}/{max_retries} due to error: {e}")
                        last_exception = e
                        # Force-recreate client on connection issues
                        reconnect_supabase()
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        raise e
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

@retry_query()
def fetch_all(table: str, columns: str = "*", **filters):
    """
    Fetch all rows from a table.
    
    Usage:
        users = fetch_all('users')
        active_users = fetch_all('users', user_type='youth')
    """
    supabase = get_supabase()
    query = supabase.table(table).select(columns)
    
    for key, value in filters.items():
        query = query.eq(key, value)
    
    response = query.execute()
    return response.data


@retry_query()
def fetch_one(table: str, columns: str = "*", **filters):
    """
    Fetch a single row from a table.
    
    Usage:
        user = fetch_one('users', user_id=1)
    """
    supabase = get_supabase()
    query = supabase.table(table).select(columns)
    
    for key, value in filters.items():
        query = query.eq(key, value)
    
    response = query.limit(1).execute()
    return response.data[0] if response.data else None


@retry_query()
def insert(table: str, data: dict):
    """
    Insert a new row into a table.
    
    Usage:
        new_msg = insert('messages', {
            'sender_id': 1,
            'receiver_id': 2,
            'content': 'Hello!'
        })
    """
    supabase = get_supabase()
    response = supabase.table(table).insert(data).execute()
    return response.data[0] if response.data else None


@retry_query()
def update(table: str, data: dict, **filters):
    """
    Update rows in a table.
    
    Usage:
        update('users', {'username': 'new_name'}, user_id=1)
    """
    supabase = get_supabase()
    query = supabase.table(table).update(data)
    
    for key, value in filters.items():
        query = query.eq(key, value)
    
    response = query.execute()
    return response.data


@retry_query()
def delete(table: str, **filters):
    """
    Delete rows from a table.
    
    Usage:
        delete('messages', message_id=5)
    """
    supabase = get_supabase()
    query = supabase.table(table).delete()
    
    for key, value in filters.items():
        query = query.eq(key, value)
    
    response = query.execute()
    return response.data


# ============================================
# RAW SQL QUERY (using RPC)
# ============================================

def execute_sql(sql: str, params: dict = None):
    """
    Execute raw SQL using Supabase RPC.
    Note: You need to create an RPC function in Supabase for this.
    For complex queries, prefer using the table methods above.
    """
    supabase = get_supabase()
    # This requires setting up an RPC function in Supabase
    # For now, use table methods for most operations

# ============================================
# STORAGE HELPERS
# ============================================

def upload_file(file_storage, bucket: str = 'images', path: str = None) -> str:
    """
    Upload a file to Supabase Storage and return the public URL.
    
    Args:
        file_storage: The Flask FileStorage object (from request.files)
        bucket: Name of the Supabase storage bucket
        path: Optional specific path/filename. If None, uses original filename.
    
    Returns:
        str: Public URL of the uploaded file
    """
    try:
        supabase = get_supabase()
        file_bytes = file_storage.read()
        content_type = file_storage.content_type
        
        # Determine path
        filename = path if path else file_storage.filename
        
        # Upload
        supabase.storage.from_(bucket).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        # Get Public URL
        public_url = supabase.storage.from_(bucket).get_public_url(filename)
        return public_url
        
    except Exception as e:
        print(f"Supabase Storage Error: {e}")
        # Fallback to returning None or re-raising?
        # Re-raising allows the caller to handle it (e.g. show flash message)
        raise e
