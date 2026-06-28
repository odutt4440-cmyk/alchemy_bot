import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events, types, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from database import can_craft, add_craft_point, db, get_recipe

load_dotenv()

client = TelegramClient('alchemy_bot', int(os.getenv('API_ID')), os.getenv('API_HASH'))

# ⚠️ TERA OFFICIAL GROUP KA ID DAALNA HAI
OFFICIAL_GC_ID = -1001234567890  # ← YEH BADALNA HAI!

# Official group ke liye welcome
OFFICIAL_WELCOME_MSG = (
    "**🎉 Welcome to the Infinite Alchemy Community!**\n\n"
    "Thanks for joining us! Here you can:\n"
    "🧪 Share your best discoveries\n"
    "💡 Get help with combinations\n"
    "🏆 Compete with other alchemists\n"
    "🔬 Discuss strategies and recipes\n\n"
    "**Quick Start:**\n"
    "👉 Use `/craft` to combine elements\n"
    "👉 Use `/inventory` to see your collection\n"
    "👉 Use `/points` to check your score\n\n"
    "We hope you enjoy your journey! ✨"
)

# Doosre group mein add ho toh
OTHER_GROUP_MSG = (
    "**🤖 Thanks for adding me in the group!**\n\n"
    "I'm **Infinite Alchemy Bot** — I help you discover new elements by combining items!\n\n"
    "**How to use:**\n"
    "• `/craft Fire Water` — Combine two elements\n"
    "• `/c Fire Water` — Shortcut\n"
    "• `/inventory` — See your collection (DM only)\n"
    "• `/points` — Check your score (DM only)\n\n"
    "**To play, please use me in DM:** @your_bot_username\n"
    "Type `/start` there to begin your journey! ✨"
)

async def set_commands():
    commands = [
        types.BotCommand("start", "Introduction to the bot"),
        types.BotCommand("craft", "Start crafting (Ex: /craft Fire Water)"),
        types.BotCommand("points", "Check your current points"),
        types.BotCommand("inventory", "View your discovered elements"),
        types.BotCommand("help", "Get help and support")
    ]
    await client(SetBotCommandsRequest(
        scope=types.BotCommandScopeDefault(),
        lang_code='',
        commands=commands
    ))

@client.on(events.ChatAction)
async def welcome_handler(event):
    """Handle when bot is added to a group"""
    try:
        file_path = "assets/start_image.jpg"
        has_photo = os.path.exists(file_path)
        
        # Jab bot ko kisi group mein add karein
        if event.user_added or event.user_join:
            for user in event.users:
                if hasattr(user, 'id') and user.id == (await client.get_me()).id:
                    # Bot add hua hai
                    chat_id = event.chat_id
                    
                    if chat_id == OFFICIAL_GC_ID:
                        if has_photo:
                            await client.send_file(chat_id, file_path, caption=OFFICIAL_WELCOME_MSG)
                        else:
                            await event.reply(OFFICIAL_WELCOME_MSG)
                    else:
                        if has_photo:
                            await client.send_file(chat_id, file_path, caption=OTHER_GROUP_MSG)
                        else:
                            await event.reply(OTHER_GROUP_MSG)
                    
                    return
        
        # Jab koi member join kare
        if event.user_join:
            for user in event.users:
                if hasattr(user, 'id') and user.id == (await client.get_me()).id:
                    continue
                
                if event.chat_id == OFFICIAL_GC_ID:
                    if has_photo:
                        await client.send_file(event.chat_id, file_path, caption=OFFICIAL_WELCOME_MSG)
                    else:
                        await event.reply(OFFICIAL_WELCOME_MSG)
    
    except Exception as e:
        print(f"Welcome handler error: {e}")

