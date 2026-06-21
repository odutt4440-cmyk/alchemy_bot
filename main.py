from telethon import TelegramClient, events
from database import can_craft, add_craft_point
import os

client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

@client.on(events.NewMessage(pattern='/craft'))
async def craft_handler(event):
    user_id = event.sender_id
    
    # 1. Anti-Cheat Check
    if not await can_craft(user_id):
        await event.reply("⚠️ Crafting too fast! Chill out for a few seconds.")
        return

    # 2. Logic (Crafting process...)
    # ... call alchemy_engine ...
    
    # 3. Add point
    await add_craft_point(user_id)
    await event.reply("✅ Crafted! +1 Point added.")

client.start()
client.run_until_disconnected()
