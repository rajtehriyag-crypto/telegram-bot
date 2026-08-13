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

bot.infinity_polling(skip_pending=True)
