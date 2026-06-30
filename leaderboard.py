from telethon import Button
from database import db
from datetime import datetime

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
    m = mode_str.split('_')
    scope, category, time_frame = m[0], m[1], m[2]
    
    # 1. ALL TIME LOGIC (Directly from db.users)
    if time_frame == "all":
        field = "crafted_count" if category == "craft" else "points"
        query = {"group_id": chat_id} if scope == "chat" and chat_id else {}
        
        # Agar scope chat hai toh humein users ka group history check karna hoga
        # Simple version: All time global hi sahi work karega
        cursor = db.users.find({}).sort(field, -1).limit(10)
        return await cursor.to_list(length=10)

    # 2. TODAY LOGIC (From craft_history)
    else:
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        match_stage = {"crafted_at": {"$gte": start_date}}
        if scope == "chat" and chat_id:
            match_stage["group_id"] = chat_id
            
        field = "points" if category == "points" else "points" # Assuming history has points
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}}},
            {"$sort": {"total": -1}},
            {"$limit": 10}
        ]
        return await db.craft_history.aggregate(pipeline).to_list(length=10)
