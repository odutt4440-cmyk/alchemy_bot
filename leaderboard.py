from telethon import Button
from database import db
from datetime import datetime  # Ye line tumhare file mein hogi hi

async def get_lb_markup(current_mode):
    # Mode: "global_points_today"
    m = current_mode.split('_')
    
    return [
        [Button.inline("« Global »" if m[0] != "global" else "✅ Global", f"lb_global_{m[1]}_{m[2]}"), 
         Button.inline("This chat" if m[0] != "chat" else "✅ This chat", f"lb_chat_{m[1]}_{m[2]}")],
        [Button.inline("Most Craft" if m[1] != "craft" else "✅ Most Craft", f"lb_{m[0]}_craft_{m[2]}"), 
         Button.inline("Most Points" if m[1] != "points" else "✅ Most Points", f"lb_{m[0]}_points_{m[2]}")],
        [Button.inline("Today" if m[2] != "today" else "✅ Today", f"lb_{m[0]}_{m[1]}_today"), 
         Button.inline("All time" if m[2] != "all" else "✅ All time", f"lb_{m[0]}_{m[1]}_all")],
        [Button.inline("🔄 Refresh", f"refresh_{current_mode}")]
    ]

async def fetch_leaderboard_data(mode_str, chat_id=None):
    # Split mode: global/chat, craft/points, today/all
    m = mode_str.split('_')
    scope, category, time_frame = m[0], m[1], m[2]
    
    # 1. Base Match Stage
    match_stage = {}
    
    # Scope filter (This Chat vs Global)
    if scope == "chat" and chat_id:
        match_stage["group_id"] = chat_id
    
    # 2. Time Filter (Today vs All)
    if time_frame == "today":
        # Yahan fix dekho: datetime.utcnow() use kiya hai
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        match_stage["crafted_at"] = {"$gte": start_date}
            
    # 3. Pipeline
    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$user_id", 
            "total": {"$sum": "$points" if category == "points" else 1}
        }},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]
    
    # 4. Aggregate query execute karo
    try:
        results = await db.craft_history.aggregate(pipeline).to_list(length=10)
    except Exception as e:
        print(f"Leaderboard aggregation error: {e}")
        return []
        
    # 5. Naam attach karo (Lookup optimization)
    for entry in results:
        user_info = await db.users.find_one({"user_id": entry["_id"]})
        entry["first_name"] = user_info.get("first_name", "Unknown") if user_info else "Unknown"
            
    return results
