import os
from dotenv import load_dotenv

load_dotenv()

# ===== ENV VARIABLES (Sensitive) =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot_username")  # @ ke bina

# ===== GROUP IDs =====
OFFICIAL_GC_ID = -1001234567890  # ← YAHI DAAL APNA OFFICIAL GROUP ID

# ===== BUTTON URLS =====
DEV_URL = "https://t.me/your_username"
HELP_URL = "https://t.me/help_link"
GC_URL = "https://t.me/your_group"
CHANNEL_URL = "https://t.me/your_channel"

# ===== POINTS & REWARDS SYSTEM =====
CRAFT_POINTS = 10             # Points for leaderboard
CRAFT_COINS = 2               # Coins for rewards
COOLDOWN_SECONDS = 5          # Craft ke beech ka wait time
INITIAL_ITEMS = ["Fire 🔥", "Water 💦", "Earth 🌏", "Air 💨"]

# ===== FILE PATHS =====
DB_PATH = "infinite_craft.db"
RELEASE_URL = "https://github.com/odutt4440-cmyk/alchemy_bot/releases/latest/download/infinite_craft.db.gz"
START_IMAGE = "assets/start_image.jpg"

# ===== MESSAGES =====
START_MSG_DM = (
    "**🧪 Infinite Alchemy Bot**\n\n"
    "You start with 4 basic items: Fire 🔥, Water 💦, Earth 🌏, and Wind 💨.\n"
    "Combine them to discover new elements!\n\n"
    "**How to craft:**\n"
    "Use `/craft [Item1] [Item2]` or `/c [Item1] [Item2]`"
)

START_MSG_OFFICIAL_GC = (
    "**🧪 Welcome to Official GC!**\n\n"
    "Use `/craft [Item1] [Item2]` to combine elements!\n"
    "Use `/help` for more info."
)

START_MSG_OTHER_GROUP = (
    "**🧪 Infinite Alchemy Bot**\n\n"
    "Use me in DM to craft elements!\n"
    f"👉 @{BOT_USERNAME}\n"
    "Type `/start` there."
)

OFFICIAL_WELCOME_MSG = (
    "**🎉 Welcome to the Infinite Alchemy Community!**\n\n"
    "Thanks for joining us! Here you can:\n"
    "🧪 Share your best discoveries\n"
    "💡 Get help with combinations\n"
    "🏆 Compete with other alchemists\n"
    "🔬 Discuss strategies and recipes\n\n"
    "**Quick Start:**\n"
    "👉 Use `/craft` to combine elements\n"
    "👉 Use `/inventory` to see your collection\n"
    "👉 Use `/points` to check your score\n\n"
    "We hope you enjoy your journey! ✨"
)

OTHER_GROUP_MSG = (
    "**🤖 Thanks for adding me in the group!**\n\n"
    "I'm **Infinite Alchemy Bot** — I help you discover new elements by combining items!\n\n"
    "**How to use:**\n"
    "• `/craft Fire Water` — Combine two elements\n"
    "• `/c Fire Water` — Shortcut\n"
    "• `/inventory` — See your collection (DM only)\n"
    "• `/points` — Check your score (DM only)\n\n"
    f"**To play, please use me in DM:** @{BOT_USERNAME}\n"
    "Type `/start` there to begin your journey! ✨"
)

CRAFT_EMPTY_MSG = "⚠️ **Combine 2 objects to discover new elements!**\n\nExample: `/craft Fire Water`"
CRAFT_FORMAT_MSG = "⚠️ **Format:** `/craft [Item1] [Item2]`\nExample: `/craft Fire Water`"
SLOW_DOWN_MSG = "⚠️ **Slow down!** Please wait 5 seconds."
DM_FIRST_MSG = (
    "⚠️ **Please start the bot in DM first!**\n\n"
    f"Click here 👉 @{BOT_USERNAME}\n"
    "Type `/start` there, then come back to craft here!"
)
POINTS_GROUP_MSG = "⚠️ Use `/points` in DM to check your stats!"
INVENTORY_GROUP_MSG = "⚠️ Use `/inventory` in DM to see your collection!"
NOTHING_MSG = "❌ This combination created nothing."

HELP_MSG = (
    "**📖 Help & Support**\n\n"
    "**Commands:**\n"
    "`/start` - Bot introduction\n"
    "`/craft [item1] [item2]` - Combine two elements\n"
    "`/c [item1] [item2]` - Shortcut for craft\n"
    "`/inventory` - View your collection\n"
    "`/points` - Check your score\n\n"
    "**Need more help?**\n"
    f"Join our Official GC: @{GC_URL.split('/')[-1]}\n"
    f"Contact Developer: @{DEV_URL.split('/')[-1]}"
)
