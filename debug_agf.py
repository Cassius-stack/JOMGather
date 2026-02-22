import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from utils.supabase_db import get_supabase

supabase = get_supabase()

print("--- TESTING QUERIES ---")

try:
    res = supabase.table('users').select('user_id, username, profile_picture, user_type').limit(1).execute()
    print("USERS OK")
except Exception as e:
    print("USERS ERROR:", e)

try:
    res = supabase.table('questions').select('id, title, created_at, likes').limit(1).execute()
    print("QUESTIONS OK")
except Exception as e:
    print("QUESTIONS ERROR:", e)

try:
    res = supabase.table('replies').select('reply_id, content, created_at, coins_awarded').limit(1).execute()
    print("REPLIES OK")
except Exception as e:
    print("REPLIES ERROR:", e)
