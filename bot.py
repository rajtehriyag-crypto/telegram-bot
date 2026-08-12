# ============================================================
# 🌌 REALMX HELPER BOT
# PART A — CORE / CONFIG / DATABASE
# ============================================================

import os
import sys
import time
import random
import sqlite3
import threading
from datetime import datetime, timedelta
from collections import defaultdict

import telebot
from telebot import types


# ============================================================
# 🔐 CONFIGURATION
# ============================================================

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"

SUPPORT_CHANNEL = "https://t.me/realmXsupport"
SUPPORT_GROUP = "https://t.me/+6BXS6AfvJPQ2OTI1"

# @ ke bina bot username
BOT_USERNAME = "realmXhelperbot"


# ============================================================
# 🤖 BOT INITIALIZATION
# ============================================================

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="HTML",
    threaded=True
)


# ============================================================
# 💾 DATABASE
# ============================================================

DB_FILE = "realmx.db"

db_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


db = get_db()


# ============================================================
# 🗄️ CREATE TABLES
# ============================================================

with db_lock:

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            coins INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            reputation INTEGER DEFAULT 0,
            messages INTEGER DEFAULT 0,
            last_seen TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            messages INTEGER DEFAULT 0,
            welcome_enabled INTEGER DEFAULT 0,
            goodbye_enabled INTEGER DEFAULT 0,
            antispam INTEGER DEFAULT 0,
            antiflood INTEGER DEFAULT 0,
            rules TEXT DEFAULT ''
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER,
            user_id INTEGER,
            warnings INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            chat_id INTEGER,
            user_id INTEGER,
            rank INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            chat_id INTEGER,
            keyword TEXT,
            reply TEXT,
            PRIMARY KEY (chat_id, keyword)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS blocklist (
            chat_id INTEGER,
            word TEXT,
            PRIMARY KEY (chat_id, word)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item TEXT,
            amount INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS marriages (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            chat_id INTEGER,
            user_id INTEGER,
            messages INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS economy_cooldowns (
            user_id INTEGER,
            command TEXT,
            last_used INTEGER,
            PRIMARY KEY (user_id, command)
        )
    """)

    db.commit()


# ============================================================
# 🌐 RUNTIME DATA
# ============================================================

last_deleted_message = {}
last_edited_message = {}

afk_users = {}

flood_tracker = defaultdict(list)

quiz_games = {}

tictactoe_games = {}

pending_marriages = {}

daily_cache = {}

weekly_cache = {}

checkin_cache = {}


# ============================================================
# 👤 USER DATABASE
# ============================================================

def register_user(user):

    if not user:
        return

    username = user.username or ""
    first_name = user.first_name or "User"

    with db_lock:

        db.execute("""
            INSERT INTO users (
                user_id,
                username,
                first_name,
                last_seen
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_seen = excluded.last_seen
        """, (
            user.id,
            username,
            first_name,
            datetime.now().isoformat()
        ))

        db.commit()


# ============================================================
# 👥 GROUP DATABASE
# ============================================================

def register_group(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        return

    with db_lock:

        db.execute("""
            INSERT INTO groups (
                chat_id,
                title
            )
            VALUES (?, ?)

            ON CONFLICT(chat_id)
            DO UPDATE SET
                title = excluded.title
        """, (
            message.chat.id,
            message.chat.title or "Group"
        ))

        db.commit()


# ============================================================
# 📊 ACTIVITY TRACKING
# ============================================================

def track_activity(message):

    if not message.from_user:
        return

    register_user(
        message.from_user
    )

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        return

    register_group(message)

    now = datetime.now().isoformat()

    with db_lock:

        db.execute("""
            INSERT INTO activity (
                chat_id,
                user_id,
                messages,
                last_seen
            )
            VALUES (?, ?, 1, ?)

            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET
                messages = messages + 1,
                last_seen = excluded.last_seen
        """, (
            message.chat.id,
            message.from_user.id,
            now
        ))

        db.execute("""
            UPDATE users
            SET messages = messages + 1,
                last_seen = ?
            WHERE user_id = ?
        """, (
            now,
            message.from_user.id
        ))

        db.execute("""
            UPDATE groups
            SET messages = messages + 1
            WHERE chat_id = ?
        """, (
            message.chat.id,
        ))

        db.commit()


# ============================================================
# 🛡️ ADMIN CHECK
# ============================================================

def is_admin(chat_id, user_id):

    try:

        member = bot.get_chat_member(
            chat_id,
            user_id
        )

        return member.status in [
            "administrator",
            "creator"
        ]

    except Exception:
        return False


# ============================================================
# 👑 OWNER CHECK
# ============================================================

def is_owner(message):

    return (
        message.chat.type == "private"
        and
        message.from_user.id == OWNER_ID
    )


# ============================================================
# 🛡️ OWNER OR ADMIN
# ============================================================

def is_owner_or_admin(message):

    if message.from_user.id == OWNER_ID:
        return True

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        return False

    return is_admin(
        message.chat.id,
        message.from_user.id
    )


# ============================================================
# 👑 STAFF RANK
# ============================================================

def get_staff_rank(chat_id, user_id):

    row = db.execute("""
        SELECT rank
        FROM staff
        WHERE chat_id = ?
        AND user_id = ?
    """, (
        chat_id,
        user_id
    )).fetchone()

    if row:
        return row["rank"]

    return 0


# ============================================================
# ⭐ VIP KEYBOARD
# ============================================================

def vip_panel():

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "👑 Owner",
            url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"
        ),
        types.InlineKeyboardButton(
            "📢 Channel",
            url=SUPPORT_CHANNEL
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "💬 Support",
            url=SUPPORT_GROUP
        )
    )

    return markup


# ============================================================
# 🚫 PERMISSION MESSAGE
# ============================================================

def permission_denied(message):

    bot.reply_to(
        message,
        """
🔒 <b>ACCESS DENIED</b>

You don't have permission to use this command.

🛡️ Required:
Group Admin / Authorized Staff
"""
    )


# ============================================================
# 📝 UNIVERSAL MESSAGE TRACKER
# ============================================================

@bot.message_handler(
    func=lambda message: (
        message.from_user is not None
        and
        message.content_type in [
            "text",
            "photo",
            "video",
            "document",
            "audio",
            "voice",
            "sticker"
        ]
    )
)
def universal_tracker(message):

    try:
        track_activity(message)

    except Exception:
        pass


# ============================================================
# 🌐 BASIC START
# ============================================================

@bot.message_handler(commands=["start"])
def start_command(message):

    register_user(
        message.from_user
    )

    # GROUP
    if message.chat.type in [
        "group",
        "supergroup"
    ]:

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌌 Open REALMX",
                url=f"https://t.me/{BOT_USERNAME}?start=realm"
            )
        )

        bot.reply_to(
            message,
            """
🌌 <b>REALMX HELPER</b>

🔒 Private commands ke liye mujhe DM mein start karein.

👇 Neeche button dabayein.
""",
            reply_markup=markup
        )

        return

    # PRIVATE DM

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🛡️ Commands",
            callback_data="main_commands"
        ),
        types.InlineKeyboardButton(
            "📊 Profile",
            callback_data="main_profile"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📢 Support Channel",
            url=SUPPORT_CHANNEL
        ),
        types.InlineKeyboardButton(
            "💬 Support Group",
            url=SUPPORT_GROUP
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👑 Owner",
            url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"
        )
    )

    bot.send_message(
        message.chat.id,
        f"""
╔════════════════════════════╗
║ 🌌 <b>REALMX HELPER BOT</b> ║
╚════════════════════════════╝

👋 Welcome, <b>{message.from_user.first_name}</b>!

🛡️ Advanced Moderation
💰 Economy System
🎮 Mini Games
📊 Analytics
⚙️ AutoMod
👑 VIP Features

━━━━━━━━━━━━━━━━━━━━

👑 Owner:
{OWNER_USERNAME}

🌌 Welcome to the <b>REALMX NETWORK</b>.
""",
        reply_markup=markup
    )


# ============================================================
# 🔘 MAIN BUTTON CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: call.data.startswith("main_")
)
def main_buttons(call):

    if call.data == "main_commands":

        bot.answer_callback_query(
            call.id
        )

        bot.send_message(
            call.message.chat.id,
            """
🌌 <b>REALMX COMMAND CENTER</b>

🛡️ Moderation
👑 Staff Management
⚙️ AutoMod
📢 Tag System
💰 Economy
🤖 AI & Tools
📊 Analytics
🎮 Games
💬 Social
🔧 Utility
""",
            reply_markup=vip_panel()
        )

    elif call.data == "main_profile":

        bot.answer_callback_query(
            call.id,
            "📊 Profile system coming with the next part."
        )


# ============================================================
# ❤️ BOT START MESSAGE
# ============================================================

print("======================================")
print("🌌 REALMX HELPER BOT")
print("======================================")
print("🟢 Bot is starting...")
print(f"👑 Owner ID: {OWNER_ID}")
print(f"📢 Channel: {SUPPORT_CHANNEL}")
print(f"💬 Group: {SUPPORT_GROUP}")
print("======================================")


# ============================================================
# 🚀 START BOT
# ============================================================

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )
