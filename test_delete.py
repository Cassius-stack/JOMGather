"""Quick test to debug delete question via Supabase admin client."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import os

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
print(f"URL: {url}")
print(f"SERVICE_KEY length: {len(key) if key else 'NONE'}")
print(f"SERVICE_KEY starts with quote: {key[0] == chr(34) if key else 'N/A'}")

from supabase import create_client
admin = create_client(url, key)

# List all questions
res = admin.table('questions').select('id, title, user_id').execute()
print(f"\nAll questions ({len(res.data)}):")
for q in res.data:
    print(f"  id={q['id']}, user_id={q['user_id']}, title={q['title'][:50]}")

# Try deleting the first question that has a user_id matching our test user
if res.data:
    test_q = res.data[-1]  # last question
    qid = test_q['id']
    print(f"\nAttempting to delete question id={qid}, title='{test_q['title']}'...")
    
    # First delete replies
    try:
        del_replies = admin.table('replies').delete().eq('question_id', qid).execute()
        print(f"Deleted replies result: {del_replies.data}")
    except Exception as e:
        print(f"Replies delete error: {e}")
    
    # Then delete question
    try:
        del_result = admin.table('questions').delete().eq('id', qid).execute()
        print(f"Delete result: {del_result.data}")
    except Exception as e:
        print(f"Delete error: {e}")
    
    # Verify
    verify = admin.table('questions').select('id').eq('id', qid).execute()
    if verify.data:
        print("FAILED: Question still exists!")
    else:
        print("SUCCESS: Question was deleted!")
else:
    print("No questions found to test with.")
