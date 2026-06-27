from motor.motor_asyncio import AsyncIOMotorClient
import datetime
import os
import sqlite3
import requests
import gzip
from dotenv import load_dotenv

load_dotenv()

# ===== MONGO (User data) =====
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("❌ MONGO_URI is not set in the .env file!")

mongo_client = AsyncIOMotorClient(mongo_uri)
db = mongo_client.infinite_craft

# ===== SQLITE (Game data - downloaded from GitHub) =====
SQLITE_DB_PATH = "infinite_craft.db"
BASE_URL = "https://github.com/odutt4440-cmyk/infinite-craft-scraper/raw/main"

def _download_sqlite_db():
    """Download and combine chunks from GitHub if DB doesn't exist"""
    if os.path.exists(SQLITE_DB_PATH):
        return
    
    import time
    print("📥 Downloading game database chunks...")
    chunk_num = 0
    with open("infinite_craft.db.gz", "wb") as out:
        while True:
            n = chunk_num
            letters = []
            while True:
                letters.append(chr(97 + n % 26))
                n = n // 26
                if n == 0:
                    break
            filename = "part_" + "".join(reversed(letters))
            url = f"{BASE_URL}/{filename}"
            
            resp = requests.get(url)
            if resp.status_code != 200:
                break
            
            out.write(resp.content)
            chunk_num += 1
    
    print(f"📦 Decompressing ({chunk_num} chunks)...")
    with gzip.open("infinite_craft.db.gz", "rb") as f_in:
        with open(SQLITE_DB_PATH, "wb") as f_out:
            f_out.write(f_in.read())
    
    os.remove("infinite_craft.db.gz")
    print(f"✅ Game DB ready")

def _get_sqlite_conn():
    """Get SQLite connection"""
    _download_sqlite_db()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== GAME DATA LOOKUP (SQLite) =====
async def get_recipe(item1_name, item2_name):
    try:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT result, result_emoji FROM recipes 
            WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
        """, (item1_name, item2_name))
        
        recipe = c.fetchone()
        conn.close()
        
        if recipe:
            return {"result": recipe[0], "emoji": recipe[1]}
        
        # Reverse order bhi check karo
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("""
            SELECT result, result_emoji FROM recipes 
            WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
        """, (item2_name, item1_name))
        
        recipe = c.fetchone()
        conn.close()
        
        if recipe:
            return {"result": recipe[0], "emoji": recipe[1]}
        
        return None
    except Exception as e:
        print(f"❌ get_recipe error: {e}")
        return None

async def get_item_name(item_name):
    """Return the item name with proper case from database"""
    try:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT name, emoji FROM elements WHERE LOWER(name) = LOWER(?)", (item_name,))
        item = c.fetchone()
        conn.close()
        
        if item:
            return f"{item[0]} {item[1]}"
        return item_name
    except:
        return item_name

# ===== MONGO (User data - existing code) =====
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
