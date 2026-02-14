# Deployment Guide for JOMGather

This guide answers your questions and provides step-by-step instructions for deploying your Flask application to Render or Railway.

## 1. Branch Management
> **"Do your branches automatically delete itself?"**

**No.** Git branches are permanent until you manually delete them. You can switch between branches anytime using `git checkout <branch-name>`. This `deployment-guide` branch will remain available in your repository unless you or a collaborator deletes it.

## 2. Hosting Recommendation
> **"What can I use? Render? Railway? What do you suggest?"**

I strongly recommend **Render** for this project because:
1.  **Free Tier:** It offers a generous free tier for Web Services.
2.  **Persistent Processes:** Unlike Vercel, Render keeps your application running, which is *required* for the WebSocket features (chat, video calls) to work reliably.
3.  **Ease of Use:** It automatically detects Python apps.

**Railway** is also excellent and often faster, but their free tier is trial-based (credits), whereas Render has a perpetual free instance type.

## 3. Render Deployment Instructions (Step-by-Step)

The reason your previous attempts likely failed ("startup command... always doesnt work") is because standard Gunicorn configurations do not support the specific WebSocket mode (`threading`) used in this app.

I have added a `Procfile` to this branch which automatically tells Render the correct command. However, you should also know the manual settings:

### Configuration Settings
When creating a new **Web Service** on Render:

1.  **Connect GitHub:** Select your repository `JOMGather`.
2.  **Environment:** Select `Python 3`.
3.  **Build Command:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Start Command:**
    *   *Option A (Automatic):* Leave it blank (Render will read the `Procfile` I just created).
    *   *Option B (Manual):* Copy-paste this EXACT command:
        ```bash
        gunicorn --worker-class gthread --workers 1 --threads 8 app:app
        ```
    *   *Why this command?*
        - `app:app`: Tells Gunicorn to look in `app.py` for the `app` object.
        - `--worker-class gthread`: Enables multi-threading support required by `Flask-SocketIO` in this app.
        - `--workers 1`: Ensures all WebSocket connections go to the same process (crucial for chat to work without a complex Redis setup).
        - `--threads 8`: Allows the server to handle multiple requests concurrently.

### Environment Variables (Crucial!)
Your app will crash immediately if these are missing. In the Render Dashboard, go to the **Environment** tab and add:

| Key | Value |
| :--- | :--- |
| `SUPABASE_URL` | *(Copy from your local .env file)* |
| `SUPABASE_ANON_KEY` | *(Copy from your local .env file)* |
| `SECRET_KEY` | *(Generate a random string or copy from local .env)* |

## 4. Troubleshooting Common Errors

*   **"Worker failed to boot"**: Usually means a syntax error in `app.py` or missing dependency. Check the *Logs* tab.
*   **"Timeout"**: The free tier on Render spins down after 15 minutes of inactivity. The first request might take 50 seconds to wake it up. This is normal for the free tier.
*   **WebSocket Disconnects**: If you see frequent disconnects, ensure you are using `--worker-class gthread`. Standard sync workers will block the heartbeat signals.

## Summary
Use **Render**. Use the `Procfile` or the manual command `gunicorn --worker-class gthread --workers 1 --threads 8 app:app`. Don't forget the Environment Variables!
