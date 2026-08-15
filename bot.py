import telebot
from telebot import types
import os
import json

BOT_TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
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

import random

# =========================
# TARGET USER HELPER
# =========================

def get_target_user(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user

    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        class FakeUser:
            def __init__(self, name):
                self.first_name = name

        return FakeUser(args[1])

    return None

# =========================
# MARRY COMMAND
# =========================

@bot.message_handler(commands=["marry"])
def marry_cmd(message):

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            "💍 Reply kisi user ko karo ya /marry @username use karo."
        )
        return

    rate = random.randint(80, 100)

    text = f"""
💍✨ <b>ZYNOX MARRIAGE SYSTEM</b> ✨💍

🤵 {message.from_user.first_name}
💖
👰 {target.first_name}

🎊 Congratulations!

💒 Marriage Success: <b>{rate}%</b>
🎁 Wedding Gift: 500 Coins

❤️ Official Zynox Couple ❤️
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML"
    )

# =========================
# DIVORCE COMMAND
# =========================

@bot.message_handler(commands=["divorce"])
def divorce_cmd(message):

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            "💔 Reply kisi user ko karo ya /divorce @username use karo."
        )
        return

    text = f"""
💔 <b>DIVORCE APPROVED</b> 💔

👤 {message.from_user.first_name}
⚡
👤 {target.first_name}

📜 Court Decision: Approved
💸 Alimony: 999 Coins

😭 Relationship Status: Ended
"""

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML"
    )

# =========================
# SHIP COMMAND
# =========================

@bot.message_handler(commands=["ship"])
def ship_cmd(message):

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            "❤️ Reply kisi user ko karo ya /ship @username use karo."
        )
        return

    score = random.randint(1, 100)

    bot.send_message(
        message.chat.id,
        f"""
❤️ <b>ZYNOX SHIP SYSTEM</b> ❤️

👤 {message.from_user.first_name}
💞
👤 {target.first_name}

💕 Compatibility: <b>{score}%</b>
""",
        parse_mode="HTML"
    )

# =========================
# BESTIE COMMAND
# =========================

@bot.message_handler(commands=["bestie"])
def bestie_cmd(message):

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            "🫂 Reply kisi user ko karo ya /bestie @username use karo."
        )
        return

    bot.send_message(
        message.chat.id,
        f"""
🫂 <b>BEST FRIENDS FOREVER</b> 🫂

👤 {message.from_user.first_name}
🤝
👤 {target.first_name}

💙 Friendship Level: {random.randint(90,100)}%
🏆 Official Besties!
""",
        parse_mode="HTML"
    )

# =========================
# ENEMY COMMAND
# =========================

@bot.message_handler(commands=["enemy"])
def enemy_cmd(message):

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            "😈 Reply kisi user ko karo ya /enemy @username use karo."
        )
        return

    bot.send_message(
        message.chat.id,
        f"""
⚔️ <b>ENEMY MODE ACTIVATED</b> ⚔️

😈 {message.from_user.first_name}
🆚
😈 {target.first_name}

🔥 Rivalry Level: {random.randint(80,100)}%

⚡ Battle Begins!
""",
        parse_mode="HTML"
    )


print("🎮 Zynox Gaming Started...")

bot.infinity_polling(skip_pending=True)
