"""
Start ngrok tunnel for BOOMERang video chat
Run this AFTER starting Flask (py app.py)
"""
from pyngrok import ngrok
import os

# Kill any existing ngrok processes first
ngrok.kill()

# Set auth token via environment variable (more reliable)
os.environ["NGROK_AUTHTOKEN"] = "38hFt9ayV9zNDvjHU3xiMAnniT3_FHbfhyuU3r4WkKeebm63"

# Start tunnel
print("Starting ngrok tunnel...")
try:
    tunnel = ngrok.connect(5000)
    
    print("\n" + "="*60)
    print("🎉 BOOMERang HTTPS URL Ready!")
    print("="*60)
    print(f"\n👉 Share this URL with your friend:\n")
    print(f"   {tunnel.public_url}/activities/boomerang")
    print(f"\n📹 Camera will work for both of you!")
    print("="*60)
    print("\nPress Ctrl+C to stop the tunnel")
    
    # Keep running
    ngrok_process = ngrok.get_ngrok_process()
    ngrok_process.proc.wait()
except KeyboardInterrupt:
    print("\nShutting down...")
    ngrok.kill()
except Exception as e:
    print(f"Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure Flask is running (py app.py)")
    print("2. Make sure Malwarebytes allows ngrok")
    print("3. Try again")
    ngrok.kill()
