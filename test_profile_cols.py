import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

res = supabase.table('users').select('*').limit(2).execute()
print("USER RECORD KEYS:")
if res.data:
    print(res.data[0].keys())
else:
    print("No users found.")
