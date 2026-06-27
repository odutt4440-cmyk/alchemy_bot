import requests
import sqlite3
import json
import time
import gzip
import shutil
import os

DATA_URL = "https://github.com/expitau/InfiniteCraftWiki/raw/refs/heads/main/web/data/data.json"
DB_PATH = "infinite_craft.db"
GZ_PATH = "infinite_craft.db.gz"

print("📥 Downloading data.json...")
resp = requests.get(DATA_URL, timeout=600)
data = resp.json()
index = data["index"]
data_str = data["data"]

print("🗄️ Creating SQLite tables...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS elements (
        code TEXT PRIMARY KEY,
        name TEXT UNIQUE,
        emoji TEXT,
        cost INTEGER
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        first TEXT,
        second TEXT,
        result TEXT,
        first_emoji TEXT,
        second_emoji TEXT,
        result_emoji TEXT,
        UNIQUE(first, second)
    )
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_recipes_result ON recipes(result)")
conn.commit()

print("📦 Inserting elements...")
count = 0
c.execute("BEGIN TRANSACTION")
for code, elem in index.items():
    c.execute("INSERT OR IGNORE INTO elements VALUES (?, ?, ?, ?)",
              (code, elem[1], elem[0], elem[2] if len(elem) > 2 else 0))
    count += 1
    if count % 50000 == 0:
        conn.commit()
        c.execute("BEGIN TRANSACTION")
        print(f"   ✅ {count} elements...")
conn.commit()
e_count = c.execute("SELECT COUNT(*) FROM elements").fetchone()[0]
print(f"   ✅ Total: {e_count} elements")

print("📦 Inserting recipes...")
recipes = data_str.split(";")
total = len(recipes)
count = 0
errors = 0
start = time.time()

c.execute("BEGIN TRANSACTION")
for i, recipe_str in enumerate(recipes):
    if not recipe_str.strip():
        continue
    parts = recipe_str.split(",")
    if len(parts) != 3:
        errors += 1
        continue
    
    a = index.get(parts[0])
    b = index.get(parts[1])
    r = index.get(parts[2])
    if not a or not b or not r:
        errors += 1
        continue
    
    c.execute("INSERT OR IGNORE INTO recipes VALUES (?, ?, ?, ?, ?, ?)",
              (a[1], b[1], r[1], a[0], b[0], r[0]))
    count += 1
    
    if count % 50000 == 0:
        conn.commit()
        c.execute("BEGIN TRANSACTION")
        elapsed = time.time() - start
        rate = count / (elapsed / 60)
        pct = (i / total) * 100
        eta = (total - i) / rate * 60 if rate > 0 else 0
        print(f"   ✅ {count} recipes ({pct:.1f}%) | {rate:.0f}/min | ETA: {eta:.0f}s")

conn.commit()
r_count = c.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
elapsed = time.time() - start
print(f"\n   ✅ DONE! {r_count} recipes in {elapsed:.0f}s")
conn.close()

print("\n🗜️ Compressing...")
with open(DB_PATH, 'rb') as f_in:
    with gzip.open(GZ_PATH, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

orig = os.path.getsize(DB_PATH) / (1024*1024)
comp = os.path.getsize(GZ_PATH) / (1024*1024)
print(f"   Original: {orig:.0f} MB → Compressed: {comp:.0f} MB")
print(f"\n🎉 Done! DB ready at {GZ_PATH}")
