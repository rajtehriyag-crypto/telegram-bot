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

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL),
        types.InlineKeyboardButton("💬 Support Group", url=SUPPORT_GROUP)
    )

    markup.add(
        types.InlineKeyboardButton("👑 Owner", url="https://t.me/internationalpanditG")
    )

    help_text = """
╔════════════════════════════╗
║ 🌌 REALMX HELPER COMMANDS ║
╚════════════════════════════╝

🛠️ GENERAL & UTILITY

🚀 /start
➜ VIP welcome panel open karta hai.

📚 /help
➜ Saari commands aur unka work dikhata hai.

🏓 /ping
➜ Bot online hai ya nahi check karta hai.

🆔 /id
➜ User ID aur Group ID dikhata hai.

👤 /info
➜ User profile information dikhata hai.

🚨 /report
➜ Reply ki hui message ko admins tak report karta hai.

🌙 /afk [reason]
➜ AFK status set karta hai.

⏳ /uptime
➜ Bot kitne time se online hai dikhata hai.

━━━━━━━━━━━━━━━━━━

🛡️ MODERATION

🔨 /ban
➜ User ko permanently ban karta hai.

✅ /unban
➜ Banned user ko restore karta hai.

👢 /kick
➜ User ko group se remove karta hai.

🔇 /mute [minutes]
➜ User ko temporary mute karta hai.

🔊 /unmute
➜ User ko unmute karta hai.

⚠️ /warn
➜ Warning deta hai.

🟢 /unwarn
➜ Warning remove karta hai.

🧹 /purge
➜ Bulk messages delete karta hai.

📌 /pin
➜ Important message pin karta hai.

📍 /unpin
➜ Pinned message remove karta hai.

━━━━━━━━━━━━━━━━━━

👑 STAFF MANAGEMENT

🥉 /promote1
➜ Realm Keeper rank deta hai.

🥈 /promote2
➜ Realm Guardian rank deta hai.

🥇 /promote3
➜ Realm Commander rank deta hai.

⬇️ /demote
➜ Staff rank remove karta hai.

━━━━━━━━━━━━━━━━━━

⚙️ AUTOMOD

🚫 /antispam
➜ Spam protection ON/OFF.

🛡️ /antiflood
➜ Flood protection ON/OFF.

👋 /welcome
➜ Welcome system manage karta hai.

🚪 /goodbye
➜ Goodbye messages manage karta hai.

✍️ /setwelcome
➜ Custom welcome set karta hai.

📜 /setrules
➜ Group rules save karta hai.

📖 /rules
➜ Saved rules dikhata hai.

⚙️ /filter
➜ Auto reply create karta hai.

❌ /stopfilter
➜ Auto reply remove karta hai.

📝 /blocklist
➜ Blocked words manage karta hai.

━━━━━━━━━━━━━━━━━━

📊 ANALYTICS

🌟 /profile
➜ VIP profile card dikhata hai.

🎖️ /rank
➜ XP aur level progress dikhata hai.

📈 /mystats
➜ Personal activity report dikhata hai.

🏆 /leaderboard
➜ Top users list dikhata hai.

📊 /activity
➜ Aaj ki activity dikhata hai.

📅 /weekly
➜ Weekly stats dikhata hai.

👑 /topusers
➜ Most active users dikhata hai.

━━━━━━━━━━━━━━━━━━

🎮 FUN & GAMES

🎲 /dice
➜ Dice roll karta hai.

🪙 /coin
➜ Coin toss karta hai.

✊ /rps
➜ Rock Paper Scissors game.

🔢 /guess
➜ Number guessing game.

❓ /quiz
➜ Quiz question deta hai.

😇 /truth
➜ Random truth question.

🔥 /dare
➜ Random dare challenge.

🎱 /8ball
➜ Magic 8 Ball answer.

⭕ /tictac
➜ Tic Tac Toe game.

━━━━━━━━━━━━━━━━━━

🔒 OWNER PANEL

👑 /panel
➜ Owner control panel.

📊 /stats
➜ Global bot statistics.

📢 /broadcast
➜ All users ko message.

🌍 /gcast
➜ All groups me message.

💾 /backup
➜ Database backup.

♻️ /restart
➜ Bot restart.

━━━━━━━━━━━━━━━━━━

🌌 REALMX HELPER
👑 Owner: @internationalpanditG
"""

    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=markup
    )

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
# PART B - GENERAL COMMANDS
# =========================

import time

BOT_START_TIME = time.time()

afk_users = {}

# -------------------------
# PING
# -------------------------

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
╔════════════════════╗
║ 🏓 REALMX PING 🏓 ║
╚════════════════════╝

🟢 Status : ONLINE

⚡ Response :
Excellent

🌌 RealmX Network Active
""",
        reply_markup=markup
    )

# -------------------------
# ID
# -------------------------

@bot.message_handler(commands=['id'])
def id_cmd(message):

    bot.reply_to(
        message,
        f"""
╔════════════════════╗
║ 🆔 REALMX ID CARD ║
╚════════════════════╝

👤 USER ID

<code>{message.from_user.id}</code>

💬 CHAT ID

<code>{message.chat.id}</code>
"""
    )

# -------------------------
# INFO
# -------------------------

@bot.message_handler(commands=['info'])
def info_cmd(message):

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "No Username"
    )

    bot.reply_to(
        message,
        f"""
╔══════════════════════╗
║ 👤 REALMX PROFILE 👤 ║
╚══════════════════════╝

🪪 Name :
{user.first_name}

🔗 Username :
{username}

🆔 User ID :
<code>{user.id}</code>

🌌 Member Of RealmX
"""
    )

# -------------------------
# REPORT
# -------------------------

@bot.message_handler(commands=['report'])
def report_cmd(message):

    if not message.reply_to_message:

        bot.reply_to(
            message,
            """
⚠️ REPORT FAILED

Reply to a message and use:

/report
"""
        )
        return

    bot.reply_to(
        message,
        """
🚨 REALMX REPORT

🛡️ Report Submitted

Admins have been notified.
"""
    )

# -------------------------
# AFK
# -------------------------

@bot.message_handler(commands=['afk'])
def afk_cmd(message):

    reason = "AFK"

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) > 1:
        reason = parts[1]

    afk_users[
        message.from_user.id
    ] = reason

    bot.reply_to(
        message,
        f"""
🌙 AFK MODE ENABLED

👤 User :
{message.from_user.first_name}

📝 Reason :
{reason}
"""
    )

# -------------------------
# UPTIME
# -------------------------

@bot.message_handler(commands=['uptime'])
def uptime_cmd(message):

    uptime = int(
        time.time() -
        BOT_START_TIME
    )

    hours = uptime // 3600
    minutes = (
        uptime % 3600
    ) // 60

    bot.reply_to(
        message,
        f"""
⏳ REALMX UPTIME

🟢 Running For

{hours} Hours
{minutes} Minutes
"""
    )

# -------------------------
# AFK WATCHER
# -------------------------

@bot.message_handler(
    func=lambda m:
    m.reply_to_message is not None
)
def afk_watch(message):

    target = (
        message.reply_to_message
        .from_user.id
    )

    if target in afk_users:

        bot.reply_to(
            message,
            f"""
🌙 USER IS AFK

📝 Reason :

{afk_users[target]}
"""
    )
@bot.message_handler(func=lambda m: True)
def tracker(message):

    save_user(message.from_user)

    if message.chat.type in ["group", "supergroup"]:
        save_group(message.chat)        

print("🌌 REALMX HELPER STARTED")

bot.infinity_polling(skip_pending=True)
