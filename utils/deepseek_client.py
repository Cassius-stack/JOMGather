
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


def generate_rag_response(query, context_list):
    """
    Generates a helpful response based on the user query and retrieved context (Q&A).
    """
    if not DEEPSEEK_API_KEY:
        # Simple Keyword RAG Fallback
        words = query.lower().split()
        keywords = [w for w in words if len(w) > 3]
        best_match = None
        max_score = 0
        
        for item in context_list:
            score = 0
            item_lower = item.lower()
            for k in keywords:
                if k in item_lower:
                    score += 1
            if score > max_score:
                max_score = score
                best_match = item
                
        if best_match and max_score > 0:
            return f"I can't connect to my AI brain, but I found this related post: ... {best_match[:300]} ..."
        
        return "I can't access my brain right now and I found no relevant posts. Please add your DEEPSEEK_API_KEY."

    context_text = "\n\n".join(context_list)
    prompt = f"""
    You are a helpful assistant for "Ask A Grandfriend", a platform connecting seniors and youth.
    Use the following community Q&A context to answer the user's question.
    If the answer isn't in the context, use your general knowledge but mention that it's not from the community yet.
    
    Context:
    {context_text}
    
    User Question: {query}
    
    Answer (keep it warm, encouraging, and concise):
    """

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a warm, intergenerational community assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error generating RAG response: {e}")
        return "I'm having trouble thinking right now. Maybe try searching the posts directly?"

def generate_starter_prompts(recent_items=[]):
    """
    Generates 3 short, clickable starter questions based on recent topics.
    Input: List of dicts {'category': str, 'title': str, 'content': str}
    """
    # 1. Local Fallback (Smart Construction)
    if not DEEPSEEK_API_KEY:
        local_prompts = []
        import random
        
        # Filter items with content
        valid_items = [i for i in recent_items if i.get('title')]
        
        if valid_items:
            # Strategy A: Ask about a specific title
            item = random.choice(valid_items)
            local_prompts.append(f"More about '{item['title']}'?")
            
            # Strategy B: Ask about a category
            cats = list(set(i['category'] for i in valid_items if i.get('category')))
            if cats:
                cat = random.choice(cats)
                local_prompts.append(f"Advice on {cat}?")
                
            # Strategy C: General
            local_prompts.append("How can I help today?")
        else:
             local_prompts = ["How do I make friends?", "Best advice for school?", "Stories from the 60s?"]
             
        return local_prompts[:3]

    # 2. AI Generation
    # Summarize items for prompt
    context_str = ""
    for i in recent_items[:5]:
        context_str += f"- [{i.get('category')}] {i.get('title')}: {i.get('content')[:50]}...\n"

    prompt = f"""
    Generate 3 short, catchy user questions (max 6 words) based on these recent posts:
    {context_str}
    Return ONLY a JSON array of strings.
    """

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        # Clean up code blocks if present
        if content.startswith('```'):
            content = content.replace('```json', '').replace('```', '')
        return json.loads(content)
    except Exception as e:
        print(f"Error generating prompts: {e}")
        return ["Life advice?", "Favorite memory?", "School tips?"]

if __name__ == "__main__":
    # Test
    print(generate_daily_question())

