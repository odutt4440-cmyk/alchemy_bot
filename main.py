import os
import asyncio
from telethon import TelegramClient, events, types, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from database import can_craft, add_craft_point, db, get_recipe
from config import (
    API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME,
    OFFICIAL_GC_ID, LOG_GC_ID,
    DEV_URL, HELP_URL, GC_URL, CHANNEL_URL,
    CRAFT_COINS,
    CRAFT_POINTS, INITIAL_ITEMS,
    START_IMAGE,
    START_MSG_DM, START_MSG_OFFICIAL_GC, START_MSG_OTHER_GROUP,
    OFFICIAL_WELCOME_MSG, OTHER_GROUP_MSG,
    CRAFT_EMPTY_MSG, CRAFT_FORMAT_MSG, SLOW_DOWN_MSG, DM_FIRST_MSG,
    POINTS_GROUP_MSG, INVENTORY_GROUP_MSG, NOTHING_MSG, HELP_MSG
)
# Admin imports
from admin import (
    MAINTENANCE, sudohelp, addsudo, power_callback, coins_cmd, 
    ban_unban, broadcast_init, bc_callback, stats, info, maintenance_mode , give_redeem
)

client = TelegramClient('alchemy_bot', API_ID, API_HASH)

# Maintenance check helper
async def check_maintenance(event):
    if MAINTENANCE.get("status"):
        await event.reply(f"⚠️ **Maintenance Notice**\n\n{MAINTENANCE.get('reason')}")
        return True
    return False

async def set_commands():
    commands = [
        types.BotCommand("start", "Introduction to the bot"),
        types.BotCommand("craft", "Start crafting (Ex: /craft Fire Water)"),
        types.BotCommand("points", "Check your current points"),
        types.BotCommand("inventory", "View your discovered elements"),
        types.BotCommand("redeem", "Redeem Rewards through this command"),
        types.BotCommand("help", "Get help and support")
    ]
    await client(SetBotCommandsRequest(
        scope=types.BotCommandScopeDefault(),
        lang_code='',
        commands=commands
    ))

@client.on(events.ChatAction)
async def welcome_handler(event):
    """Handle when bot is added to a group with logging"""
    try:
        if event.user_added:
            me = await client.get_me()
            bot_added = any(user.id == me.id for user in event.users)
            
            if bot_added:
                chat = await event.get_chat()
                await client.send_message(
                    LOG_GC_ID, 
                    f"🤖 **Bot Added to Group**\n"
                    f"Name: {chat.title}\n"
                    f"ID: `{event.chat_id}`"
                )
                
                file_path = START_IMAGE
                has_photo = os.path.exists(file_path)
                msg = OFFICIAL_WELCOME_MSG if event.chat_id == OFFICIAL_GC_ID else OTHER_GROUP_MSG
                
                if has_photo:
                    await client.send_file(event.chat_id, file_path, caption=msg)
                else:
                    await event.reply(msg)
    except Exception as e:
        print(f"Welcome handler error: {e}")

@client.on(events.NewMessage(pattern=r'(?i)/start'))
async def start_handler(event):
    if await check_maintenance(event): return
    if event.is_group:
        if event.chat_id == OFFICIAL_GC_ID:
            await event.reply(START_MSG_OFFICIAL_GC)
        else:
            await event.reply(START_MSG_OTHER_GROUP)
        return
    
    user = await db.users.find_one({"user_id": event.sender_id})
    if not user:
        await db.users.insert_one({
            "user_id": event.sender_id,
            "points": 0,
            "coins": 0,
            "crafted_count": 0,
            "last_craft_time": None,
            "inventory": INITIAL_ITEMS
        })
        sender = await event.get_sender()
        user_name = f"{sender.first_name} {sender.last_name or ''}"
        await client.send_message(
            LOG_GC_ID,
            f"👤 **New User Started Bot**\n"
            f"Name: {user_name}\n"
            f"ID: `{event.sender_id}`"
        )
    
    buttons = [
        [Button.url("👨‍💻 Developer", DEV_URL)],
        [Button.url("❓ Help", HELP_URL), Button.url("💬 Official GC", GC_URL)],
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
    if await check_maintenance(event): return
    await event.reply(HELP_MSG)

def get_progress_bar(current, target):
    percent = min(current / target, 1.0)
    filled = int(percent * 10)
    bar = "▓" * filled + "░" * (10 - filled)
    return f"[{bar}] {int(percent * 100)}%"

@client.on(events.NewMessage(pattern=r'(?i)/points'))
async def points_handler(event):
    if await check_maintenance(event): return
    if event.is_group:
        await event.reply(POINTS_GROUP_MSG)
        return
    
    user = await db.users.find_one({"user_id": event.sender_id})
    points = user.get("points", 0) if user else 0
    coins = user.get("coins", 0) if user else 0
    bar = get_progress_bar(coins, 1000)
    
    msg = (
        f"📊 **Alchemist Stats**\n\n"
        f"💎 Points: `{points}`\n"
        f"🪙 Coins: `{coins}`\n\n"
        f"🚀 **Next Reward Progress:**\n"
        f"{bar}\n\n"
        f"__Use /redeem to see available rewards!__"
    )
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'(?i)/redeem'))
async def redeem_handler(event):
    if await check_maintenance(event): return
    if event.is_group:
        return await event.reply("⚠️ **Redeem commands work only in DM!**")

    user = await db.users.find_one({"user_id": event.sender_id})
    coins = user.get("coins", 0) if user else 0

    rewards = {
        1: {"name": "10rs Playstore", "cost": 1000},
        2: {"name": "TG ID Promo", "cost": 5000},
        3: {"name": "TG Premium", "cost": 10000}
    }

    msg = f"🎁 **Rewards Store**\n\n💰 Your Coins: `{coins}`\n\n"
    btns = []
    for i, r in rewards.items():
        msg += f"{i}. {r['name']} ({r['cost']} coins)\n"
        btns.append([Button.inline(f"Redeem {r['name']}", f"red_{i}")])
    
    btns.append([Button.inline("❌ Close", "red_close")])
    await event.reply(msg, buttons=btns)

