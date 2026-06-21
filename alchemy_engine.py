import google.generativeai as genai
import os
from database import db

# API Key setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

async def get_ai_recipe(item1, item2):
    # Prompting for standard format
    prompt = f"Combine {item1} and {item2}. Give me the result in format: [Name] | [Emoji]. If illogical, return: Nothing | ❌"
    
    response = model.generate_content(prompt)
    result_text = response.text.strip()
    
    # Clean output
    try:
        name, emoji = result_text.split('|')
        name = name.strip()
        emoji = emoji.strip()
    except:
        name, emoji = "Nothing", "❌"
        
    # Save to MongoDB for future caching
    await db.recipes.insert_one({
        "elements": sorted([item1, item2]),
        "result": name,
        "emoji": emoji
    })
    
    return {"name": name, "emoji": emoji}
