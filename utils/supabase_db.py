"""
Supabase Database Helper for JOMGather
Provides connection and query utilities for Supabase (PostgreSQL)
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')

# Create Supabase client (singleton)
_supabase_client: Client = None


def get_supabase() -> Client:
    """Get the Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ============================================
# DATABASE QUERY HELPERS
# ============================================

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
    raise NotImplementedError("Use table methods (fetch_all, insert, etc.) instead")
