# JOMGather

An intergenerational connection platform connecting youth and seniors in Singapore.

## Tech Stack

- **Python Flask** - Web framework
- **Jinja2** - HTML templating
- **SQLite** - Database
- **Bootstrap 5** - CSS framework

## Team Members

- Cassius - Home page, Slice of Life
- Brandon - Activity page, AskAGrandfriend, BOOMERang
- Zongrong - Profile Management, Supports Swap
- Deon - Login page, Social tab (Communities), Jukebox
- Akil - Social tab (Inbox), Cyber Challenge, Rewards page

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Cassius-stack/JOMGather.git
cd JOMGather
```

2. Create a virtual environment (recommended):
```bash
py -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
py app.py
```

5. Open your browser and go to: `http://127.0.0.1:5000`

## Project Structure

```
JOMGather/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── static/             # CSS, JS, images
├── templates/          # HTML templates
├── models/             # Python classes
├── routes/             # Flask blueprints
├── database/           # SQLite database
└── utils/              # Helper functions
```

## Features
- **Slice of Life**: Collaborative storytelling
- **AskAGrandfriend**: Forums for Youth and Senior
- **BOOMERang**: Meet new elderlies and youths
- **Cyber Challenge**: Defending against scams daily
- **Support Swap**: Learn and exchange skills
- **Jukebox**: Explore both generations' music

- **Rewards**: Redeem coins earnt for vouchers and items
- **Messaging**: Direct messaging with elderlies and youths
- **Communities**: Group management for interest groups
- **Profiles**: Customise your profile

## License

This project is created for educational purposes as part of IT1225 Web Development Project.g