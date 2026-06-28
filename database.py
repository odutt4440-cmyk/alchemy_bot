from motor.motor_asyncio import AsyncIOMotorClient
import datetime
import os
import sqlite3
import requests
import gzip
from config import MONGO_URI, DB_PATH, RELEASE_URL, CRAFT_POINTS, CRAFT_COINS, OWNER_ID, COOLDOWN_SECONDS, INITIAL_ITEMS

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI is not set!")

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.infinite_craft

# SQLite connection cache
_sqlite_conn = None

def _download_sqlite_db():
    """Download DB from GitHub Release if not exists - only once"""
    global _sqlite_conn
    
    if os.path.exists(DB_PATH):
        return
    
    print("📥 Downloading game database from Release...")
    
    resp = requests.get(RELEASE_URL, stream=True)
    
    if resp.status_code != 200:
        print(f"❌ Download failed: HTTP {resp.status_code}")
        return
    
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
    
    print("📦 Decompressing...")
    with gzip.open("infinite_craft.db.gz", "rb") as f_in:
        with open(DB_PATH, "wb") as f_out:
            f_out.write(f_in.read())
    
    os.remove("infinite_craft.db.gz")
    
    try:
        conn = sqlite3.connect(DB_PATH)
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
    """Get SQLite connection - cached for performance"""
    global _sqlite_conn
    _download_sqlite_db()
    
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
    
    return _sqlite_conn

# ===== GAME DATA LOOKUP (SQLite) =====
async def get_recipe(item1_name, item2_name):
    try:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT result, result_emoji FROM recipes 
            WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
        """, (item1_name, item2_name))
        
        row = c.fetchone()
        
        if not row:
            c.execute("""
                SELECT result, result_emoji FROM recipes 
                WHERE LOWER(first) = LOWER(?) AND LOWER(second) = LOWER(?)
            """, (item2_name, item1_name))
            row = c.fetchone()
        
        if row:
            return {"result": f"{row[0]} {row[1]}", "emoji": row[1]}
        
        return None
    except Exception as e:
        print(f"❌ get_recipe error: {e}")
        return None

async def get_item_name(item_name):
    try:
        conn = _get_sqlite_conn()
        c = conn.cursor()
        c.execute("SELECT name, emoji FROM elements WHERE LOWER(name) = LOWER(?)", (item_name,))
        row = c.fetchone()
        
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
    
    return (now - last_time).total_seconds() >= COOLDOWN_SECONDS

# add_craft_point ko update karo (coins support ke liye)
async def add_craft_point(user_id, new_item_name=None, points=None, coins=None):
    points = points if points is not None else CRAFT_POINTS
    coins = coins if coins is not None else CRAFT_COINS # config se import karna
    now = datetime.datetime.now(datetime.timezone.utc)
    
    user = await db.users.find_one({"user_id": user_id})
    
    if not user:
        await db.users.insert_one({
            "user_id": user_id,
            "points": points,
            "coins": coins,
            "crafted_count": 1,
            "last_craft_time": now,
            "inventory": INITIAL_ITEMS,
            "is_banned": False,
            "is_admin": False
        })
    else:
        update_query = {
            "$inc": {"points": points, "coins": coins, "crafted_count": 1},
            "$set": {"last_craft_time": now}
        }
        if "inventory" not in user or not user["inventory"]:
            update_query.setdefault("$set", {})["inventory"] = INITIAL_ITEMS
        if new_item_name:
            update_query.setdefault("$addToSet", {})["inventory"] = new_item_name
        await db.users.update_one({"user_id": user_id}, update_query)

async def is_admin(user_id):
    # Agar ye True return nahi kar raha, toh command nahi chalegi
    if user_id == OWNER_ID:
        return True
    user = await db.users.find_one({"user_id": user_id})
    return user.get("is_admin", False) if user else False
