from telethon import TelegramClient, events
from database import can_craft, add_craft_point, db
from alchemy_engine import get_ai_recipe
import os

client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

@client.on(events.NewMessage(pattern='/craft'))
async def craft_handler(event):
    # Regex se items nikalo (e.g., /craft Fire Water)
    args = event.message.message.split()[1:]
    if len(args) < 2:
        await event.reply("Usage: /craft [Item1] [Item2]")
        return
    
    item1, item2 = args[0], args[1]
    user_id = event.sender_id
    
    if not await can_craft(user_id):
        await event.reply("⚠️ Too fast! Wait 5 seconds.")
        return

    # 1. DB Search
    recipe = await db.recipes.find_one({"elements": sorted([item1, item2])})
    
    if recipe:
        result = {"name": recipe["name"], "emoji": recipe["emoji"]}
    else:
        # 2. AI Call (Groq)
        result = await get_ai_recipe(item1, item2)
    
    # 3. Add point & reply
    await add_craft_point(user_id)
    await event.reply(f"✨ Crafted: {result['name']} {result['emoji']}\nPoints: +1")

client.start(bot_token=os.getenv('BOT_TOKEN'))
client.run_until_disconnected()