@client.on(events.NewMessage(pattern=r'(?i)/start'))
async def start_handler(event):
    if event.is_group:
        if event.chat_id == OFFICIAL_GC_ID:
            await event.reply(
                "**🧪 Welcome to Official GC!**\n\n"
                "Use `/craft [Item1] [Item2]` to combine elements!\n"
                "Use `/help` for more info."
            )
        else:
            await event.reply(
                "**🧪 Infinite Alchemy Bot**\n\n"
                "Use me in DM to craft elements!\n"
                "👉 @your_bot_username\n"
                "Type `/start` there."
            )
        return
    
    # DM mein — photo + buttons
    msg = (
        "**🧪 Infinite Alchemy Bot**\n\n"
        "You start with 4 basic items: Fire 🔥, Water 💦, Earth 🌏, and Wind 💨.\n"
        "Combine them to discover new elements!\n\n"
        "**How to craft:**\n"
        "Use `/craft [Item1] [Item2]` or `/c [Item1] [Item2]`"
    )
    
    buttons = [
        [Button.url("👨‍💻 Developer", "https://t.me/your_username")],
        [Button.url("❓ Help", "https://t.me/help_link"),
         Button.url("💬 Official GC", "https://t.me/your_group")],
        [Button.url("📢 Official Channel", "https://t.me/your_channel")]
    ]
    
    file_path = "assets/start_image.jpg"
    if os.path.exists(file_path):
        await client.send_file(event.sender_id, file_path, caption=msg, buttons=buttons)
        if event.chat_id != event.sender_id:
            await event.reply("✅ Check your DM!")
    else:
        await event.reply(msg, buttons=buttons)

@client.on(events.NewMessage(pattern=r'(?i)/help'))
async def help_handler(event):
    help_msg = (
        "**📖 Help & Support**\n\n"
        "**Commands:**\n"
        "`/start` - Bot introduction\n"
        "`/craft [item1] [item2]` - Combine two elements\n"
        "`/c [item1] [item2]` - Shortcut for craft\n"
        "`/inventory` - View your collection\n"
        "`/points` - Check your score\n\n"
        "**Need more help?**\n"
        "Join our Official GC: @your_group\n"
        "Contact Developer: @your_username"
    )
    await event.reply(help_msg)

@client.on(events.NewMessage(pattern=r'(?i)/points'))
async def points_handler(event):
    if event.is_group:
        await event.reply("⚠️ Use `/points` in DM to check your stats!")
        return
    user = await db.users.find_one({"user_id": event.sender_id})
    points = user.get("points", 0) if user else 0
    crafted = user.get("crafted_count", 0) if user else 0
    await event.reply(f"📊 **Your Stats**\n\n💎 Points: {points}\n🧪 Total Crafts: {crafted}")

@client.on(events.NewMessage(pattern=r'(?i)/inventory'))
async def inventory_handler(event):
    if event.is_group:
        await event.reply("⚠️ Use `/inventory` in DM to see your collection!")
        return
    
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

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s*$'))
async def craft_empty_handler(event):
    await event.reply("⚠️ **Combine 2 objects to discover new elements!**\n\nExample: `/craft Fire Water`")

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s+(.*)'))
async def craft_handler(event):
    text = event.pattern_match.group(2)
    args = text.split()
    
    if len(args) < 2:
        await event.reply("⚠️ **Format:** `/craft [Item1] [Item2]`\nExample: `/craft Fire Water`")
        return
    
    item1_input, item2_input = args[0].capitalize(), args[1].capitalize()
    
    # ✅ GC mein craft karne se pehle check karo ki user ne DM mein bot start kiya hai
    user = await db.users.find_one({"user_id": event.sender_id})
    
    if not user:
        # User ne kabhi DM mein /start nahi kiya
        if event.is_group:
            await event.reply(
                "⚠️ **Please start the bot in DM first!**\n\n"
                "Click here 👉 @your_bot_username\n"
                "Type `/start` there, then come back to craft here!"
            )
            return
        else:
            # DM mein hai toh user ko initialize karo
            initial_items = ["Fire 🔥", "Water 💦", "Earth 🌏", "Wind 💨"]
            await db.users.insert_one({
                "user_id": event.sender_id,
                "points": 0,
                "crafted_count": 0,
                "last_craft_time": None,
                "inventory": initial_items
            })
            user = await db.users.find_one({"user_id": event.sender_id})
    
    if not await can_craft(event.sender_id):
        await event.reply("⚠️ **Slow down!** Please wait 5 seconds.")
        return

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
        
        if any(result_name_emoji.split(' ')[0].lower() in item.lower() for item in inventory):
            await event.reply(f"♻️ You have already crafted **{result_name_emoji}**!")
            return
            
        await add_craft_point(event.sender_id, new_item_name=result_name_emoji, points=2)
        await event.reply(f"✨ **Crafted:** {result_name_emoji}\nTotal Points: +2")
    else:
        await event.reply("❌ This combination created nothing.")

async def main():
    await client.start(bot_token=os.getenv('BOT_TOKEN'))
    await set_commands()
    print("Bot is running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
