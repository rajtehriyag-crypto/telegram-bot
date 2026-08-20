import os
import sqlite3
import telebot
from telebot import types

# =========================
# CONFIG
# =========================

TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
OWNER_ID = 8727799160

GROUP_LINK = "https://t.me/+6BXS6AfvJPQ2OTI1"
CHANNEL_LINK = "https://t.me/+CS-ZvjWSB1oxZjZl"

if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# DATABASE
# =========================

db = sqlite3.connect("zynox.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS groups_db(
    group_id INTEGER PRIMARY KEY,
    title TEXT
)
""")

db.commit()

# =========================
# HELPERS
# =========================

def register_user(user):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (
                user.id,
                user.first_name or "",
                user.username or ""
            )
        )
        db.commit()

        try:
            bot.send_message(
                OWNER_ID,
                f"""
🚀 <b>NEW USER STARTED BOT</b>

👤 Name: {user.first_name}

🆔 ID: <code>{user.id}</code>

📛 Username:
@{user.username if user.username else 'No Username'}

✅ Database Working
✅ User Registration Working
"""
            )
        except:
            pass


def register_group(chat):
    cur.execute(
        "SELECT group_id FROM groups_db WHERE group_id=?",
        (chat.id,)
    )

    exists = cur.fetchone()

    if not exists:
        cur.execute(
            "INSERT INTO groups_db VALUES (?, ?)",
            (chat.id, chat.title)
        )
        db.commit()

        try:
            bot.send_message(
                OWNER_ID,
                f"""
👥 <b>BOT ADDED TO NEW GROUP</b>

📛 Group:
{chat.title}

🆔 ID:
<code>{chat.id}</code>
"""
            )
        except:
            pass


def start_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "👑 Creator",
            callback_data="creator"
        ),
        types.InlineKeyboardButton(
            "📚 Guide",
            callback_data="guide"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "⚡ Features",
            callback_data="features"
        ),
        types.InlineKeyboardButton(
            "🌐 Community",
            callback_data="community"
        )
    )

    return markup


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start_cmd(message):

    if message.chat.type != "private":

        btn = types.InlineKeyboardMarkup()
        btn.add(
            types.InlineKeyboardButton(
                "🚀 Open Zynox Gaming",
                url=f"https://t.me/{bot.get_me().username}"
            )
        )

        bot.reply_to(
            message,
            "📩 Please start me in DM first.",
            reply_markup=btn
        )
        return

    register_user(message.from_user)

    text = """
<b>🎮 ZYNOX GAMING</b>

✨ Aura System
🎮 Multiplayer Games
💍 Relationship System
🏆 Global Rankings

🌌 Build your Aura. Rule the Leaderboard.
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=start_menu()
    )


# =========================
# GROUP REGISTER
# =========================

@bot.message_handler(content_types=["new_chat_members"])
def joined_group(message):
    register_group(message.chat)


# =========================
# CALLBACKS
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):

    if call.data == "creator":

        bot.answer_callback_query(call.id)

        bot.edit_message_text(
            """
👑 <b>CREATOR</b>

📛 @internationalpanditG

🚀 Founder Of Zynox Gaming
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=start_menu()
        )

    elif call.data == "guide":

        bot.answer_callback_query(call.id)

        bot.edit_message_text(
            """
📚 <b>GUIDE</b>

💍 Marriage System

✨ Aura System

🫂 Friendship System

🧠 Random Quiz

🎁 Daily Claim

🏆 Leaderboards
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=start_menu()
        )

    elif call.data == "features":

        bot.answer_callback_query(call.id)

        bot.edit_message_text(
            """
⚡ <b>FEATURES</b>

✨ Aura Economy

🏆 Global Rankings

💍 Marriage System

🫂 Friendship Tracking

🎁 Daily Rewards

🧠 Random Quizzes
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=start_menu()
        )

    elif call.data == "community":

        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "👥 Support Group",
                url=GROUP_LINK
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "📢 Support Channel",
                url=CHANNEL_LINK
            )
        )

        bot.edit_message_text(
            "🌐 <b>COMMUNITY</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

@bot.message_handler(commands=["profile"])
def profile_cmd(message):

    bot.reply_to(
        message,
        """
👤 PROFILE

⚡ Aura: 0

🏅 Rank: 🥉 Bronze

🔥 Streak: 0

💍 Partner: Single
"""
    )

print("🎮 Zynox Gaming Started...")
bot.infinity_polling(skip_pending=True)
