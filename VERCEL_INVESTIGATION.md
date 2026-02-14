# Vercel Suitability Investigation Report

## Project Overview
**Application:** JOMGather (Python Flask)
**Key Dependencies:** `Flask-SocketIO`, `Supabase`, `opencv-python` (implied for camera features), `pyngrok` (tunneling).
**Architecture:** Monolithic Flask application with blueprints, relying heavily on persistent WebSocket connections for real-time features.

## Findings

After a thorough review of the codebase, I have determined that **JOMGather is NOT suitable for hosting on Vercel without significant code changes.**

### Critical Incompatibilities

1.  **WebSockets (Flask-SocketIO):**
    *   **Issue:** The application relies extensively on `Flask-SocketIO` for chat, video call signaling, notifications, and the "Cyber Challenge" feature (`routes/chat_events.py`, `routes/boomerang_events.py`).
    *   **Vercel Limitation:** Vercel Serverless Functions are short-lived, stateless HTTP handlers. They terminate immediately after sending a response and cannot maintain the long-lived, persistent WebSocket connections required by `Flask-SocketIO`. Any attempt to connect via WebSocket will fail or be immediately terminated.
    *   **Impact:** Real-time chat, video calling, and notifications will be completely non-functional.

2.  **File System (Local Uploads):**
    *   **Issue:** The application saves uploaded images and audio files directly to the local filesystem (`static/uploads/chat` and `static/uploads/audio`) in `routes/social.py`.
    *   **Vercel Limitation:** Vercel's filesystem is ephemeral and mostly read-only. Any file written to the disk during a function execution will disappear immediately after the function completes.
    *   **Impact:** Users will be unable to share images or voice messages. Uploaded files will vanish instantly.

3.  **Execution Model (Blocking Processes):**
    *   **Issue:** The application entry point (`app.py`) uses `socketio.run(app, ...)` which is a blocking call designed for a long-running server process.
    *   **Vercel Limitation:** Vercel expects a WSGI callable to be exposed for serverless invocation. While Flask can be adapted, the blocking nature of `socketio.run` and the reliance on background threads (`async_mode='threading'`) are incompatible with the serverless model where execution is paused/killed between requests.

## Recommendation

For a student presentation where **"no code changes"** is a requirement, you should host this application on a Platform-as-a-Service (PaaS) that supports persistent, long-running processes.

**Suitable Alternatives:**

1.  **Render (Web Service):**
    *   Supports persistent processes (ideal for `socketio.run`).
    *   Has a free tier.
    *   *Note:* The free tier on Render also has an ephemeral filesystem, so uploaded files will still be lost if the service restarts (which happens frequently on free tier). Ideally, you should switch to cloud storage (e.g., Supabase Storage) for uploads, but since "no code changes" is strict, Render is still better than Vercel because the WebSockets will work while the instance is running.

2.  **Railway:**
    *   Similar to Render, supports persistent processes and Docker containers.
    *   Better performance but may require a small paid plan (trial credits available).

3.  **PythonAnywhere:**
    *   Designed specifically for Python/Flask.
    *   Supports persistent files (good for local uploads!).
    *   *Limitation:* WebSockets might not work well on the free tier, but it solves the file storage issue better than Render free tier.

**Conclusion:** Do not deploy to Vercel. Use **PythonAnywhere** (for file persistence) or **Render** (for WebSockets) depending on which feature is more critical for your presentation, or use a paid VPS (DigitalOcean/AWS) for full compatibility.
