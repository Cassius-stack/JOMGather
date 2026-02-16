from utils.supabase_db import get_supabase
import datetime

def test_storage():
    supabase = get_supabase()
    bucket_name = 'social_uploads'

    print(f"Checking bucket: {bucket_name}")
    try:
        # Try to list buckets to see if it exists
        buckets = supabase.storage.list_buckets()
        exists = any(b.name == bucket_name for b in buckets)
        
        if not exists:
            print(f"Creating bucket {bucket_name}...")
            # Note: create_bucket might not be available or permissions restricted
            # Public bucket needed
            supabase.storage.create_bucket(bucket_name, options={'public': True})
            print("Bucket created.")
        else:
            print("Bucket already exists.")
            
        # Test Upload
        print("Testing upload...")
        test_filename = f"test_{datetime.datetime.now().timestamp()}.txt"
        res = supabase.storage.from_(bucket_name).upload(
            file=b"Hello Cloud",
            path=test_filename,
            file_options={"content-type": "text/plain"}
        )
        print(f"Upload result: {res}")
        
        # Get Public URL
        url = supabase.storage.from_(bucket_name).get_public_url(test_filename)
        print(f"Public URL: {url}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_storage()
