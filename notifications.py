import asyncio
from datetime import datetime, timedelta
from database import db

async def send_smart_notifications(client):
    while True:
        users = await db.users.find().to_list(length=None)
        now = datetime.utcnow()
        
        for user in users:
            uid = user["user_id"]
            try:
                # 1. DAILY REMINDER (Check if 24h passed)
                last_daily = user.get("last_daily_time")
                if not last_daily or (now - last_daily) >= timedelta(hours=24):
                    await client.send_message(uid, "⏰ **Claim your Daily Reward!**\nIncrease your coins to redeem exciting gifts using /redeem.")
                
                # 2. REFERRAL REMINDER (Har 2 ghante mein)
                # Note: Har 2 ghante mein notification bhejna thoda spammy ho sakta hai, 
                # ensure karna ki users block na karein!
                await client.send_message(uid, "👥 **Earn Extra Coins!**\nRefer your friends using /refer and boost your earnings faster. Share the link now!")
                
            except Exception:
                continue # Agar user ne bot block kiya ho
        
        # 2 ghante ka wait (scheduler loop)
        await asyncio.sleep(7200)
