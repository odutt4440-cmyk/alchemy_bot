from openai import OpenAI
import os
from database import db

# Groq ka configuration
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

async def get_ai_recipe(item1, item2):
    prompt = f"Combine {item1} and {item2}. Result format: [Name] | [Emoji]. If illogical: Nothing | ❌"
    
    response = client.chat.completions.create(
        model="llama3-8b-8192", # Groq ka sabse fast model
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    result_text = response.choices[0].message.content.strip()
    try:
        name, emoji = result_text.split('|')
        data = {"name": name.strip(), "emoji": emoji.strip()}
    except:
        data = {"name": "Nothing", "emoji": "❌"}
        
    # MongoDB mein cache save karo
    await db.recipes.insert_one({"elements": sorted([item1, item2]), **data})
    return data
