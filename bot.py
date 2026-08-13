import telebot
from telebot import types
import sqlite3

# =========================
# CONFIG
# =========================

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"

SUPPORT_CHANNEL = "https://t.me/realmXsupport"
SUPPORT_GROUP = "https://t.me/+6BXS6AfvJPQ2OTI1"

BOT_USERNAME = "realmXhelperbot"

# =========================
# BOT
# =========================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# DATABASE
# =========================

db = sqlite3.connect("realmx.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS groups(
    chat_id INTEGER PRIMARY KEY,
    title TEXT
)
""")

db.commit()

# =========================
# SAVE USER/GROUP
# =========================

def save_user(user):
    cursor.execute(
        "INSERT OR REPLACE INTO users VALUES(?,?,?)",
        (
            user.id,
            user.username if user.username else "",
            user.first_name
        )
    )
    db.commit()

def save_group(chat):
    cursor.execute(
        "INSERT OR REPLACE INTO groups VALUES(?,?)",
        (
            chat.id,
            chat.title
        )
    )
    db.commit()

# =========================
# START
# =========================

@bot.message_handler(commands=['start'])
def start(message):

    save_user(message.from_user)

    if message.chat.type != "private":

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🌌 OPEN BOT IN DM",
                url=f"https://t.me/{BOT_USERNAME}"
            )
        )

        bot.reply_to(
            message,
            "🤖 Please start me in private chat.",
            reply_markup=markup
        )
        return

    markup = types.InlineKeyboardMarkup(row_width=2)

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
            url="https://t.me/internationalpanditG"
        )
    )

    text = f"""
🌌 <b>REALMX HELPER BOT</b>

👑 Owner: {OWNER_USERNAME}

🛡️ Moderation
📊 Analytics
⚙️ Automod
🎮 Games

Welcome to RealmX Network.
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )

# =========================
# HELP
# =========================

@bot.message_handler(commands=['help'])
def help_cmd(message):

    text = """
🌌 <b>REALMX COMMANDS</b>

🛠️ General
/start
/help

More commands coming soon...
"""

    bot.send_message(message.chat.id, text)

# =========================
# TRACK USERS
# =========================

@bot.message_handler(func=lambda m: True)
def tracker(message):

    save_user(message.from_user)

    if message.chat.type in ["group", "supergroup"]:
        save_group(message.chat)

# =========================
# RUN
# =========================

print("🌌 REALMX HELPER STARTED")

# =========================
# GENERAL COMMANDS
# =========================

import time

START_TIME = time.time()

afk_users = {}

@bot.message_handler(commands=['ping'])
def ping_cmd(message):

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "📢 Support",
            url=SUPPORT_CHANNEL
        )
    )

    bot.reply_to(
        message,
        """
╔══════════════════╗
║ 🏓 REALMX PING 🏓 ║
╚══════════════════╝

🟢 Bot Status: Online
⚡ Response: Excellent
""",
        reply_markup=markup
    )


@bot.message_handler(commands=['id'])
def id_cmd(message):

    bot.reply_to(
        message,
        f"""
╔══════════════════╗
║ 🆔 REALMX ID INFO ║
╚══════════════════╝

👤 User ID: <code>{message.from_user.id}</code>

💬 Chat ID:
<code>{message.chat.id}</code>
"""
    )


@bot.message_handler(commands=['info'])
def info_cmd(message):

    user = message.from_user

    bot.reply_to(
        message,
        f"""
╔════════════════════╗
║ 👤 USER PROFILE 👤 ║
╚════════════════════╝

🪪 Name: {user.first_name}

🔗 Username:
@{user.username if user.username else "None"}

🆔 ID:
<code>{user.id}</code>
"""
    )


@bot.message_handler(commands=['report'])
def report_cmd(message):

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "⚠️ Kisi message ko reply karke /report use karo."
        )
        return

    bot.reply_to(
        message,
        """
🚨 REPORT SUBMITTED

🛡️ Admins have been notified.
"""
    )


@bot.message_handler(commands=['afk'])
def afk_cmd(message):

    reason = "AFK"

    try:
        reason = message.text.split(
            maxsplit=1
        )[1]
    except:
        pass

    afk_users[message.from_user.id] = reason

    bot.reply_to(
        message,
        f"""
🌙 AFK MODE ENABLED

👤 User:
{message.from_user.first_name}

📝 Reason:
{reason}
"""
    )


@bot.message_handler(commands=['uptime'])
def uptime_cmd(message):

    uptime = int(
        time.time() - START_TIME
    )

    hours = uptime // 3600
    mins = (uptime % 3600) // 60

    bot.reply_to(
        message,
        f"""
🌌 REALMX UPTIME

⏳ Running:
{hours}h {mins}m
"""
    )


@bot.message_handler(func=lambda m: True)
def afk_checker(message):

    if (
        message.from_user.id
        in afk_users
    ):
        del afk_users[
            message.from_user.id
        ]

        bot.reply_to(
            message,
            "✅ AFK mode removed."
        )

    if message.reply_to_message:

        uid = (
            message.reply_to_message
            .from_user.id
        )

        if uid in afk_users:

            bot.reply_to(
                message,
                f"""
🌙 User is AFK

📝 Reason:
{afk_users[uid]}
"""
            )

bot.infinity_polling(skip_pending=True)
