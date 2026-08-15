import telebot
from telebot import types
import os
import json

BOT_TOKEN = os.getenv("8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU")
OWNER_ID = 8727799160

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# =========================
# USER DATABASE
# =========================

USERS_FILE = "users.json"

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def add_user(user_id):
    users = load_users()

    if user_id not in users:
        users.append(user_id)
        save_users(users)

# =========================
# START COMMAND
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    add_user(message.from_user.id)

    user = message.from_user.first_name

    text = f"""
🎮 <b>WELCOME TO ZYNOX GAMING</b> 🎮

👋 Hello <b>{user}</b>

✨ Premium Gaming Experience
🎲 Fun Games
😂 Funny Commands
🏆 Rewards & Rankings

Use the buttons below to explore.

━━━━━━━━━━━━━━━━━━
⚡ Powered By Zynox Gaming
━━━━━━━━━━━━━━━━━━
"""

    markup = types.InlineKeyboardMarkup(row_width=1)

    help_btn = types.InlineKeyboardButton(
        "📚 Help",
        callback_data="help_menu"
    )

    owner_btn = types.InlineKeyboardButton(
        "👑 Owner",
        url="https://t.me/internationalpanditG"
    )

    group_btn = types.InlineKeyboardButton(
        "👥 Support Group",
        url="https://t.me/unseentea"
    )

    channel_btn = types.InlineKeyboardButton(
        "📢 Support Channel",
        url="https://t.me/realmXsupport"
    )

    markup.add(help_btn)
    markup.add(owner_btn)
    markup.add(group_btn)
    markup.add(channel_btn)

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )

# =========================
# HELP MENU
# =========================

@bot.callback_query_handler(func=lambda c: c.data == "help_menu")
def help_menu(call):

    text = """
🎮 <b>ZYNOX GAMING COMMANDS</b>

🎲 GAMES
/rps
/dice
/coin
/guess
/quiz
/scramble
/ttt

😂 FUN
/marry
/divorce
/ship
/bestie
/enemy
/luck
/aura
/simp
/clown
/roast
/joke
/excuse

🏆 PROFILE
/daily
/balance
/profile
/rank
/leaderboard

ℹ️ SYSTEM
/start
/help
"""

    if call.from_user.id == OWNER_ID:
        text += """

👑 OWNER ONLY
/broadcast
/stats
"""

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )

    bot.answer_callback_query(call.id)

# =========================
# HELP COMMAND
# =========================

@bot.message_handler(commands=["help"])
def help_command(message):

    text = """
🎮 <b>Use the Help Button in /start</b>

Press:
📚 Help
"""

    bot.send_message(
        message.chat.id,
        text
    )

print("🎮 Zynox Gaming Started...")

bot.infinity_polling(skip_pending=True)
