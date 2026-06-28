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

# ===== SQLITE (Game data - downloaded from GitHub Release) =====
SQLITE_DB_PATH = "infinite_craft.db"
# ✅ Latest release se DB download karega
RELEASE_URL = "https://github.com/odutt4440-cmyk/alchemy_bot/releases/latest/download/infinite_craft.db.gz"

def _download_sqlite_db():
    """Download DB from GitHub Release if not exists"""
    if os.path.exists(SQLITE_DB_PATH):
        print(f"✅ DB already exists ({os.path.getsize(SQLITE_DB_PATH)/1024/1024:.0f} MB)")
        return
    
    print("📥 Downloading game database from Release...")
    
    resp = requests.get(RELEASE_URL, stream=True)
    
    if resp.status_code != 200:
        print(f"❌ Download failed: HTTP {resp.status_code}")
        print(f"   URL: {RELEASE_URL}")
        return
    
    # Download compressed file
    total_size = int(resp.headers.get('content-length', 0))
    downloaded = 0
    
    with open("infinite_craft.db.gz", "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = (downloaded / total_size) * 100
                print(f"   ⏳ Downloading... {pct:.0f}%", end="\r")
    
    print(f"\n   ✅ Downloaded ({downloaded/1024/1024:.0f} MB)")
    
    # Decompress
    print("📦 Decompressing...")
    with gzip.open("infinite_craft.db.gz", "rb") as f_in:
        with open(SQLITE_DB_PATH, "wb") as f_out:
            f_out.write(f_in.read())
    
    os.remove("infinite_craft.db.gz")
    
    # Verify
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM recipes")
        r_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM elements")
        e_count = c.fetchone()[0]
        conn.close()
        print(f"✅ Game DB ready! {e_count} elements, {r_count} recipes")
    except Exception as e:
        print(f"⚠️ DB verification error: {e}")

def _get_sqlite_conn():
    """Get SQLite connection with proper row factory"""
    _download_sqlite_db()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== GAME DATA LOOKUP (SQLite) =====
async def get_recipe(item1_name, item2_name):
    try:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        
        # Direct order
        c.execute("""
            SELECT result, result_emoji FROM recipes 
            WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
        """, (item1_name, item2_name))
        
        row = c.fetchone()
        
        if not row:
            # Reverse order
            c.execute("""
                SELECT result, result_emoji FROM recipes 
                WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
            """, (item2_name, item1_name))
            row = c.fetchone()
        
        conn.close()
        
        if row:
            return {"result": f"{row[0]} {row[1]}", "emoji": row[1]}
        
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
        row = c.fetchone()
        conn.close()
        
        if row:
            return f"{row[0]} {row[1]}"
        return item_name
    except:
        return item_name

# ===== MONGO (User data) =====
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
        
        if new_item_name:
            update_query.setdefault("$addToSet", {})["inventory"] = new_item_name
            
        await db.users.update_one({"user_id": user_id}, update_query)
