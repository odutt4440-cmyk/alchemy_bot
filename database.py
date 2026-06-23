from motor.motor_asyncio import AsyncIOMotorClient
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("❌ MONGO_URI is not set in the .env file!")

client = AsyncIOMotorClient(mongo_uri)


# --- Naya: Recipe aur Items lookup function ---
async def get_recipe(item1_name, item2_name):
    # 1. Item names se IDs nikalo (case-insensitive)
    i1 = await db.items.find_one({"name": {"$regex": f"^{item1_name}$", "$options": "i"}})
    i2 = await db.items.find_one({"name": {"$regex": f"^{item2_name}$", "$options": "i"}})
    
    if not i1 or not i2:
        return None
        
    id1, id2 = i1['id'], i2['id']
    ids = sorted([id1, id2])
    
    # 2. Ab 'first' aur 'second' fields use karo (Screenshot ke hisaab se)
    recipe = await db.recipes.find_one({
        "first": ids[0], 
        "second": ids[1]
    })
    
    return recipe # Yeh wapas karega {"first": x, "second": y, "result": z}

async def get_item_name(item_id):
    item = await db.items.find_one({"id": item_id})
    return item['name'] if item else "Unknown"

# --- Tera existing code ---
async def can_craft(user_id):
    user = await db.users.find_one({"user_id": user_id})
    if not user: return True
    
    last_time = user.get("last_craft_time")
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if last_time:
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=datetime.timezone.utc)
    else:
        last_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    
    return (now - last_time).total_seconds() >= 5

async def add_craft_point(user_id, new_item_name=None, new_item_emoji=None, points=2):
    now = datetime.datetime.now(datetime.timezone.utc)
    initial_items = ["Fire 🔥", "Water 💦", "Earth 🌏", "Air 💨"]
    
    user = await db.users.find_one({"user_id": user_id})
    
    if not user:
        await db.users.insert_one({
            "user_id": user_id,
            "points": points,
            "crafted_count": 1,
            "last_craft_time": now,
            "inventory": initial_items
        })
    else:
        update_query = {
            "$inc": {"points": points, "crafted_count": 1},
            "$set": {"last_craft_time": now}
        }
        
        if "inventory" not in user or not user["inventory"]:
            update_query.setdefault("$set", {})["inventory"] = initial_items
        
        if new_item_name and new_item_emoji:
            formatted_item = f"{new_item_name} {new_item_emoji}"
            update_query.setdefault("$addToSet", {})["inventory"] = formatted_item
            
        await db.users.update_one({"user_id": user_id}, update_query)