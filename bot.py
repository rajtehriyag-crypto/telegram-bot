# ==========================================
# ZYNOX GAMING BOT - PART 1A
# Config + Database + User Registration
# ==========================================

import sqlite3
import telebot
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==========================================
# CONFIG
# ==========================================

BOT_TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"

OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"

BOT_USERNAME = "zynoxgamingbot"

SUPPORT_CHANNEL = "https://t.me/+CS-ZvjWSB1oxZjZl"
SUPPORT_GROUP = "https://t.me/+97rox0VQWXNiMzg1"

# ==========================================
# BOT
# ==========================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)

# ==========================================
# DATABASE
# ==========================================

db = sqlite3.connect(
    "zynox.db",
    check_same_thread=False
)

cursor = db.cursor()

# ==========================================
# USERS TABLE
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    coins INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    created_at TEXT
)
""")

db.commit()

# ==========================================
# USER REGISTER
# ==========================================

def register_user(user):

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,)
    )

    data = cursor.fetchone()

    if data:
        return False

    cursor.execute("""
    INSERT INTO users(
        user_id,
        username,
        first_name,
        created_at
    )
    VALUES(?,?,?,?)
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    ))

    db.commit()

    return True

# ==========================================
# GET USER
# ==========================================

def get_user(user_id):

    cursor.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    return cursor.fetchone()

# ==========================================
# OWNER NOTIFICATION
# ==========================================

def notify_owner_new_user(user):

    try:

        text = f"""
🚀 <b>NEW USER STARTED BOT</b>

👤 Name: {user.first_name}

🆔 ID:
<code>{user.id}</code>

📛 Username:
@{user.username if user.username else 'None'}

🎮 Bot:
@{BOT_USERNAME}
"""

        bot.send_message(
            OWNER_ID,
            text
        )

    except Exception as e:
        print(
            "Owner Notification Error:",
            e
        )

# ==========================================
# END OF PART 1A
# ==========================================
# ==========================================
# ZYNOX GAMING BOT - PART 1B
# START SYSTEM + VIP WELCOME
# ==========================================

@bot.message_handler(commands=["start"])
def start_command(message):

    # --------------------------------------
    # GROUP START
    # --------------------------------------

    if message.chat.type != "private":

        group_text = f"""
╔═ 🎮✨ ZYNOX GAMING ✨🎮 ═╗

🤖 Bot Menu DM Me Available

💎 Start The Bot To:
🪙 Earn Coins
⭐ Gain XP
🏆 Climb Leaderboards
🎮 Play Games

╚════ 🚀 START NOW 🚀 ════╝
"""

        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "🎮 START BOT",
                url=f"https://t.me/{BOT_USERNAME}?start=welcome"
            )
        )

        bot.reply_to(
            message,
            group_text,
            reply_markup=keyboard
        )

        return

    # --------------------------------------
    # DM START
    # --------------------------------------

    is_new_user = register_user(
        message.from_user
    )

    # Notify Owner Only On First Start

    if is_new_user:
        notify_owner_new_user(
            message.from_user
        )

    first_name = (
        message.from_user.first_name
        or "Player"
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "No Username"
    )

    vip_text = f"""
╔═ 🎉✨ WELCOME ✨🎉 ═╗

👋 Welcome, {first_name} 💎

🆔 User ID :
<code>{message.from_user.id}</code>

👤 Username :
{username}

🎮 Welcome To 🎮

✅ 𝐙𝐘𝐍𝐎𝐗 𝐆𝐀𝐌𝐈𝐍𝐆 ✅

╚══ 🚀💓 ENJOY 💓🚀 ══╝
"""

    keyboard = InlineKeyboardMarkup(
        row_width=2
    )

    keyboard.add(
        InlineKeyboardButton(
            "👤 PROFILE",
            callback_data="profile"
        ),
        InlineKeyboardButton(
            "❓ HELP",
            callback_data="help"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "📢 SUPPORT CHANNEL",
            url=SUPPORT_CHANNEL
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "👥 SUPPORT GROUP",
            url=SUPPORT_GROUP
        )
    )

    bot.send_message(
        message.chat.id,
        vip_text,
        reply_markup=keyboard
    )

# ==========================================
# CALLBACK PLACEHOLDERS
# ==========================================

@bot.callback_query_handler(
    func=lambda call: True
)
def callback_handler(call):

    if call.data == "profile":

        bot.answer_callback_query(
            call.id,
            "👤 Use /profile"
        )

    elif call.data == "help":

        bot.answer_callback_query(
            call.id,
            "📖 Use /help"
        )

# ==========================================
# END OF PART 1B
# ==========================================
# ==========================================
# ZYNOX GAMING BOT - PART 1C
# PROFILE + HELP + STARTUP
# ==========================================

@bot.message_handler(commands=["profile"])
def profile_command(message):

    user = get_user(
        message.from_user.id
    )

    if not user:

        register_user(
            message.from_user
        )

        user = get_user(
            message.from_user.id
        )

    profile_text = f"""
╔═ 👤 PROFILE ═╗

🆔 ID :
<code>{user[0]}</code>

👤 Name :
{user[2]}

📛 Username :
@{user[1] if user[1] else 'None'}

🪙 Coins :
{user[3]}

⭐ XP :
{user[4]}

🎖 Level :
{user[5]}

🏆 Wins :
{user[6]}

❌ Losses :
{user[7]}

╚══════════════╝
"""

    bot.reply_to(
        message,
        profile_text
    )

# ==========================================
# HELP COMMAND
# ==========================================

@bot.message_handler(commands=["help"])
def help_command(message):

    help_text = """
╔═ 🎮 ZYNOX HELP ═╗

📋 Commands

/start
/profile
/help

🎲 Games

/ttt
/rps

💰 Coin Games

/ttt 50+
/rps 50+

🎁 Coming Soon

/daily
/dice
/rank
/leaderboard

╚══════════════╝
"""

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "📢 Support Channel",
            url=SUPPORT_CHANNEL
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "👥 Support Group",
            url=SUPPORT_GROUP
        )
    )

    bot.reply_to(
        message,
        help_text,
        reply_markup=keyboard
    )

# ==========================================
# ERROR HANDLER
# ==========================================

def run_bot():

    print("ZYNOX GAMING STARTED")

    while True:

        try:

            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:

            print(
                "BOT ERROR:",
                e
            )

# ==========================================
# START BOT
# ==========================================

if __name__ == "__main__":

    run_bot()

# ==========================================
# END OF PART 1C
# ==========================================
