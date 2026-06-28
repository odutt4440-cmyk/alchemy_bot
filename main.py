import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events, types
from telethon.tl.functions.bots import SetBotCommandsRequest
from database import can_craft, add_craft_point, db, get_recipe  # ✅ get_item_name hata diya

load_dotenv()

client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

async def set_commands():
    commands = [
        types.BotCommand("start", "Introduction to the bot"),
        types.BotCommand("craft", "Start crafting (Ex: /craft Fire Water)"),
        types.BotCommand("points", "Check your current points"),
        types.BotCommand("inventory", "View your discovered elements")
    ]
    await client(SetBotCommandsRequest(
        scope=types.BotCommandScopeDefault(),
        lang_code='',
        commands=commands
    ))

@client.on(events.NewMessage(pattern=r'(?i)/start'))
async def start_handler(event):
    msg = (
        "**🧪 Infinite Alchemy Bot**\n\n"
        "You start with 4 basic items: Fire 🔥, Water 💦, Earth 🌏, and Wind 💨.\n"
        "Combine them to discover new elements!\n\n"
        "**How to craft:**\n"
        "Use `/craft [Item1] [Item2]` or `/c [Item1] [Item2]`"
    )
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'(?i)/points'))
async def points_handler(event):
    user = await db.users.find_one({"user_id": event.sender_id})
    points = user.get("points", 0) if user else 0
    crafted = user.get("crafted_count", 0) if user else 0
    await event.reply(f"📊 **Your Stats**\n\n💎 Points: {points}\n🧪 Total Crafts: {crafted}")

@client.on(events.NewMessage(pattern=r'(?i)/inventory'))
async def inventory_handler(event):
    user_id = event.sender_id
    user = await db.users.find_one({"user_id": user_id})
    
    if not user or "inventory" not in user or not user["inventory"]:
        initial = ["Fire 🔥", "Water 💦", "Earth 🌏", "Wind 💨"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"inventory": initial, "points": 0, "crafted_count": 0}},
            upsert=True
        )
        items = initial
    else:
        items = user.get("inventory", [])
    
    display_items = ", ".join(items)
    await event.reply(f"🎒 **Your Collection ({len(items)} items):**\n\n{display_items}")

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s+(.*)'))
async def craft_handler(event):
    text = event.pattern_match.group(2)
    args = text.split()
    
    if len(args) < 2:
        await event.reply("⚠️ **Format:** `/craft [Item1] [Item2]`")
        return
    
    item1_input, item2_input = args[0].capitalize(), args[1].capitalize()
    
    if not await can_craft(event.sender_id):
        await event.reply("⚠️ **Slow down!** Please wait 5 seconds.")
        return

    user = await db.users.find_one({"user_id": event.sender_id})
    inventory = user.get("inventory", []) if user else []
    
    def find_item_in_inv(name, inv):
        for item in inv:
            if name.lower() in item.lower():
                return item 
        return None

    actual_item1 = find_item_in_inv(item1_input, inventory)
    actual_item2 = find_item_in_inv(item2_input, inventory)
    
    if not actual_item1 or not actual_item2:
        missing = item1_input if not actual_item1 else item2_input
        await event.reply(f"❌ You don't have **{missing}**! Check your /inventory.")
        return

    recipe = await get_recipe(item1_input, item2_input)
    
    if recipe:
        result_name_emoji = recipe['result']
        result_emoji = recipe.get('emoji', '🧪')
        
        if any(result_name_emoji.split(' ')[0].lower() in item.lower() for item in inventory):
            await event.reply(f"♻️ You have already crafted **{result_name_emoji}**!")
            return
            
        await add_craft_point(event.sender_id, new_item_name=result_name_emoji, new_item_emoji=result_emoji, points=2)
        await event.reply(f"✨ **Crafted:** {result_name_emoji} 🧪\nTotal Points: +2")
    else:
        await event.reply("❌ This combination created nothing.")

async def main():
    await client.start(bot_token=os.getenv('BOT_TOKEN'))
    await set_commands()
    print("Bot is running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
    
