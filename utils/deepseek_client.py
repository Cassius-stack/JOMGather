
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

def determine_navigation_intent(query, user_context):
    """
    Uses DeepSeek to determine where the user wants to go based on their query.
    user_context should include friend names and IDs.
    """
    if not DEEPSEEK_API_KEY:
        return {"action": "message", "response": "Savvy Assist is currently offline."}

    prompt = f"""
    You are 'Savvy', a friendly AI assistant for an intergenerational social app called JOMGather.
    Your job is to determine where the user wants to go based on their natural language request.
    
    User Query: "{query}"
    
    Context:
    - Current User Friends: {json.dumps(user_context.get('friends', []))}
    - App Pages & slugs: 
        Home: /
        Activities: /activities/
        Memory Library: /slice-of-life/catalog
        Daily Memory Topic: /slice-of-life/
        Social Hub: /social/
        Communities: /social/community/
        Jukebox: /jukebox/
        Support Swap: /support-swap/
        Rewards/Coins: /rewards/
        My Profile: /profile/view/{user_context.get('user_id')}
    
    Response format: JSON ONLY.
    {{
        "action": "redirect" | "chat" | "message",
        "target": "URL or UserID or null",
        "response": "A friendly, ultra-short message like 'Sure! Taking you to Ben.'"
    }}
    
    Rules:
    1. If they ask for a friend by name (e.g., "Take me to Ben", "I want to talk to Sarah"), action is "chat" and target is their UserID from the context.
    2. If they ask for a page (e.g., "show me my memories", "let's play games", "how many coins do I have"), action is "redirect" and target is the appropriate URL.
    3. If you aren't sure or they are just chatting, action is "message" and target is null, response is a helpful question.
    """

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a specialized navigation agent for JOMGather. Respond ONLY in valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return json.loads(result['choices'][0]['message']['content'])
    except Exception as e:
        print(f"Error determining intent: {e}")
        return {"action": "message", "response": "I'm sorry, I'm having trouble finding that right now."}

if __name__ == "__main__":
    # Test
    print(generate_daily_question())
