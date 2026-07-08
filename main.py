import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, types, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from database import can_craft, add_craft_point, db, get_recipe
from notifications import send_smart_notifications
from referrals import process_referral, get_daily_coins
from leaderboard import get_lb_markup, fetch_leaderboard_data
from config import (
    API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME,
    OFFICIAL_GC_ID, LOG_GC_ID, OWNER_ID,
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
    is_admin, sudohelp, addsudo, power_callback, coins_cmd, 
    ban_unban, broadcast_init, bc_callback, stats, info, maintenance_mode , give_redeem, inspect_user, send_captcha, inspection_mode
)

client = TelegramClient('alchemy_bot', API_ID, API_HASH)
ITEMS_PER_PAGE = 100
# Maintenance check helper
# main.py mein ye function replace kar do
async def check_maintenance(event):
    # DB se status lao
    m_data = await db.config.find_one({"_id": "maintenance"})
    is_m = m_data.get("status", False) if m_data else False
    
    if is_m:
        # Owner/Admin bypass
        if event.sender_id == OWNER_ID or await is_admin(event.sender_id):
            return False
            
        reason = m_data.get("reason", "Bot is under maintenance!")
        await event.reply(f"⚠️ **Maintenance Notice**\n\n{reason}")
        return True
    return False

async def set_commands():
    commands = [
        types.BotCommand("start", "Introduction to the bot"),
        types.BotCommand("craft", "Start crafting (Ex: /craft Fire Water)"),
        types.BotCommand("points", "Check your current points"),
        types.BotCommand("inventory", "View your discovered elements"),
        types.BotCommand("leaderboard", "Check global/chat leaderboard"),
        types.BotCommand("daily", "Claim your daily rewards"),  
        types.BotCommand("refer", "Get your referral link"),
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
    try:
        # Sirf groups ke liye
        if not event.is_group: return
        
        me = await client.get_me()
        
        # 1. Bot add/join logic
        if event.user_added or event.user_joined:
            # Check karo kya bot add hua hai
            if any(u.id == me.id for u in event.users):
                
                chat = await event.get_chat()
                
                # DB Update
                await db.groups.update_one(
                    {"id": event.chat_id}, 
                    {"$set": {"active": True, "title": chat.title}}, 
                    upsert=True
                )

                # Log to LOG_GC
                # event.action_message.sender_id ye sabse safe way hai sender nikalne ka
                sender_id = event.action_message.sender_id if event.action_message else "Unknown"
                
                chat_link = f"https://t.me/c/{str(event.chat_id).replace('-100', '')}" if event.chat_id < 0 else "N/A"

                await client.send_message(
                    LOG_GC_ID, 
                    f"🤖 **Bot Added to Group**\n\n"
                    f"🏢 **Group:** {chat.title}\n"
                    f"🆔 **GC ID:** `{event.chat_id}`\n"
                    f"🔗 **Link:** {chat_link}\n"
                    f"👤 **Added By ID:** `{sender_id}`"
                )
                
                # Welcome Message
                msg = OFFICIAL_WELCOME_MSG if int(event.chat_id) == int(OFFICIAL_GC_ID) else OTHER_GROUP_MSG
                if os.path.exists(START_IMAGE):
                    await client.send_file(event.chat_id, START_IMAGE, caption=msg)
                else:
                    await client.send_message(event.chat_id, msg)
                return

            if int(event.chat_id) == int(OFFICIAL_GC_ID):
                for user in event.users:
                    # Sirf Official GC mein welcome message
                    if os.path.exists(START_IMAGE):
                        await client.send_file(event.chat_id, START_IMAGE, caption=OFFICIAL_WELCOME_MSG)
                    else:
                        await client.send_message(event.chat_id, OFFICIAL_WELCOME_MSG)

        # 2. Left/Kick logic
        elif event.user_kicked or event.user_left:
            if any(u.id == me.id for u in event.users):
                await db.groups.update_one({"id": event.chat_id}, {"$set": {"active": False}})

    except Exception as e:
        # Error print karo taaki hume pata chale exact line kya hai
        import traceback
        traceback.print_exc()
        print(f"Welcome handler error: {e}")

@client.on(events.NewMessage)
async def group_tracker(event):
    if event.is_group:
        # Har command chalne par group ko active mark kar do
        chat = await event.get_chat()
        await db.groups.update_one(
            {"id": event.chat_id}, 
            {"$set": {"id": event.chat_id, "title": chat.title, "active": True}}, 
            upsert=True
        )


@client.on(events.NewMessage(pattern=r'(?i)/start( ref_(.+))?'))
async def start_handler(event):
    if await check_maintenance(event): return
    
    # 1. HAR BAAR LOG GC ME LOG BHEJO
    sender = await event.get_sender()
    user_name = f"{sender.first_name} {sender.last_name or ''}"
    await client.send_message(
        LOG_GC_ID,
        f"👤 **Bot Started/Restarted**\nName: {user_name}\nID: `{event.sender_id}`\nIn Group: {event.is_group}"
    )

    # 2. Group Logic (Agar group mein start kiya hai)
    if event.is_group:
        if event.chat_id == OFFICIAL_GC_ID:
            await event.reply(START_MSG_OFFICIAL_GC)
        else:
            await event.reply(START_MSG_OTHER_GROUP)
        return
    
    # 3. DM Logic (Referral Processing)
    args = event.pattern_match.group(2)
    if args:
        try:
            referrer_id = int(args)
            if referrer_id != event.sender_id:
                res = await process_referral(referrer_id, event.sender_id)
                if res.get("reward"):
                    await client.send_message(referrer_id, "🎉 **5 Referrals Completed!**\n10 coins bonused to your account.")
        except:
            pass

    # 4. User registration (Agar naya user hai)
    user = await db.users.find_one({"user_id": event.sender_id})
    if not user:
        await db.users.insert_one({
            "user_id": event.sender_id,
            "points": 0,
            "coins": 0,
            "crafted_count": 0,
            "last_craft_time": None,
            "refer_count": 0, # Refer tracker
            "inventory": INITIAL_ITEMS
        })
    
    # 5. Welcome Buttons
    buttons = [
        [Button.url("👨‍💻 Developer", DEV_URL)],
        [Button.url("❓ Help", HELP_URL), Button.url("💬 Official GC", GC_URL)],
        [Button.url("📢 Official Channel", CHANNEL_URL)]
    ]
    
    file_path = START_IMAGE
    if os.path.exists(file_path):
        await client.send_file(event.sender_id, file_path, caption=START_MSG_DM, buttons=buttons)
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


@client.on(events.NewMessage(pattern=r'(?i)/(inventory|inv)(\s+(.*))?'))
async def inventory_handler(event):
    user_id = event.sender_id
    # Letter catch karo
    query = event.pattern_match.group(3)
    
    user = await db.users.find_one({"user_id": user_id})
    full_inv = user.get("inventory", []) if user else []
    
    if query:
        # Letter filter logic
        filtered = [item for item in full_inv if item.lower().startswith(query.lower())]
        if not filtered:
            await event.reply(f"❌ No inventory found starting with letter '{query}'.")
            return
        await send_filtered_inventory(event, user_id, 0, len(filtered), filtered, query)
    else:
        # Default behavior (jo tumhara pehle tha)
        await send_inventory_page(event, user_id, 0, len(full_inv))

async def send_inventory_page(event, owner_id, page, total_count):
    user_data = await db.users.find_one(
        {"user_id": owner_id},
        {"inventory": {"$slice": [page * ITEMS_PER_PAGE, ITEMS_PER_PAGE]}}
    )
    items = user_data.get("inventory", []) if user_data else []
    display_text = ", ".join(items) if items else "No items found!"
    
    # FIX: Total pages ka logic safe banao
    total_pages = max(1, (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE) if total_count > 0 else 1
    current_page = page + 1
    
    text = (f"🎒 **Your Collection ({total_count} items):**\n"
            f"📄 Page {current_page} / {total_pages}\n\n"
            f"{display_text}")
    
    # Buttons logic
    buttons = None
    row = []
    if page > 0:
        row.append(Button.inline("◀️ Prev", data=f"inv_{owner_id}_{page-1}"))
    if (page + 1) * ITEMS_PER_PAGE < total_count:
        row.append(Button.inline("Next ▶️", data=f"inv_{owner_id}_{page+1}"))
    
    if row:
        buttons = [row]

    if isinstance(event, events.NewMessage.Event):
        await event.reply(text, buttons=buttons)
    else:
        await event.edit(text, buttons=buttons)

# Filtered page ke liye naya function
async def send_filtered_inventory(event, owner_id, page, total_count, items, letter):
    start = page * ITEMS_PER_PAGE
    display_items = items[start : start + ITEMS_PER_PAGE]
    display_text = ", ".join(display_items) if display_items else "No items found!"
    
    # FIX: Yahan bhi same safe logic
    total_pages = max(1, (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE) if total_count > 0 else 1
    
    text = (f"🎒 **Collection ('{letter}'):** ({total_count} items)\n"
            f"📄 Page {page + 1} / {total_pages}\n\n"
            f"{display_text}")
    
    buttons = None
    row = []
    if page > 0:
        row.append(Button.inline("◀️ Prev", data=f"invf_{owner_id}_{page-1}_{letter}"))
    if (page + 1) * ITEMS_PER_PAGE < total_count:
        row.append(Button.inline("Next ▶️", data=f"invf_{owner_id}_{page+1}_{letter}"))
    
    if row:
        buttons = [row]
    
    if isinstance(event, events.NewMessage.Event):
        await event.reply(text, buttons=buttons)
    else:
        await event.edit(text, buttons=buttons)

@client.on(events.CallbackQuery(pattern=b"inv"))
async def callback_handler(event):
    data = event.data.decode().split("_")
    is_filtered = data[0] == "invf"
    owner_id = int(data[1])
    target_page = int(data[2])
    
    if event.sender_id != owner_id:
        await event.answer("🚫 This is not your inventory, stay away!", alert=True)
        return
    
    user = await db.users.find_one({"user_id": owner_id})
    full_inv = user.get("inventory", []) if user else []
    
    if is_filtered:
        # Agar letter limit se zyada hai, toh yahan error aa sakta hai.
        # Lekin 'a', 'b', 'c' ke liye ye 100% safe hai.
        letter = "_".join(data[3:]) # Agar letter mein underscore ho toh handle karega
        filtered = [item for item in full_inv if item.lower().startswith(letter.lower())]
        await send_filtered_inventory(event, owner_id, target_page, len(filtered), filtered, letter)
    else:
        await send_inventory_page(event, owner_id, target_page, len(full_inv))



@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s*$'))
async def craft_empty_handler(event):
    if await check_maintenance(event): return
    await event.reply(CRAFT_EMPTY_MSG)

@client.on(events.NewMessage(pattern=r'(?i)/(craft|c)\s+(.*)'))
async def craft_handler(event):
    if await check_maintenance(event): return

    # 1. Inspection & Captcha Check
    if inspection_mode.get(event.sender_id, False):
        user = await db.users.find_one({"user_id": event.sender_id})
        last_time = user.get("last_craft_time")
        import datetime
        if last_time and (datetime.datetime.now() - last_time).total_seconds() < 1.8:
            await client.send_message(LOG_GC_ID, f"🕵️ **Forensic Alert:** User `{event.sender_id}` is under inspection.")

    user = await db.users.find_one({"user_id": event.sender_id})
    if user and user.get("is_verifying"):
        await client.send_message(LOG_GC_ID, f"🚨 **Busted!** User `{event.sender_id}` using script.")
        await event.reply("🚫 **Access Blocked!** Admin has sent a verification captcha to your DM.")
        return

    raw_text = event.pattern_match.group(2).strip()
    uid = event.sender_id
    
    if not user:
        if event.is_group:
            await event.reply(DM_FIRST_MSG)
            return
        await db.users.insert_one({"user_id": event.sender_id, "points": 0, "inventory": INITIAL_ITEMS})
        user = await db.users.find_one({"user_id": event.sender_id})

    if not await can_craft(event.sender_id):
        await event.reply(SLOW_DOWN_MSG)
        return

    inventory = user.get("inventory", [])
    
    # --- BULLETPROOF MATCHING ---
    import re
    def get_clean_name(name):
        # Sabse pehle underscore hatao, phir non-alphanumeric chars (emojis) hatao
        name = name.replace("_", " ")
        return re.sub(r'[^\w\s]', '', name).strip().lower()

    def match_item(input_str, inv):
        search = get_clean_name(input_str)
        
        # 1. First Pass: Exact Match (Jo tumhara abhi ka logic hai)
        for item in inv:
            if search == get_clean_name(item):
                return item
        
        # 2. Second Pass: Fallback for Numbers (Agar exact nahi mila, toh check karo startwith)
        # Ye sirf tab chalega agar exact match fail ho gaya, toh tumhare purane items secure hain!
        if search.isdigit(): 
            for item in inv:
                if get_clean_name(item).startswith(search + " "):
                    return item
                    
        return None

    # Splitting logic
    parts = raw_text.replace("+", " ").split()
    item1, item2 = None, None
    missing_item = None 

    for i in range(1, len(parts)):
        cand1 = match_item(" ".join(parts[:i]), inventory)
        cand2 = match_item(" ".join(parts[i:]), inventory)
        
        if cand1 and cand2:
            item1, item2 = cand1, cand2
            break
        else:
            # Agar nahi mila, toh check karo kaunsa missing hai
            # Sirf tab update karo jab humein specific pata chale
            if not cand1: missing_item = " ".join(parts[:i])
            elif not cand2: missing_item = " ".join(parts[i:])

    # Debug line (as you wanted)
    print(f"DEBUG [User: {uid}]: Input: {raw_text} | Inventory Size: {len(inventory)}")
            
    if not item1 or not item2:
        # Ek line ka compact reply
        await event.reply(f"❌ **Not in Inventory:** `{missing_item or raw_text}` is missing from your collection. 🧪")
        return

    print(f"DEBUG: Crafting: {item1} + {item2}")

    recipe = await get_recipe(item1, item2)
    
    if recipe:
        result = recipe['result']
        # Check if already exists
        if any(get_clean_name(result) == get_clean_name(i) for i in inventory):
            await event.reply(f"♻️ You have already crafted **{result}**!")
            return
            
        await add_craft_point(event.sender_id, (await event.get_sender()).first_name, result, CRAFT_POINTS, CRAFT_COINS, event.chat_id)
        await event.reply(f"✨ **Crafted:** {result}\nPoints: +{CRAFT_POINTS} | Coins: +{CRAFT_COINS}")
    else:
        await event.reply(NOTHING_MSG)
        
@client.on(events.NewMessage(pattern=r'(?i)/(lb|leaderboard)'))
async def lb_cmd(event):
    if await check_maintenance(event): return
    
    initial_mode = "global_points_today"
    data = await fetch_leaderboard_data(initial_mode, chat_id=event.chat_id if event.is_group else None)
    
    text = "🏆 **Alchemist Leaderboard (Today)**\n\n"
    for i, user in enumerate(data, 1):
        # Yahan .get('total', 0) use kiya hai taaki crash na ho
        text += f"{i}. User ID: `{user['_id']}` - {user.get('total', 0)} pts\n"
        
    btns = await get_lb_markup(initial_mode)
    await event.reply(text, buttons=btns)

@client.on(events.CallbackQuery(pattern=b"lb_|refresh_"))
async def lb_callback(event):
    data = event.data.decode()
    mode = data.replace("refresh_", "").replace("lb_", "")
    
    chat_id = event.chat_id if "chat" in mode else None
    leaderboard_data = await fetch_leaderboard_data(mode, chat_id=chat_id)
    
    parts = mode.split('_')
    # Parts: 0=scope(global/chat), 1=category(craft/points), 2=time(today/all)
    header = f"🏆 **Alchemist Leaderboard ({parts[0].upper()} — {parts[2].upper()})**"
    
    if not leaderboard_data:
        text = f"{header}\n\nNo records found yet!"
    else:
        text = f"{header}\n\n"
        for i, user in enumerate(leaderboard_data, 1):
            name = user.get("first_name", "Unknown")
            val = user.get('total', 0)
            unit = 'pts' if 'points' in mode else 'crafts'
            text += f"{i}. {name} — {val} {unit}\n"
    
    btns = await get_lb_markup(mode)
    
    try:
        await event.edit(text, buttons=btns)
    except Exception as e:
        # Check karo agar error 'MessageNotModified' hai
        if "MessageNotModified" in str(e):
            await event.answer("Nothing to update!")
        else:
            print(f"Leaderboard callback error: {e}")
            
    await event.answer("✅ Updated!")

@client.on(events.NewMessage(func=lambda e: e.is_private))
async def verify_handler(event):
    user = await db.users.find_one({"user_id": event.sender_id})
    if user and user.get("is_verifying"):
        sent_code = user.get("captcha_code")
        user_reply = event.text.strip()
        
        # Log evidence: Admin ne kya bheja aur User ne kya type kiya
        await client.send_message(LOG_GC_ID, f"📝 **Captcha Evidence**\nUser: `{event.sender_id}`\nSent Code: `{sent_code}`\nUser Replied: `{user_reply}`")
        
        if user_reply == sent_code:
            await db.users.update_one({"user_id": event.sender_id}, {"$set": {"is_verifying": False, "captcha_code": None}})
            await event.reply("✅ **Verified.** You are now cleared.")
        else:
            await event.reply("❌ **Invalid code!** Admin will be notified of this attempt.")

@client.on(events.NewMessage(pattern="/refer"))
async def refer_cmd(event):
    bot_info = await client.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{event.sender_id}"
    
    user = await db.users.find_one({"user_id": event.sender_id})
    count = user.get("refer_count", 0)
    
    msg = f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n👥 **Progress:** {count}/5\nInvite 5 users to get 10 coins!"
    await event.reply(msg, buttons=[[Button.url("Share Link", f"https://t.me/share/url?url={ref_link}")]])

@client.on(events.NewMessage(pattern="/daily"))
async def daily_cmd(event):
    user = await db.users.find_one({"user_id": event.sender_id})
    now = datetime.utcnow()
    last_daily = user.get("last_daily_time")
    
    if last_daily and (now - last_daily).total_seconds() < 86400:
        remaining = 86400 - (now - last_daily).total_seconds()
        await event.reply(f"❌ Claimed! Back in {int(remaining/3600)}h {int((remaining%3600)/60)}m")
        return

    coins = await get_daily_coins()
    await db.users.update_one({"user_id": event.sender_id}, {"$set": {"last_daily_time": now}, "$inc": {"coins": coins}})
    await event.reply(f"🎁 **Daily Gift:** You received `{coins}` coins!")


async def main():
    await client.start(bot_token=BOT_TOKEN)
    asyncio.create_task(send_smart_notifications(client))
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
    client.add_event_handler(inspect_user)
    client.add_event_handler(send_captcha)
    
    print("Bot is running with Admin & Maintenance support!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
