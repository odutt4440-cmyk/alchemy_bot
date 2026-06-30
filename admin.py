from telethon import events, Button
from database import db, is_admin
from config import LOG_GC_ID, OWNER_ID


@events.register(events.NewMessage(pattern=r'/maintenance (on|off)(.*)'))
async def maintenance_mode(event):
    # Admin/Owner check
    if event.sender_id != OWNER_ID and not await is_admin(event.sender_id):
        return

    mode = event.pattern_match.group(1)
    reason = event.pattern_match.group(2).strip() or "Bot is under maintenance!"
    
    # Status ko DB mein update karo (Permanent fix)
    await db.config.update_one(
        {"_id": "maintenance"}, 
        {"$set": {"status": mode == "on", "reason": reason}}, 
        upsert=True
    )
    
    if mode == "on":
        await event.reply(f"✅ Maintenance Mode ON\nReason: {reason}")
    else:
        await event.reply("✅ Maintenance Mode OFF")

@events.register(events.NewMessage(pattern=r'/sudohelp'))
async def sudohelp(event):
    if not await is_admin(event.sender_id): return
    await event.reply("👑 **Sudo Control Panel**\n\n"
                      "📢 `/broadcast [text]` - DM Broadcast\n"
                      "🚫 `/ban [reason]` - Ban replied user\n"
                      "💎 `/addcoins [amt]` - Add coins to replied user\n"
                      "📊 `/stats` - Global Stats\n"
                      "🔎 `/info [uid]` - User details")

# Fixed: Ek saath Admin/Ban toggle
@events.register(events.NewMessage(pattern=r'/(add|rem)sudo'))
async def addsudo(event):
    if not await is_admin(event.sender_id): return
    target = await event.get_reply_message()
    if not target: return await event.reply("Reply to user!")
    
    uid = target.sender_id
    u = await db.users.find_one({"user_id": uid})
    if not u: return await event.reply("User not found!")
    
    # Check already status (Validation)
    is_admin_now = u.get("is_admin", False)
    action = "add" in event.text
    if action and is_admin_now: return await event.reply("⚠️ User is already a Sudo!")
    if not action and not is_admin_now: return await event.reply("⚠️ User is not an admin!")
    
    # Apply change
    await db.users.update_one({"user_id": uid}, {"$set": {"is_admin": action}})
    
    # Original Buttons Logic
    b = "✅" if u.get("is_banned") else "❌"
    a = "✅" if action else "❌" # Updated admin status
    
    btns = [
        [Button.inline(f"{a} Admin", f"p_adm_{uid}"), Button.inline(f"{b} Ban", f"p_ban_{uid}")],
        [Button.inline("❌ Cancel", f"p_cancel_{uid}")]
    ]
    await event.reply(f"Managing: {uid}\n\nClick buttons to toggle (no need to close!):", buttons=btns)

@events.register(events.CallbackQuery(data=lambda d: d.startswith(b'p_')))
async def power_callback(event):
    if not await is_admin(event.sender_id): return
    data = event.data.decode().split('_')
    act, uid = data[1], int(data[2])
    
    if act == "cancel": return await event.delete()
    
    u = await db.users.find_one({"user_id": uid})
    if act == "adm": 
        new_val = not u.get("is_admin", False)
        await db.users.update_one({"user_id": uid}, {"$set": {"is_admin": new_val}})
    elif act == "ban": 
        new_val = not u.get("is_banned", False)
        await db.users.update_one({"user_id": uid}, {"$set": {"is_banned": new_val}})
    
    # Update buttons automatically (Original Format)
    u = await db.users.find_one({"user_id": uid})
    b = "✅" if u.get("is_banned") else "❌"
    a = "✅" if u.get("is_admin") else "❌"
    btns = [[Button.inline(f"{a} Admin", f"p_adm_{uid}"), Button.inline(f"{b} Ban", f"p_ban_{uid}")], [Button.inline("❌ Close", f"p_cancel_{uid}")]]
    await event.edit(f"Managing: {uid}", buttons=btns)

