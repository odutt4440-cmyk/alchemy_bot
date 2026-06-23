import os
import asyncio
from telethon import TelegramClient, events, types
from database import can_craft, add_craft_point, db
# alchemy_engine ko ab hum yahan nahi bulayenge, iske bajaye ek local scraper use karenge

# Configuration
client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

async def set_commands():
    commands = [
        types.BotCommand("start", "Introduction to the bot"),
        types.BotCommand("craft", "Start crafting (Ex: /craft Fire Water)"),
        types.BotCommand("points", "Check your current points"),
        types.BotCommand("inventory", "View your discovered elements")
    ]
    await client(types.bots.SetBotCommandsRequest(commands=commands))

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    msg = (
        "**🧪 Infinite Alchemy Bot**\n\n"
        "Craft anything in the universe! Earn points with every discovery.\n\n"
        "Get started: `/craft [Item1] [Item2]`"
    )
    await event.reply(msg)

@client.on(events.NewMessage(pattern='/craft (.*)'))
async def craft_handler(event):
    # Regex pattern se args extract kar rahe hain
    args = event.pattern_match.group(1).split()
    
    if len(args) < 2:
        await event.reply("⚠️ **Invalid format.** Use: `/craft [Item1] [Item2]`")
        return
    
    item1, item2 = args[0].capitalize(), args[1].capitalize()
    user_id = event.sender_id
    
    # Anti-spam check
    if not await can_craft(user_id):
        await event.reply("⚠️ **Slow down!** Please wait 5 seconds between crafts.")
        return

    # 1. DB Search
    recipe = await db.recipes.find_one({"elements": sorted([item1, item2])})
    
    if recipe:
        result = {"name": recipe["name"], "emoji": recipe["emoji"]}
    else:
        # Yahan hum scraper call karenge (Abhi ye function hum `scraper_utils.py` mein banayenge)
        await event.reply("🔍 **Searching recipe online...**")
        # result = await get_recipe_from_website(item1, item2)
        # Agar website pe nahi mila, toh fallback "Nothing"
        result = {"name": "Nothing", "emoji": "🚫"}
    
    # Points 2 kar diye
    await add_craft_point(user_id, points=2) 
    
    await event.reply(f"✨ **Crafted:** {result['name']} {result['emoji']}\nPoints: +2")

async def main():
    await client.start(bot_token=os.getenv('BOT_TOKEN'))
    await set_commands()
    print("Bot is successfully running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
