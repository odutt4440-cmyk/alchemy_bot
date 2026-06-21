import os
import asyncio
from telethon import TelegramClient, events, types
from database import can_craft, add_craft_point, db
from alchemy_engine import get_ai_recipe

# Configuration
client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

async def set_commands():
    """Register bot commands in the Telegram menu."""
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
        "Craft anything in the universe! Earn points with every discovery and redeem them for rewards.\n\n"
        "Get started by using: `/craft [Item1] [Item2]`"
    )
    await event.reply(msg)

@client.on(events.NewMessage(pattern='/craft'))
async def craft_handler(event):
    args = event.message.message.split()[1:]
    if len(args) < 2:
        await event.reply("⚠️ **Invalid format.** Use: `/craft [Item1] [Item2]`")
        return
    
    item1, item2 = args[0].capitalize(), args[1].capitalize()
    user_id = event.sender_id
    
    # Anti-spam check
    if not await can_craft(user_id):
        await event.reply("⚠️ **Slow down!** Please wait 5 seconds between crafts.")
        return

    # DB Search (using sorted list for consistency)
    recipe = await db.recipes.find_one({"elements": sorted([item1, item2])})
    
    if recipe:
        result = {"name": recipe["name"], "emoji": recipe["emoji"]}
    else:
        # AI Call (Groq)
        result = await get_ai_recipe(item1, item2)
    
    # Save point and update stats
    await add_craft_point(user_id)
    await event.reply(f"✨ **Crafted:** {result['name']} {result['emoji']}\nPoints: +1")

# Bot start sequence
async def main():
    await client.start(bot_token=os.getenv('BOT_TOKEN'))
    await set_commands()
    print("Bot is successfully running and commands are set!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
