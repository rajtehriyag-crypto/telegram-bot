# ============================================================
# 🌌 REALMX HELPER BOT - UNIFIED & FIXED
# ============================================================

import os
import sys
import time
import random
import sqlite3
import threading
import json
import shutil
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
BOT_USERNAME = "realmXhelperbot"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)

# ============================================================
# 💾 DATABASE
# ============================================================
DB_FILE = "realmx.db"
db_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()

with db_lock:
    db.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, coins INTEGER DEFAULT 0, bank INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, reputation INTEGER DEFAULT 0, messages INTEGER DEFAULT 0, last_seen TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, title TEXT, messages INTEGER DEFAULT 0, welcome_enabled INTEGER DEFAULT 0, goodbye_enabled INTEGER DEFAULT 0, antispam INTEGER DEFAULT 0, antiflood INTEGER DEFAULT 0, rules TEXT DEFAULT '', welcome_text TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS warnings (chat_id INTEGER, user_id INTEGER, warnings INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS staff (chat_id INTEGER, user_id INTEGER, rank INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, keyword TEXT, reply TEXT, PRIMARY KEY (chat_id, keyword))""")
    db.execute("""CREATE TABLE IF NOT EXISTS blocklist (chat_id INTEGER, word TEXT, PRIMARY KEY (chat_id, word))""")
    db.execute("""CREATE TABLE IF NOT EXISTS activity (chat_id INTEGER, user_id INTEGER, messages INTEGER DEFAULT 0, last_seen TEXT, PRIMARY KEY (chat_id, user_id))""")
    
    # Missing Tables Added Here
    db.execute("""CREATE TABLE IF NOT EXISTS message_stats (chat_id INTEGER, user_id INTEGER, timestamp INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS profiles (chat_id INTEGER, user_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1, messages INTEGER DEFAULT 0, coins INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS afk (user_id INTEGER PRIMARY KEY, reason TEXT, since INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS reputation (user_id INTEGER, chat_id INTEGER, rep INTEGER DEFAULT 0, PRIMARY KEY (user_id, chat_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS quizzes (quiz_id INTEGER PRIMARY KEY, chat_id INTEGER, question TEXT, answer TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS tictactoe (game_id INTEGER PRIMARY KEY, chat_id INTEGER, player_id INTEGER, board TEXT, turn TEXT)""")
    db.commit()

# ============================================================
# 🌐 RUNTIME DATA
# ============================================================
last_deleted_message = {}
last_edited_message = {}

# ============================================================
# 👤 HELPERS & TRACKING
# ============================================================
def register_user(user):
    if not user: return
    with db_lock:
        db.execute("INSERT INTO users (user_id, username, first_name, last_seen) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username = excluded.username, first_name = excluded.first_name, last_seen = excluded.last_seen", (user.id, user.username or "", user.first_name or "User", datetime.now().isoformat()))
        db.commit()

def register_group(message):
    if message.chat.type not in ["group", "supergroup"]: return
    with db_lock:
        db.execute("INSERT INTO groups (chat_id, title) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title", (message.chat.id, message.chat.title or "Group"))
        db.commit()

def track_activity(message):
    if not message.from_user: return
    register_user(message.from_user)
    if message.chat.type not in ["group", "supergroup"]: return
    register_group(message)
    now = datetime.now().isoformat()
    with db_lock:
        db.execute("INSERT INTO activity (chat_id, user_id, messages, last_seen) VALUES (?, ?, 1, ?) ON CONFLICT(chat_id, user_id) DO UPDATE SET messages = messages + 1, last_seen = excluded.last_seen", (message.chat.id, message.from_user.id, now))
        db.execute("UPDATE users SET messages = messages + 1, last_seen = ? WHERE user_id = ?", (now, message.from_user.id))
        db.execute("UPDATE groups SET messages = messages + 1 WHERE chat_id = ?", (message.chat.id,))
        db.commit()

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except: return False

def is_owner_or_admin(message):
    if message.from_user.id == OWNER_ID: return True
    if message.chat.type not in ["group", "supergroup"]: return False
    return is_admin(message.chat.id, message.from_user.id)

def permission_denied(message):
    bot.reply_to(message, "🔒 <b>ACCESS DENIED</b>\n\nYou don't have permission to use this command.\n🛡️ Required: Group Admin / Authorized Staff")

def vip_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"),
        types.InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL)
    )
    markup.add(types.InlineKeyboardButton("💬 Support", url=SUPPORT_GROUP))
    return markup

# ============================================================
# 📝 UNIVERSAL TRACKER & START
# ============================================================
@bot.message_handler(func=lambda message: message.from_user is not None and message.content_type in ["text", "photo", "video", "document", "audio", "voice", "sticker"])
def universal_tracker(message):
    try: track_activity(message)
    except: pass

@bot.message_handler(commands=["start"])
def start_command(message):
    register_user(message.from_user)
    if message.chat.type in ["group", "supergroup"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌌 Open REALMX", url=f"https://t.me/{BOT_USERNAME}?start=realm"))
        bot.reply_to(message, "🌌 <b>REALMX HELPER</b>\n\n🔒 Private commands ke liye mujhe DM mein start karein.\n👇 Neeche button dabayein.", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🛡️ Commands", callback_data="main_commands"), types.InlineKeyboardButton("📊 Profile", callback_data="main_profile"))
    markup.add(types.InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL), types.InlineKeyboardButton("💬 Group", url=SUPPORT_GROUP))
    markup.add(types.InlineKeyboardButton("👑 Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))
    bot.send_message(message.chat.id, f"╔════════════════════════════╗\n║ 🌌 <b>REALMX HELPER BOT</b> ║\n╚════════════════════════════╝\n\n👋 Welcome, <b>{message.from_user.first_name}</b>!\n\n🛡️ Advanced Moderation\n💰 Economy System\n🎮 Mini Games\n📊 Analytics\n⚙️ AutoMod\n👑 VIP Features", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("main_"))
def main_buttons(call):
    if call.data == "main_commands":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🌌 <b>REALMX COMMAND CENTER</b>\n\n🛡️ Moderation\n👑 Staff Management\n⚙️ AutoMod\n📢 Tag System\n💰 Economy\n🤖 AI & Tools\n📊 Analytics\n🎮 Games", reply_markup=vip_panel())
    elif call.data == "main_profile":
        bot.answer_callback_query(call.id, "📊 Profile system coming with the next part.")

# ============================================================
# 🛡️ MODERATION HELPERS
# ============================================================
def get_target_user(message):
    if message.reply_to_message: return message.reply_to_message.from_user
    parts = message.text.split()
    if len(parts) < 2: return None
    target = parts[1].strip()
    if target.lstrip("-").isdigit():
        try: return bot.get_chat_member(message.chat.id, int(target)).user
        except: return None
    # Note: Telegram Bot API doesn't support resolving @username via get_chat_member natively
    return None

def protected_target(message, target):
    if not target: return False
    if target.id == OWNER_ID:
        bot.reply_to(message, "👑 Owner ko target nahi kiya ja sakta.")
        return True
    if target.id == message.from_user.id:
        bot.reply_to(message, "❌ Aap khud ko target nahi kar sakte.")
        return True
    if target.is_bot:
        bot.reply_to(message, "🤖 Bot ko target nahi kiya ja sakta.")
        return True
    return False

# ============================================================
# 🔨 MODERATION COMMANDS
# ============================================================
@bot.message_handler(commands=["ban", "unban", "kick", "mute", "unmute", "warn", "unwarn", "purge", "pin", "unpin"])
def moderation_handler(message):
    if not is_owner_or_admin(message):
        permission_denied(message)
        return
    
    cmd = message.text.split()[0].lower()
    target = get_target_user(message)

    if cmd in ["/ban", "/kick", "/mute", "/warn"] and protected_target(message, target): return

    try:
        if cmd == "/ban":
            if not target: return bot.reply_to(message, "🔨 Reply to user or provide ID to ban.")
            bot.ban_chat_member(message.chat.id, target.id)
            bot.send_message(message.chat.id, f"🔨 <b>USER BANNED</b>\n👤 {target.first_name}\n👮 Action By: {message.from_user.first_name}")
        
        elif cmd == "/unban":
            if not target: return bot.reply_to(message, "✅ Reply to user or provide ID to unban.")
            bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
            bot.send_message(message.chat.id, f"✅ <b>USER UNBANNED</b>\n👤 {target.first_name}")

        elif cmd == "/kick":
            if not target: return bot.reply_to(message, "👢 Reply to member to kick.")
            bot.ban_chat_member(message.chat.id, target.id)
            bot.unban_chat_member(message.chat.id, target.id)
            bot.send_message(message.chat.id, f"👢 <b>USER KICKED</b>\n👤 {target.first_name}")

        elif cmd == "/mute":
            if not target: return bot.reply_to(message, "🔇 Reply to mute.")
            parts = message.text.split()
            mins = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 30
            until = datetime.now() + timedelta(minutes=max(1, min(mins, 10080)))
            bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
            bot.send_message(message.chat.id, f"🔇 <b>USER MUTED</b>\n👤 {target.first_name}\n⏱️ Duration: {mins} mins")

        elif cmd == "/unmute":
            if not target: return bot.reply_to(message, "🔊 Reply to unmute.")
            bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(can_send_messages=True, can_send_other_messages=True))
            bot.send_message(message.chat.id, f"🔊 <b>USER UNMUTED</b>\n👤 {target.first_name}")

        elif cmd == "/warn":
            if not target: return bot.reply_to(message, "⚠️ Reply to warn.")
            row = db.execute("SELECT warnings FROM warnings WHERE chat_id = ? AND user_id = ?", (message.chat.id, target.id)).fetchone()
            count = (row["warnings"] if row else 0) + 1
            with db_lock:
                db.execute("INSERT INTO warnings (chat_id, user_id, warnings) VALUES (?, ?, ?) ON CONFLICT(chat_id, user_id) DO UPDATE SET warnings = ?", (message.chat.id, target.id, count, count))
                db.commit()
            if count >= 3:
                bot.ban_chat_member(message.chat.id, target.id)
                with db_lock:
                    db.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (message.chat.id, target.id))
                    db.commit()
                bot.send_message(message.chat.id, f"🔨 <b>AUTO BAN</b>\n👤 {target.first_name}\n⚠️ Warnings: 3/3")
            else:
                bot.send_message(message.chat.id, f"⚠️ <b>WARNING ISSUED</b>\n👤 {target.first_name}\n⚠️ Warnings: {count}/3")

        elif cmd == "/purge":
            if not message.reply_to_message: return bot.reply_to(message, "🧹 Reply to a message to purge.")
            count = int(message.text.split()[1]) if len(message.text.split()) > 1 and message.text.split()[1].isdigit() else 10
            for msg_id in range(message.reply_to_message.message_id, message.reply_to_message.message_id + min(100, count) + 1):
                try: bot.delete_message(message.chat.id, msg_id)
                except: pass
            bot.send_message(message.chat.id, "🧹 <b>PURGE COMPLETE</b>")

    except Exception as e:
        bot.reply_to(message, f"❌ Action failed.\n<code>{e}</code>")

# ============================================================
# ⚙️ AUTOMOD & WELCOME
# ============================================================
def get_group_setting(chat_id, column):
    row = db.execute(f"SELECT {column} FROM groups WHERE chat_id = ?", (chat_id,)).fetchone()
    return row[column] if row else 0

@bot.message_handler(commands=["antispam", "antiflood", "welcome", "goodbye"])
def toggle_settings(message):
    if not is_owner_or_admin(message): return
    col = message.text.split()[0][1:]
    if col == "welcome": col = "welcome_enabled"
    if col == "goodbye": col = "goodbye_enabled"
    
    current = get_group_setting(message.chat.id, col)
    new_status = 0 if current else 1
    with db_lock:
        db.execute(f"UPDATE groups SET {col} = ? WHERE chat_id = ?", (new_status, message.chat.id))
        db.commit()
    bot.reply_to(message, f"⚙️ {col.upper()} is now {'ON' if new_status else 'OFF'}.")

@bot.message_handler(content_types=["new_chat_members"])
def new_member_welcome(message):
    if message.chat.type not in ["group", "supergroup"] or not get_group_setting(message.chat.id, "welcome_enabled"): return
    row = db.execute("SELECT welcome_text FROM groups WHERE chat_id = ?", (message.chat.id,)).fetchone()
    custom_text = row["welcome_text"] if row and row["welcome_text"] else "👋 Welcome {name} to {group}!"
    for user in message.new_chat_members:
        text = custom_text.replace("{name}", user.first_name).replace("{group}", message.chat.title)
        bot.send_message(message.chat.id, text)

# Bug Fix: Completed the member_goodbye function
@bot.message_handler(content_types=["left_chat_member"])
def member_goodbye(message):
    if message.chat.type not in ["group", "supergroup"] or not get_group_setting(message.chat.id, "goodbye_enabled"): return
    bot.send_message(message.chat.id, f"🚪 Alvida, <b>{message.left_chat_member.first_name}</b>! 👋")

# ============================================================
# 🎮 MINI GAMES
# ============================================================
@bot.message_handler(commands=["dice", "coin", "rps", "games"])
def fun_games(message):
    cmd = message.text.split()[0].lower()
    if cmd == "/dice":
        bot.send_message(message.chat.id, f"🎲 Result: <b>{random.randint(1, 6)}</b>")
    elif cmd == "/coin":
        bot.send_message(message.chat.id, f"🪙 Result: <b>{random.choice(['HEADS', 'TAILS'])}</b>")
    elif cmd == "/rps":
        parts = message.text.split()
        if len(parts) < 2 or parts[1].lower() not in ["rock", "paper", "scissors"]:
            return bot.reply_to(message, "✊ Use: /rps rock | paper | scissors")
        bot_choice = random.choice(["rock", "paper", "scissors"])
        user_choice = parts[1].lower()
        res = "🤝 DRAW!" if user_choice == bot_choice else ("🏆 YOU WIN!" if (user_choice=="rock" and bot_choice=="scissors") or (user_choice=="paper" and bot_choice=="rock") or (user_choice=="scissors" and bot_choice=="paper") else "🤖 BOT WINS!")
        bot.send_message(message.chat.id, f"👤 You: {user_choice.title()}\n🤖 Bot: {bot_choice.title()}\n🎯 {res}")

# ============================================================
# 📊 PROFILES & XP (Analytics Tracker)
# ============================================================
@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and not m.text.startswith("/"))
def analytics_tracker_main(message):
    try:
        now = int(time.time())
        db.execute("INSERT INTO message_stats (chat_id, user_id, timestamp) VALUES (?, ?, ?)", (message.chat.id, message.from_user.id, now))
        db.execute("INSERT OR IGNORE INTO profiles (chat_id, user_id, xp, level, messages, coins) VALUES (?, ?, 0, 1, 0, 0)", (message.chat.id, message.from_user.id))
        db.execute("UPDATE profiles SET xp = xp + 5, messages = messages + 1 WHERE chat_id = ? AND user_id = ?", (message.chat.id, message.from_user.id))
        db.commit()
    except: pass

@bot.message_handler(commands=["profile", "id"])
def basic_info(message):
    bot.reply_to(message, f"🆔 <b>INFO</b>\n👤 {message.from_user.first_name}\n🆔 <code>{message.from_user.id}</code>\n💬 Chat ID: <code>{message.chat.id}</code>")

# ============================================================
# 👑 OWNER COMMANDS
# ============================================================
@bot.message_handler(commands=["broadcast", "restart"])
def owner_cmds(message):
    if message.from_user.id != OWNER_ID: return bot.reply_to(message, "🚫 Owner only.")
    cmd = message.text.split()[0].lower()
    if cmd == "/broadcast":
        text = message.text.partition(" ")[2]
        rows = db.execute("SELECT user_id FROM users").fetchall()
        sent = 0
        for r in rows:
            try:
                bot.send_message(r["user_id"], f"📢 <b>BROADCAST</b>\n\n{text}")
                sent += 1
            except: pass
        bot.reply_to(message, f"✅ Sent to {sent} users.")
    elif cmd == "/restart":
        bot.reply_to(message, "🔄 Restarting...")
        os.execl(sys.executable, sys.executable, *sys.argv)

# ============================================================
# 🚀 START BOT (ONLY ONCE AT THE END)
# ============================================================
if __name__ == "__main__":
    print("======================================")
    print("🌌 REALMX HELPER BOT STARTED")
    print(f"👑 OWNER: {OWNER_ID}")
    print(f"🤖 BOT: @{BOT_USERNAME}")
    print("🟢 Polling started...")
    print("======================================")
    
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
