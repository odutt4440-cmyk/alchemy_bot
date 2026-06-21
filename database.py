from motor.motor_asyncio import AsyncIOMotorClient
import datetime

client = AsyncIOMotorClient("YOUR_MONGO_URI")
db = client.alchemy_game

async def can_craft(user_id):
    user = await db.users.find_one({"user_id": user_id})
    if not user: return True
    
    # 5 second ka cooldown (Anti-Cheat)
    last_time = user.get("last_craft_time", datetime.datetime.min)
    if (datetime.datetime.now() - last_time).seconds < 5:
        return False
    return True

async def add_craft_point(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"points": 1, "crafted_count": 1}, 
         "$set": {"last_craft_time": datetime.datetime.now()}},
        upsert=True
    )
