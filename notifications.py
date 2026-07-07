import asyncio
from datetime import datetime, timedelta
from database import db

async def send_smart_notifications(client):
    while True:
        # Cursor ka use karke database se users fetch karo (Memory efficient)
        cursor = db.users.find({})
        now = datetime.utcnow()
        
        async for user in cursor:
            uid = user["user_id"]
            try:
                # 1. DAILY REMINDER (Sirf tabhi bhejo agar 24h ho gaye hon)
                last_daily = user.get("last_daily_time")
                if not last_daily or (now - last_daily) >= timedelta(hours=24):
                    await client.send_message(
                        uid, 
                        "⏰ **Claim your Daily Reward! /daily**\nIncrease your coins to redeem exciting gifts using /redeem."
                    )
                
                # 2. REFERRAL REMINDER (Har 6 ghante mein ye msg jayega)
                await client.send_message(
                    uid, 
                    "👥 **Earn Extra Coins!**\nRefer your friends using /refer and boost your earnings faster. Share the link now!"
                )
                
                # Chhota sa delay taaki Telegram API limit hit na ho
                await asyncio.sleep(0.5)
                
            except Exception:
                # Agar user ne bot block kiya hai toh error aayega, use skip kar do
                continue 
        
        # 6 ghante ka wait (6 * 3600 = 21600 seconds)
        await asyncio.sleep(21600)
