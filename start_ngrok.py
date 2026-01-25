import os
import sys
from pyngrok import ngrok, conf
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define the port your Flask app is running on
PORT = 5000

def start_ngrok():
    # Check for auth token in environment
    auth_token = os.environ.get("NGROK_AUTHTOKEN")
    if auth_token:
        print(f"Setting ngrok auth token from environment...")
        ngrok.set_auth_token(auth_token)
    else:
        print("No NGROK_AUTHTOKEN env var found. Trying default ngrok config file...")

    print(f"Starting ngrok tunnel on port {PORT}...")
    try:
        # Create a public URL for the local web server
        public_url = ngrok.connect(PORT).public_url
        print(f"\n * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{PORT}\"")
        print(f" * Access your site at: {public_url}")
        print("\nPress CTRL+C to stop the tunnel...")
        
        # Keep the script running
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("\nShutting down ngrok...")
            ngrok.kill()
            sys.exit(0)

    except Exception as e:
        print(f"\nError starting ngrok: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_ngrok()