@client.on(events.CallbackQuery(data=lambda d: d.startswith(b'red_')))
async def redeem_callback(event):
    data = event.data.decode().split('_')[1]
    if data == "close":
        return await event.delete()
    
    choice = int(data)
    rewards = {
        1: {"name": "10rs Playstore Code", "cost": 1000},
        2: {"name": "Telegram ID Promotion", "cost": 5000},
        3: {"name": "Telegram Premium", "cost": 10000}
    }
    
    user = await db.users.find_one({"user_id": event.sender_id})
    coins = user.get("coins", 0) if user else 0
    target = rewards[choice]
    
    if coins < target['cost']:
        await event.answer(f"❌ Not enough coins! Need {target['cost'] - coins} more.", alert=True)
    else:
        await db.users.update_one({"user_id": event.sender_id}, {"$inc": {"coins": -target['cost']}})
        await event.edit(f"✅ **Redeem Successful!**\nYou claimed: **{target['name']}**.\nAn admin will contact you soon.")

        try:
            from config import LOG_GC_ID 
            # Button ko inline rakho
            

            await event.client.send_message(
                LOG_GC_ID, 
                f"🎁 **New Redemption Request**\n\n"
                f"👤 User ID: `{event.sender_id}`\n"
                f"💎 Item: {target['name']}\n"
                f"💰 Coins Spent: {target['cost']}",
                
            )
        except Exception as e:
            print(f"Error sending log: {e}")


@client.on(events.NewMessage(pattern=r'(?i)/inventory'))
async def inventory_handler(event):
    if await check_maintenance(event): return
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
    if await check_maintenance(event): return
    await event.reply(CRAFT_EMPTY_MSG)

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s+(.*)'))
async def craft_handler(event):
    if await check_maintenance(event): return
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
            
        await add_craft_point(
            event.sender_id, 
            new_item_name=result_name_emoji, 
            points=CRAFT_POINTS, 
            coins=CRAFT_COINS
        )
        await event.reply(f"✨ **Crafted:** {result_name_emoji}\nTotal Points: +{CRAFT_POINTS} | Coins: +{CRAFT_COINS}")
    else:
        await event.reply(NOTHING_MSG)

async def main():
    await client.start(bot_token=BOT_TOKEN)
    await set_commands()
    
    # 📢 Bot Start Notification
    try:
        from config import LOG_GC_ID
        await client.send_message(
            LOG_GC_ID, 
            "✅ **Bot has been started successfully!**\n\n"
            "🚀 Status: `Online`\n"
            "⚙️ Mode: `Production`\n"
            "📅 Time: `Online Now`"
        )
    except Exception as e:
        print(f"Could not send start message: {e}")
    
    client.add_event_handler(sudohelp)
    client.add_event_handler(addsudo)
    client.add_event_handler(power_callback)
    client.add_event_handler(coins_cmd)
    client.add_event_handler(ban_unban)
    client.add_event_handler(broadcast_init)
    client.add_event_handler(bc_callback)
    client.add_event_handler(stats)
    client.add_event_handler(info)
    client.add_event_handler(maintenance_mode)
    client.add_event_handler(give_redeem)
    
    print("Bot is running with Admin & Maintenance support!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
