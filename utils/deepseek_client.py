
import os
import requests
import json
from datetime import datetime

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions" # Adjust if necessary

def generate_daily_question(previous_questions=[]):
    """
    Generates a unique, engaging intergenerational question using DeepSeek API.
    """
    if not DEEPSEEK_API_KEY:
        print("Warning: DEEPSEEK_API_KEY not found.")
        return "What is a fond memory from your childhood?"

    prompt = f"""
    Generate a single, engaging daily question for an app connecting seniors and youth.
    The question should be open-ended, encourage storytelling, and relate to 'Slice of Life' memories.
    Examples: "What was your favorite toy growing up?", "Describe a meal that tastes like home."
    Do not repeat these examples.
    
    Previous questions to avoid: {', '.join(previous_questions)}
    
    Return ONLY the question text.
    """

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat", # Or deepseek-coder, check docs
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for an intergenerational social app."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        question = result['choices'][0]['message']['content'].strip().strip('"')
        return question
    except Exception as e:
        print(f"Error generating question from DeepSeek: {e}")
        return "What is a simple joy you experienced recently?"

def generate_memory_title(thoughts_list):
    """
    Summarizes two user thoughts into a poetic, short title for a shared memory.
    """
    if not DEEPSEEK_API_KEY:
        return "A Shared Memory"

    combined_text = " | ".join(thoughts_list)
    prompt = f"Summarize these two perspectives into a short (3-6 words), poetic title for a shared memory. Perspectives: '{combined_text}'. Return ONLY the title."

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a poetic storyteller for an intergenerational app."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        title = result['choices'][0]['message']['content'].strip().strip('"')
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        return "A Moment Shared"

if __name__ == "__main__":
    # Test
    print(generate_daily_question())
