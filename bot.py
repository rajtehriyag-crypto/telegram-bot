import os
import sqlite3
import telebot

# =========================
# CONFIG
# =========================

TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
OWNER_ID = 8727799160

if not TOKEN:
    raise ValueError("BOT_TOKEN not found!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# DATABASE
# =========================

db = sqlite3.connect("zynox.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    aura INTEGER DEFAULT 0,
    messages INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS groups(
    group_id INTEGER PRIMARY KEY,
    title TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()

# =========================
# USER REGISTER
# =========================

def register_user(user):
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user.id,)
    )

    data = cursor.fetchone()

    if not data:
        cursor.execute(
            """
            INSERT INTO users
            (user_id, username, first_name)
            VALUES (?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.first_name
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
"""
            )
        except:
            pass

# =========================
# TEST COMMAND
# =========================

@bot.message_handler(commands=["start"])
def start_cmd(message):

    register_user(message.from_user)

    bot.reply_to(
        message,
        "✅ Database Working\n✅ User Registration Working"
    )

# =========================
# RUN
# =========================

print("🎮 Zynox Gaming Started...")
bot.infinity_polling(skip_pending=True)
