import os
import asyncio
from telethon import TelegramClient, events, types, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from database import can_craft, add_craft_point, db, get_recipe
from config import (
    API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME,
    OFFICIAL_GC_ID,
    DEV_URL, HELP_URL, GC_URL, CHANNEL_URL,
    CRAFT_POINTS, INITIAL_ITEMS,
    START_IMAGE,
    START_MSG_DM, START_MSG_OFFICIAL_GC, START_MSG_OTHER_GROUP,
    OFFICIAL_WELCOME_MSG, OTHER_GROUP_MSG,
    CRAFT_EMPTY_MSG, CRAFT_FORMAT_MSG, SLOW_DOWN_MSG, DM_FIRST_MSG,
    POINTS_GROUP_MSG, INVENTORY_GROUP_MSG, NOTHING_MSG, HELP_MSG
)

client = TelegramClient('alchemy_bot', API_ID, API_HASH)

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
    """Handle when bot is added to a group - fixed double welcome"""
    try:
        # Sirf user_added event handle karo (user_join exist nahi karta)
        if event.user_added:
            me = await client.get_me()
            bot_added = False
            
            for user in event.users:
                if hasattr(user, 'id') and user.id == me.id:
                    bot_added = True
                    break
            
            if bot_added:
                # Bot add hua hai
                chat_id = event.chat_id
                file_path = START_IMAGE
                has_photo = os.path.exists(file_path)
                
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
    
    except Exception as e:
        print(f"Welcome handler error: {e}")

@client.on(events.NewMessage(pattern=r'(?i)/start'))
async def start_handler(event):
    if event.is_group:
        if event.chat_id == OFFICIAL_GC_ID:
            await event.reply(START_MSG_OFFICIAL_GC)
        else:
            await event.reply(START_MSG_OTHER_GROUP)
        return
    
    # ✅ DM mein /start — user ko initialize karo agar pehli baar hai
    user = await db.users.find_one({"user_id": event.sender_id})
    if not user:
        await db.users.insert_one({
            "user_id": event.sender_id,
            "points": 0,
            "crafted_count": 0,
            "last_craft_time": None,
            "inventory": INITIAL_ITEMS
        })
        print(f"✅ New user initialized: {event.sender_id}")
    
    # DM mein — photo + buttons
    buttons = [
        [Button.url("👨‍💻 Developer", DEV_URL)],
        [Button.url("❓ Help", HELP_URL),
         Button.url("💬 Official GC", GC_URL)],
        [Button.url("📢 Official Channel", CHANNEL_URL)]
    ]
    
    file_path = START_IMAGE
    if os.path.exists(file_path):
        await client.send_file(event.sender_id, file_path, caption=START_MSG_DM, buttons=buttons)
        if event.chat_id != event.sender_id:
            await event.reply("✅ Check your DM!")
    else:
        await event.reply(START_MSG_DM, buttons=buttons)

@client.on(events.NewMessage(pattern=r'(?i)/help'))
async def help_handler(event):
    await event.reply(HELP_MSG)

@client.on(events.NewMessage(pattern=r'(?i)/points'))
async def points_handler(event):
    if event.is_group:
        await event.reply(POINTS_GROUP_MSG)
        return
    user = await db.users.find_one({"user_id": event.sender_id})
    points = user.get("points", 0) if user else 0
    crafted = user.get("crafted_count", 0) if user else 0
    await event.reply(f"📊 **Your Stats**\n\n💎 Points: {points}\n🧪 Total Crafts: {crafted}")

@client.on(events.NewMessage(pattern=r'(?i)/inventory'))
async def inventory_handler(event):
    if event.is_group:
        await event.reply(INVENTORY_GROUP_MSG)
        return
    
    user_id = event.sender_id
    user = await db.users.find_one({"user_id": user_id})
    
    if not user or "inventory" not in user or not user["inventory"]:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"inventory": INITIAL_ITEMS, "points": 0, "crafted_count": 0}},
            upsert=True
        )
        items = INITIAL_ITEMS
    else:
        items = user.get("inventory", [])
    
    display_items = ", ".join(items)
    await event.reply(f"🎒 **Your Collection ({len(items)} items):**\n\n{display_items}")

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s*$'))
async def craft_empty_handler(event):
    await event.reply(CRAFT_EMPTY_MSG)

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s+(.*)'))
async def craft_handler(event):
    text = event.pattern_match.group(2)
    args = text.split()
    
    if len(args) < 2:
        await event.reply(CRAFT_FORMAT_MSG)
        return
    
    item1_input, item2_input = args[0].capitalize(), args[1].capitalize()
    
    user = await db.users.find_one({"user_id": event.sender_id})
    
    if not user:
        if event.is_group:
            await event.reply(DM_FIRST_MSG)
            return
        else:
            await db.users.insert_one({
                "user_id": event.sender_id,
                "points": 0,
                "crafted_count": 0,
                "last_craft_time": None,
                "inventory": INITIAL_ITEMS
            })
            user = await db.users.find_one({"user_id": event.sender_id})
    
    if not await can_craft(event.sender_id):
        await event.reply(SLOW_DOWN_MSG)
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
            
        await add_craft_point(event.sender_id, new_item_name=result_name_emoji, points=CRAFT_POINTS)
        await event.reply(f"✨ **Crafted:** {result_name_emoji}\nTotal Points: +{CRAFT_POINTS}")
    else:
        await event.reply(NOTHING_MSG)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    await set_commands()
    print("Bot is running!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
