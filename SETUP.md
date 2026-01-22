# JOMGather Setup Guide

## Quick Start for New Developers

### 1. Clone & Pull Latest Code
```bash
git clone https://github.com/Cassius-stack/JOMGather.git
cd JOMGather
git pull origin main
```

### 2. Create Virtual Environment
```bash
# Create venv
python -m venv venv

# Activate venv
# Windows:
.\venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` File
Create a file named `.env` in the project root with:
```
SUPABASE_URL=https://bxoapzoixmqthealsryn.supabase.co
SUPABASE_ANON_KEY=sb_publishable_Phxy9luTeJWAOuKtEWGMSQ_DSGcEiX1
```

> ⚠️ **Note:** The `.env` file is gitignored - each developer needs their own copy!

### 5. Run the Application
```bash
python app.py
```

The app will be available at: http://127.0.0.1:5000

---

## Project Structure

```
JOMGather/
├── app.py                 # Main Flask application
├── routes/                # API routes & Socket.IO events
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── database/              # SQL schemas & seed scripts
├── utils/                 # Helper utilities (Supabase connection)
└── requirements.txt       # Python dependencies
```

## Database

We use **Supabase** (PostgreSQL in the cloud). The database is already set up - no additional configuration needed!

## Chat Testing

To test real-time chat with multiple users:
1. Open `http://127.0.0.1:5000/social/?user=1` (User 1 - Jeremy)
2. Open another tab: `http://127.0.0.1:5000/social/?user=2` (User 2 - Mdm Lim)
3. Send messages between them!
