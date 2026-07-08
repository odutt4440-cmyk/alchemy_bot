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

    # --- CASE 1: GLOBAL ALL-TIME (Source: db.users) ---
    if scope == "global" and time_frame == "all":
        sort_field = "points" if category == "points" else "crafted_count"
        # Users collection se directly fetch karo
        cursor = db.users.find({}).sort(sort_field, -1).limit(10)
        results = await cursor.to_list(length=10)
        
        # Format match karne ke liye process karo
        formatted = []
        for user in results:
            formatted.append({
                "_id": user.get("user_id"),
                "total": user.get(sort_field, 0),
                "first_name": user.get("first_name", "Unknown")
            })
        return formatted

    # --- CASE 2: THIS CHAT OR TODAY (Source: db.craft_history) ---
    else:
        match_stage = {}
        
        # Agar scope chat hai toh filter lagao
        if scope == "chat" and chat_id:
            match_stage["group_id"] = chat_id
            
        # Agar time_frame today hai toh date filter lagao
        if time_frame == "today":
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            match_stage["crafted_at"] = {"$gte": start_date}
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$user_id", 
                "total": {"$sum": "$points" if category == "points" else 1}
            }},
            {"$sort": {"total": -1}},
            {"$limit": 10}
        ]
        
        try:
            results = await db.craft_history.aggregate(pipeline).to_list(length=10)
        except Exception as e:
            print(f"Leaderboard aggregation error: {e}")
            return []
            
        # Name lookup
        for entry in results:
            user_info = await db.users.find_one({"user_id": entry["_id"]})
            entry["first_name"] = user_info.get("first_name", "Unknown") if user_info else "Unknown"
            
        return results
