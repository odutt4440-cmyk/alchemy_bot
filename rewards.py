from database import db

async def request_reward(user_id, reward_type):
    user = await db.users.find_one({"user_id": user_id})
    
    # Requirement check
    required = 10000 if reward_type == "telegram_account" else 15000
    
    if user['points'] < required:
        return False, f"Not enough points! Need {required}."
    
    # Yahan admin ko request bhejoge (Admin ID .env mein honi chahiye)
    # Admin approval logic will be added in main.py via InlineButton
    return True, "Request sent to Admin!"