# Fixed: Coins Logic (Reply or Direct ID)
# Sahi logic:
@events.register(events.NewMessage(pattern=r'/(add|rem)coins'))
async def coins_cmd(event):
    if not await is_admin(event.sender_id): return
    args = event.text.split()
    reply = await event.get_reply_message()
    
    # Logic change: 
    # Agar reply kiya hai: /addcoins 1000 (args[1] amount hai)
    # Agar reply nahi hai: /addcoins 8699042188 1000 (args[1] ID hai, args[2] amount hai)
    
    if reply:
        amt = int(args[1])
        target_id = reply.sender_id
    else:
        target_id = int(args[1]) # Pehla number ID
        amt = int(args[2])       # Dusra number Amount
        
    val = amt if "add" in args[0] else -amt
    await db.users.update_one({"user_id": target_id}, {"$inc": {"coins": val}})
    await event.reply(f"✅ Coins updated for {target_id} by {val}!")

    # 4. Ban / Unban
@events.register(events.NewMessage(pattern=r'/(ban|unban)'))
async def ban_unban(event):
    if not await is_admin(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.reply("Reply to user!")
    is_ban = "ban" in event.pattern_match.group(0)
    reason = event.text.split(maxsplit=1)[1] if len(event.text.split()) > 1 else "No reason"
    await db.users.update_one({"user_id": reply.sender_id}, {"$set": {"is_banned": is_ban}})
    status = "Banned" if is_ban else "Unbanned"
    await event.client.send_message(LOG_GC_ID, f"🛡 **{status}**\nUser: `{reply.sender_id}`\nReason: {reason}")
    await event.client.send_message(reply.sender_id, f"⚠️ You have been {status}.\nReason: {reason}")
    await event.reply(f"User {status}!")

# 5. Broadcast (DM & GC)
@events.register(events.NewMessage(pattern=r'/broadcast'))
async def broadcast_init(event):
    if not await is_admin(event.sender_id): return
    msg = await event.get_reply_message()
    text = msg.text if msg else event.text.split(maxsplit=1)[1] if len(event.text.split()) > 1 else None
    if not text: return await event.reply("Reply to a message or provide text!")
        
    global BROADCAST_TEXT
    BROADCAST_TEXT = text
        
    btns = [
        [Button.inline("👤 DM", "bc_dm"), Button.inline("👥 GC", "bc_gc")],
        [Button.inline("🌐 BOTH", "bc_all"), Button.inline("❌ Cancel", "bc_cancel")]
    ]
    await event.reply("Select where to broadcast:", buttons=btns)

@events.register(events.CallbackQuery(data=lambda d: d.startswith(b'bc_')))
async def bc_callback(event):
    if not await is_admin(event.sender_id): return
    action = event.data.decode().split('_')[1]
        
    if action == "cancel":
        await event.edit("❌ Broadcast Cancelled!")
        return
            
    await event.edit(f"🚀 Broadcasting via {action.upper()}...")
    
    # 1. DM Broadcast (Users)
    if action in ["dm", "all"]:
        users = await db.users.find({}).to_list(length=None)
        for u in users:
            try: 
                await event.client.send_message(u['user_id'], BROADCAST_TEXT)
            except Exception: 
                continue # Agar user ne bot block kiya ho toh skip karo

    # 2. GC Broadcast (Groups)
    if action in ["gc", "all"]:
        # DB se sirf 'active' groups uthao
        active_groups = await db.groups.find({"active": True}).to_list(length=None)
        
        for g in active_groups:
            try:
                await event.client.send_message(g['id'], BROADCAST_TEXT)
            except Exception as e:
                # Agar bot group se remove ho gaya hai, toh DB mein active: False kar do
                print(f"Failed to send to {g['id']}: {e}")
                await db.groups.update_one({"id": g['id']}, {"$set": {"active": False}})
        
        # Log update
        await event.client.send_message(LOG_GC_ID, f"📢 **Broadcast Sent:**\n{BROADCAST_TEXT}")
        
    await event.edit("✅ Broadcast Completed!")
    # 6. Stats & Info
@events.register(events.NewMessage(pattern=r'/stats'))
async def stats(event):
    if not await is_admin(event.sender_id): return
    
    # Counts
    total_users = await db.users.count_documents({})
    total_gcs = await db.groups.count_documents({"active": True})
    
    # Server Health (CPU/RAM)
    import psutil
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    await event.reply(
        f"📊 **Bot System Stats**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🏢 **Active Groups:** `{total_gcs}`\n\n"
        f"🖥 **CPU Load:** `{cpu}%`\n"
        f"💾 **RAM Usage:** `{ram}%`\n"
        f"✅ **Status:** `Stable`"
    )

@events.register(events.NewMessage(pattern=r'/info'))
async def info(event):
    if not await is_admin(event.sender_id): return
    
    # ID nikalne ka solid logic
    args = event.text.split()
    reply = await event.get_reply_message()
    uid = int(args[1]) if len(args) > 1 else (reply.sender_id if reply else None)
    
    if not uid: return await event.reply("❌ Usage: `/info [uid]` or reply to user!")
    
    u = await db.users.find_one({"user_id": uid})
    if not u: return await event.reply("❌ User not found in database!")
    
    # Get basic details
    try:
        user_ent = await event.client.get_entity(uid)
        name = user_ent.first_name
        uname = f"@{user_ent.username}" if user_ent.username else "None"
    except:
        name = "Unknown"; uname = "None"
        
    await event.reply(
        f"👤 **User Profile: {uid}**\n\n"
        f"📛 **Name:** {name}\n"
        f"🎭 **Username:** {uname}\n"
        f"💎 **Coins:** `{u.get('coins', 0)}`\n"
        f"🧪 **Crafted:** `{u.get('crafted_count', 0)}`\n"
        f"🎒 **Inventory:** `{len(u.get('inventory', []))} items`\n"
        f"🛡 **Status:** `{'Banned' if u.get('is_banned') else 'Active'}`"
    )

@events.register(events.NewMessage(pattern=r'/activegc'))
async def activegc(event):
    if not await is_admin(event.sender_id): return
    
    groups = await db.groups.find({"active": True}).to_list(length=None)
    if not groups: return await event.reply("🏢 No active groups found!")
    
    msg = "🏢 **Active Groups List:**\n\n"
    for i, g in enumerate(groups, 1):
        msg += f"{i}. {g.get('title', 'Unknown')} (`{g.get('id')}`)\n"
    
    await event.reply(msg)

@events.register(events.NewMessage(pattern=r'/giveredeem'))
async def give_redeem(event):
    if not await is_admin(event.sender_id): 
        return
    args = event.text.split(maxsplit=2)
    if len(args) < 3: 
        return await event.reply("❌ Usage: `/giveredeem [uid] [code/message]`")
    
    uid = int(args[1])
    reward_msg = args[2]
    
    try:
        await event.client.send_message(uid, f"🎁 **Your Reward is here!**\n\n{reward_msg}")
        await event.reply(f"✅ Reward sent to `{uid}` successfully!")
    except Exception as e:
        await event.reply(f"❌ Failed to send: {e}")

# admin.py
@events.register(events.NewMessage(pattern=r'/inspect\s+(\d+)'))
async def inspect_user(event):
    if not await is_admin(event.sender_id): return
    target_id = int(event.pattern_match.group(1))
    
    history = await db.craft_history.find({"user_id": target_id}).sort("crafted_at", -1).limit(5).to_list(None)
    if not history: return await event.reply("No history.")
    
    intervals = [(history[i]['crafted_at'] - history[i+1]['crafted_at']).total_seconds() for i in range(len(history)-1)]
    avg = sum(intervals)/len(intervals) if intervals else 0
    
    status = "✅ NORMAL"
    if avg < 2.5: # 2.5s se kam ka avg suspicious hai
        status = "⚠️ SUSPICIOUS - BOT LIKELY"
        # Log to GC
        await client.send_message(LOG_GC_ID, f"🚨 **Suspicious Activity Alert**\nUser: `{target_id}`\nAvg Interval: `{avg:.2f}s`\nStatus: {status}")
        
    await event.reply(f"🔍 Inspection for {target_id}\nAvg Speed: `{avg:.2f}s`\nResult: {status}")
