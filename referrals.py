import random
from datetime import datetime, timedelta
from database import db
from telethon import Button

# --- DAILY LOGIC ---
async def get_daily_coins():
    return random.choices([1, 2, 3, 4, 5, 10], weights=[35, 35, 20, 3, 3, 4], k=1)[0]

# --- REFERRAL LOGIC ---
# Ye function tumhare previous logic jaisa hi hai
async def process_referral(referrer_id, new_user_id):
    existing_user = await db.users.find_one({"user_id": new_user_id})
    if existing_user: return {"status": False}
    
    already_referred = await db.referrals.find_one({"referrer": referrer_id, "invited": new_user_id})
    if already_referred: return {"status": False}

    await db.referrals.insert_one({"referrer": referrer_id, "invited": new_user_id})
    referrer = await db.users.find_one_and_update(
        {"user_id": referrer_id},
        {"$inc": {"refer_count": 1}},
        return_document=True
    )
    
    if referrer.get("refer_count", 0) >= 5:
        await db.users.update_one({"user_id": referrer_id}, {"$set": {"refer_count": 0}, "$inc": {"coins": 10}})
        return {"status": True, "reward": True}
    return {"status": True, "reward": False}
