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

# ============================================================
# 🌌 REALMX HELPER — PART B
# 🛡️ GROUP MODERATION + STAFF MANAGEMENT
# ============================================================


# ============================================================
# 🎯 TARGET USER HELPER
# ============================================================

def get_target_user(message):

    # Reply se target
    if message.reply_to_message:
        return message.reply_to_message.from_user

    # Username / ID se target
    parts = message.text.split()

    if len(parts) < 2:
        return None

    target = parts[1].strip()

    # Numeric ID
    if target.lstrip("-").isdigit():

        try:
            user_id = int(target)

            member = bot.get_chat_member(
                message.chat.id,
                user_id
            )

            return member.user

        except Exception:
            return None

    # @username
    if target.startswith("@"):

        try:

            member = bot.get_chat_member(
                message.chat.id,
                target
            )

            return member.user

        except Exception:
            return None

    return None


# ============================================================
# 🔐 MODERATION PERMISSION
# ============================================================

def moderation_access(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        return False

    return is_owner_or_admin(message)


# ============================================================
# 🚫 BOT / OWNER PROTECTION
# ============================================================

def protected_target(message, target):

    if not target:
        return False

    if target.id == OWNER_ID:
        bot.reply_to(
            message,
            "👑 Owner ko target nahi kiya ja sakta."
        )
        return True

    if target.id == message.from_user.id:
        bot.reply_to(
            message,
            "❌ Aap khud ko target nahi kar sakte."
        )
        return True

    if target.is_bot:
        bot.reply_to(
            message,
            "🤖 Bot ko target nahi kiya ja sakta."
        )
        return True

    return False


# ============================================================
# 🔨 /BAN
# ============================================================

@bot.message_handler(commands=["ban"])
def ban_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:
        bot.reply_to(
            message,
            """
🔨 <b>BAN USER</b>

Kisi member ke message ko reply karke:

<code>/ban</code>

Ya:

<code>/ban @username</code>
"""
        )
        return

    if protected_target(message, target):
        return

    try:

        bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        bot.send_message(
            message.chat.id,
            f"""
🔨 <b>USER BANNED</b>

👤 User:
{target.first_name}

🆔 ID:
<code>{target.id}</code>

👮 Action By:
{message.from_user.first_name}

🔒 Permanent Ban
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Ban failed.\n<code>{e}</code>"
        )


# ============================================================
# ✅ /UNBAN
# ============================================================

@bot.message_handler(commands=["unban"])
def unban_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            """
✅ <b>UNBAN USER</b>

Use:

<code>/unban @username</code>

Ya User ID:
<code>/unban 123456789</code>
"""
        )
        return

    try:

        bot.unban_chat_member(
            message.chat.id,
            target.id,
            only_if_banned=True
        )

        bot.send_message(
            message.chat.id,
            f"""
✅ <b>USER UNBANNED</b>

👤 {target.first_name}

🆔 <code>{target.id}</code>

🌌 REALMX SECURITY
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Unban failed.\n<code>{e}</code>"
        )


# ============================================================
# 👢 /KICK
# ============================================================

@bot.message_handler(commands=["kick"])
def kick_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "👢 Member ke message ko reply karke <code>/kick</code> use karein."
        )
        return

    if protected_target(message, target):
        return

    try:

        # Kick = ban + immediately unban
        bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        bot.unban_chat_member(
            message.chat.id,
            target.id
        )

        bot.send_message(
            message.chat.id,
            f"""
👢 <b>USER KICKED</b>

👤 {target.first_name}

🆔 <code>{target.id}</code>

👮 By:
{message.from_user.first_name}
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Kick failed.\n<code>{e}</code>"
        )


# ============================================================
# 🔇 /MUTE [MINUTES]
# ============================================================

@bot.message_handler(commands=["mute"])
def mute_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            """
🔇 <b>MUTE USER</b>

Reply karke:

<code>/mute 30</code>

Default: 30 minutes
"""
        )
        return

    if protected_target(message, target):
        return

    parts = message.text.split()

    minutes = 30

    if len(parts) >= 2:

        # Agar reply + /mute 30 hai
        try:

            if parts[1].isdigit():
                minutes = int(parts[1])

        except:
            minutes = 30

    if minutes < 1:
        minutes = 1

    if minutes > 10080:
        minutes = 10080

    until_date = datetime.now() + timedelta(
        minutes=minutes
    )

    permissions = types.ChatPermissions(
        can_send_messages=False
    )

    try:

        bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions,
            until_date=until_date
        )

        bot.send_message(
            message.chat.id,
            f"""
🔇 <b>USER MUTED</b>

👤 {target.first_name}

⏱️ Duration:
<b>{minutes} minutes</b>

👮 By:
{message.from_user.first_name}
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Mute failed.\n<code>{e}</code>"
        )


# ============================================================
# 🔊 /UNMUTE
# ============================================================

@bot.message_handler(commands=["unmute"])
def unmute_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "🔊 Muted member ke message ko reply karke <code>/unmute</code> use karein."
        )
        return

    try:

        permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )

        bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions
        )

        bot.send_message(
            message.chat.id,
            f"""
🔊 <b>USER UNMUTED</b>

👤 {target.first_name}

✅ Messaging permissions restored.
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Unmute failed.\n<code>{e}</code>"
        )


# ============================================================
# ⚠️ /WARN
# 3 WARNINGS = AUTO BAN
# ============================================================

@bot.message_handler(commands=["warn"])
def warn_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "⚠️ Member ke message ko reply karke <code>/warn</code> use karein."
        )
        return

    if protected_target(message, target):
        return

    row = db.execute("""
        SELECT warnings
        FROM warnings
        WHERE chat_id = ?
        AND user_id = ?
    """, (
        message.chat.id,
        target.id
    )).fetchone()

    current = row["warnings"] if row else 0
    new_count = current + 1

    with db_lock:

        db.execute("""
            INSERT INTO warnings (
                chat_id,
                user_id,
                warnings
            )
            VALUES (?, ?, ?)

            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET
                warnings = excluded.warnings
        """, (
            message.chat.id,
            target.id,
            new_count
        ))

        db.commit()

    # Auto Ban at 3
    if new_count >= 3:

        try:

            bot.ban_chat_member(
                message.chat.id,
                target.id
            )

            with db_lock:

                db.execute("""
                    DELETE FROM warnings
                    WHERE chat_id = ?
                    AND user_id = ?
                """, (
                    message.chat.id,
                    target.id
                ))

                db.commit()

            bot.send_message(
                message.chat.id,
                f"""
🔨 <b>AUTO BAN</b>

👤 {target.first_name}

⚠️ Warnings reached:
<b>3/3</b>

🔒 User has been banned automatically.
"""
            )

        except Exception as e:

            bot.reply_to(
                message,
                f"❌ Auto-ban failed.\n<code>{e}</code>"
            )

        return

    bot.send_message(
        message.chat.id,
        f"""
⚠️ <b>WARNING ISSUED</b>

👤 User:
{target.first_name}

⚠️ Warnings:
<b>{new_count}/3</b>

🚨 3 warnings = Auto Ban
"""
    )


# ============================================================
# 🟢 /UNWARN
# ============================================================

@bot.message_handler(commands=["unwarn"])
def unwarn_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "🟢 Member ke message ko reply karke <code>/unwarn</code> use karein."
        )
        return

    row = db.execute("""
        SELECT warnings
        FROM warnings
        WHERE chat_id = ?
        AND user_id = ?
    """, (
        message.chat.id,
        target.id
    )).fetchone()

    current = row["warnings"] if row else 0

    if current <= 0:

        bot.reply_to(
            message,
            "ℹ️ Is user ki koi warning nahi hai."
        )
        return

    new_count = current - 1

    with db_lock:

        if new_count == 0:

            db.execute("""
                DELETE FROM warnings
                WHERE chat_id = ?
                AND user_id = ?
            """, (
                message.chat.id,
                target.id
            ))

        else:

            db.execute("""
                UPDATE warnings
                SET warnings = ?
                WHERE chat_id = ?
                AND user_id = ?
            """, (
                new_count,
                message.chat.id,
                target.id
            ))

        db.commit()

    bot.send_message(
        message.chat.id,
        f"""
🟢 <b>WARNING REMOVED</b>

👤 {target.first_name}

⚠️ Current Warnings:
<b>{new_count}/3</b>
"""
    )


# ============================================================
# 🧹 /PURGE [COUNT]
# ============================================================

@bot.message_handler(commands=["purge"])
def purge_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    if not message.reply_to_message:

        bot.reply_to(
            message,
            """
🧹 <b>PURGE</b>

Kisi message ko reply karke:

<code>/purge 20</code>

1-100 messages delete kar sakte hain.
"""
        )
        return

    parts = message.text.split()

    count = 10

    if len(parts) >= 2:

        try:
            count = int(parts[1])
        except:
            count = 10

    count = max(1, min(count, 100))

    start_id = message.reply_to_message.message_id

    message_ids = list(
        range(
            start_id,
            start_id + count + 1
        )
    )

    deleted = 0

    # Telegram bulk delete ka guarantee nahi,
    # isliye individual deletion with safe handling.
    for msg_id in message_ids:

        try:

            bot.delete_message(
                message.chat.id,
                msg_id
            )

            deleted += 1

        except:
            pass

    # Command message bhi delete
    try:
        bot.delete_message(
            message.chat.id,
            message.message_id
        )
    except:
        pass

    confirm = bot.send_message(
        message.chat.id,
        f"""
🧹 <b>PURGE COMPLETE</b>

🗑️ Deleted:
<b>{deleted}</b> messages

🌌 REALMX CLEANUP
"""
    )

    time.sleep(3)

    try:
        bot.delete_message(
            message.chat.id,
            confirm.message_id
        )
    except:
        pass


# ============================================================
# 📌 /PIN
# ============================================================

@bot.message_handler(commands=["pin"])
def pin_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    if not message.reply_to_message:

        bot.reply_to(
            message,
            "📌 Jis message ko pin karna hai usko reply karke <code>/pin</code> use karein."
        )
        return

    try:

        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id,
            disable_notification=True
        )

        bot.send_message(
            message.chat.id,
            f"""
📌 <b>MESSAGE PINNED</b>

👮 By:
{message.from_user.first_name}
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Pin failed.\n<code>{e}</code>"
        )


# ============================================================
# 📍 /UNPIN
# ============================================================

@bot.message_handler(commands=["unpin"])
def unpin_command(message):

    if not moderation_access(message):
        permission_denied(message)
        return

    try:

        if message.reply_to_message:

            bot.unpin_chat_message(
                message.chat.id,
                message.reply_to_message.message_id
            )

        else:

            bot.unpin_chat_message(
                message.chat.id
            )

        bot.send_message(
            message.chat.id,
            """
📍 <b>MESSAGE UNPINNED</b>

🌌 REALMX SECURITY
"""
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Unpin failed.\n<code>{e}</code>"
        )


# ============================================================
# 👑 STAFF DATABASE HELPER
# ============================================================

def set_staff_rank(chat_id, user_id, rank):

    with db_lock:

        db.execute("""
            INSERT INTO staff (
                chat_id,
                user_id,
                rank
            )
            VALUES (?, ?, ?)

            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET
                rank = excluded.rank
        """, (
            chat_id,
            user_id,
            rank
        ))

        db.commit()


def remove_staff_rank(chat_id, user_id):

    with db_lock:

        db.execute("""
            DELETE FROM staff
            WHERE chat_id = ?
            AND user_id = ?
        """, (
            chat_id,
            user_id
        ))

        db.commit()


# ============================================================
# 🥉 /PROMOTE1 — REALM KEEPER
# ============================================================

@bot.message_handler(commands=["promote1"])
def promote1_command(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "🥉 Member ke message ko reply karke <code>/promote1</code> use karein."
        )
        return

    if target.id == OWNER_ID:

        bot.reply_to(
            message,
            "👑 Owner ko staff rank dene ki zarurat nahi."
        )
        return

    set_staff_rank(
        message.chat.id,
        target.id,
        1
    )

    bot.send_message(
        message.chat.id,
        f"""
🥉 <b>REALM KEEPER</b>

👤 {target.first_name}

🛡️ Rank:
<b>Level 1 — Realm Keeper</b>

✅ Access:
• Warn
• Delete

👑 Assigned by:
{message.from_user.first_name}
"""
    )


# ============================================================
# 🥈 /PROMOTE2 — REALM GUARDIAN
# ============================================================

@bot.message_handler(commands=["promote2"])
def promote2_command(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "🥈 Member ke message ko reply karke <code>/promote2</code> use karein."
        )
        return

    if target.id == OWNER_ID:

        bot.reply_to(
            message,
            "👑 Owner protected hai."
        )
        return

    set_staff_rank(
        message.chat.id,
        target.id,
        2
    )

    bot.send_message(
        message.chat.id,
        f"""
🥈 <b>REALM GUARDIAN</b>

👤 {target.first_name}

🛡️ Rank:
<b>Level 2 — Realm Guardian</b>

✅ Access:
• Warn
• Delete
• Mute
• Pin

👑 Assigned by:
{message.from_user.first_name}
"""
    )


# ============================================================
# 🥇 /PROMOTE3 — REALM COMMANDER
# ============================================================

@bot.message_handler(commands=["promote3"])
def promote3_command(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "🥇 Member ke message ko reply karke <code>/promote3</code> use karein."
        )
        return

    if target.id == OWNER_ID:

        bot.reply_to(
            message,
            "👑 Owner protected hai."
        )
        return

    set_staff_rank(
        message.chat.id,
        target.id,
        3
    )

    bot.send_message(
        message.chat.id,
        f"""
🥇 <b>REALM COMMANDER</b>

👤 {target.first_name}

🛡️ Rank:
<b>Level 3 — Realm Commander</b>

✅ Full Staff Access

👑 Assigned by:
{message.from_user.first_name}
"""
    )


# ============================================================
# ⬇️ /DEMOTE
# ============================================================

@bot.message_handler(commands=["demote"])
def demote_command(message):

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        permission_denied(message)
        return

    target = get_target_user(message)

    if not target:

        bot.reply_to(
            message,
            "⬇️ Staff member ke message ko reply karke <code>/demote</code> use karein."
        )
        return

    if target.id == OWNER_ID:

        bot.reply_to(
            message,
            "👑 Owner ko demote nahi kiya ja sakta."
        )
        return

    remove_staff_rank(
        message.chat.id,
        target.id
    )

    bot.send_message(
        message.chat.id,
        f"""
⬇️ <b>STAFF RANK REMOVED</b>

👤 {target.first_name}

🛡️ Custom RealmX staff rank removed.

👑 Action By:
{message.from_user.first_name}
"""
        )

# ============================================================
# 🌌 REALMX HELPER — PART C
# ⚙️ AUTOMOD + GROUP SETTINGS
# ============================================================


# ============================================================
# 🔐 GROUP ADMIN CHECK
# ============================================================

def require_group_admin(message):

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein use ho sakti hai."
        )
        return False

    if not is_admin(
        message.chat.id,
        message.from_user.id
    ):
        permission_denied(message)
        return False

    return True


# ============================================================
# 🛡️ GROUP SETTINGS
# ============================================================

def get_group_setting(chat_id, column):

    allowed = [
        "welcome_enabled",
        "goodbye_enabled",
        "antispam",
        "antiflood"
    ]

    if column not in allowed:
        return 0

    row = db.execute(
        f"SELECT {column} FROM groups WHERE chat_id = ?",
        (chat_id,)
    ).fetchone()

    if not row:
        return 0

    return row[column] or 0


def set_group_setting(chat_id, column, value):

    allowed = [
        "welcome_enabled",
        "goodbye_enabled",
        "antispam",
        "antiflood"
    ]

    if column not in allowed:
        return

    with db_lock:

        db.execute(
            f"""
            UPDATE groups
            SET {column} = ?
            WHERE chat_id = ?
            """,
            (
                int(value),
                chat_id
            )
        )

        db.commit()


# ============================================================
# 🚫 /ANTISPAM
# ============================================================

@bot.message_handler(commands=["antispam"])
def antispam_command(message):

    if not require_group_admin(message):
        return

    current = get_group_setting(
        message.chat.id,
        "antispam"
    )

    new_status = 0 if current else 1

    set_group_setting(
        message.chat.id,
        "antispam",
        new_status
    )

    if new_status:

        bot.reply_to(
            message,
            """
🛡️ <b>ANTI-SPAM ENABLED</b>

🚫 Spam protection is now <b>ON</b>.

🌌 REALMX SECURITY
"""
        )

    else:

        bot.reply_to(
            message,
            """
⚠️ <b>ANTI-SPAM DISABLED</b>

🚫 Spam protection is now <b>OFF</b>.
"""
        )


# ============================================================
# 🌊 /ANTIFLOOD
# ============================================================

@bot.message_handler(commands=["antiflood"])
def antiflood_command(message):

    if not require_group_admin(message):
        return

    current = get_group_setting(
        message.chat.id,
        "antiflood"
    )

    new_status = 0 if current else 1

    set_group_setting(
        message.chat.id,
        "antiflood",
        new_status
    )

    if new_status:

        bot.reply_to(
            message,
            """
🌊 <b>ANTI-FLOOD ENABLED</b>

🛡️ Rapid message protection is now <b>ON</b>.
"""
        )

    else:

        bot.reply_to(
            message,
            """
⚠️ <b>ANTI-FLOOD DISABLED</b>

🌊 Flood protection is now <b>OFF</b>.
"""
        )


# ============================================================
# 📝 /BLOCKLIST
#
# /blocklist
# /blocklist add badword
# /blocklist remove badword
# ============================================================

@bot.message_handler(commands=["blocklist"])
def blocklist_command(message):

    if not require_group_admin(message):
        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) == 1:

        rows = db.execute(
            """
            SELECT word
            FROM blocklist
            WHERE chat_id = ?
            ORDER BY word
            """,
            (message.chat.id,)
        ).fetchall()

        if not rows:

            bot.reply_to(
                message,
                """
📝 <b>BLOCKLIST</b>

Blocklist empty hai.

Add karne ke liye:
<code>/blocklist add word</code>
"""
            )

            return

        words = [
            f"• <code>{row['word']}</code>"
            for row in rows
        ]

        bot.reply_to(
            message,
            """
📝 <b>BLOCKLIST</b>

""" + "\n".join(words)
        )

        return

    action = parts[1].lower()

    if action not in [
        "add",
        "remove"
    ]:

        bot.reply_to(
            message,
            """
📝 Usage:

<code>/blocklist add word</code>
<code>/blocklist remove word</code>
"""
        )

        return

    if len(parts) < 3 or not parts[2].strip():

        bot.reply_to(
            message,
            "❌ Word specify karein."
        )

        return

    word = parts[2].strip().lower()

    if len(word) > 100:

        bot.reply_to(
            message,
            "❌ Word bahut lamba hai."
        )

        return

    if action == "add":

        with db_lock:

            db.execute(
                """
                INSERT OR IGNORE INTO blocklist (
                    chat_id,
                    word
                )
                VALUES (?, ?)
                """,
                (
                    message.chat.id,
                    word
                )
            )

            db.commit()

        bot.reply_to(
            message,
            f"""
🚫 <b>BLOCKED WORD ADDED</b>

📝 Word:
<code>{word}</code>
"""
        )

    else:

        with db_lock:

            cursor = db.execute(
                """
                DELETE FROM blocklist
                WHERE chat_id = ?
                AND word = ?
                """,
                (
                    message.chat.id,
                    word
                )
            )

            db.commit()

        if cursor.rowcount:

            bot.reply_to(
                message,
                f"""
✅ <b>WORD REMOVED</b>

<code>{word}</code>
"""
            )

        else:

            bot.reply_to(
                message,
                "ℹ️ Ye word blocklist mein nahi tha."
            )


# ============================================================
# 👋 /WELCOME
# ============================================================

@bot.message_handler(commands=["welcome"])
def welcome_command(message):

    if not require_group_admin(message):
        return

    current = get_group_setting(
        message.chat.id,
        "welcome_enabled"
    )

    new_status = 0 if current else 1

    set_group_setting(
        message.chat.id,
        "welcome_enabled",
        new_status
    )

    if new_status:

        bot.reply_to(
            message,
            """
👋 <b>WELCOME ENABLED</b>

New members ke liye welcome system <b>ON</b> hai.
"""
        )

    else:

        bot.reply_to(
            message,
            """
⚠️ <b>WELCOME DISABLED</b>

Welcome system <b>OFF</b> hai.
"""
        )


# ============================================================
# 🚪 /GOODBYE
# ============================================================

@bot.message_handler(commands=["goodbye"])
def goodbye_command(message):

    if not require_group_admin(message):
        return

    current = get_group_setting(
        message.chat.id,
        "goodbye_enabled"
    )

    new_status = 0 if current else 1

    set_group_setting(
        message.chat.id,
        "goodbye_enabled",
        new_status
    )

    if new_status:

        bot.reply_to(
            message,
            """
🚪 <b>GOODBYE ENABLED</b>

Leaving members ke liye goodbye system <b>ON</b> hai.
"""
        )

    else:

        bot.reply_to(
            message,
            """
⚠️ <b>GOODBYE DISABLED</b>

Goodbye system <b>OFF</b> hai.
"""
        )


# ============================================================
# ✍️ /SETWELCOME
#
# /setwelcome Welcome {name} to {group}!
# ============================================================

@bot.message_handler(commands=["setwelcome"])
def setwelcome_command(message):

    if not require_group_admin(message):
        return

    text = message.text.partition(" ")[2].strip()

    if not text:

        bot.reply_to(
            message,
            """
✍️ <b>SET WELCOME</b>

Example:

<code>/setwelcome 🌌 Welcome {name} to {group}!</code>

Available:
{name}
{group}
"""
        )

        return

    if len(text) > 1000:

        bot.reply_to(
            message,
            "❌ Welcome message maximum 1000 characters ho sakta hai."
        )

        return

    with db_lock:

        # Existing schema mein welcome text column nahi hai,
        # isliye safely add karne ki koshish.
        try:

            db.execute(
                "ALTER TABLE groups ADD COLUMN welcome_text TEXT DEFAULT ''"
            )

        except sqlite3.OperationalError:
            pass

        db.execute(
            """
            UPDATE groups
            SET welcome_text = ?
            WHERE chat_id = ?
            """,
            (
                text,
                message.chat.id
            )
        )

        db.commit()

    bot.reply_to(
        message,
        """
✅ <b>WELCOME MESSAGE SAVED</b>

Ab new members ko custom welcome milega.
"""
    )


# ============================================================
# 📜 /SETRULES
# ============================================================

@bot.message_handler(commands=["setrules"])
def setrules_command(message):

    if not require_group_admin(message):
        return

    text = message.text.partition(" ")[2].strip()

    if not text:

        bot.reply_to(
            message,
            """
📜 <b>SET RULES</b>

Example:

<code>/setrules
1. No spam
2. Respect everyone
3. No abuse
</code>
"""
        )

        return

    if len(text) > 4000:

        bot.reply_to(
            message,
            "❌ Rules maximum 4000 characters ho sakte hain."
        )

        return

    with db_lock:

        db.execute(
            """
            UPDATE groups
            SET rules = ?
            WHERE chat_id = ?
            """,
            (
                text,
                message.chat.id
            )
        )

        db.commit()

    bot.reply_to(
        message,
        """
📜 <b>GROUP RULES SAVED</b>

Rules successfully update ho gaye.
"""
    )


# ============================================================
# 📖 /RULES
# ============================================================

@bot.message_handler(commands=["rules"])
def rules_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "📜 Group rules dekhne ke liye group mein command use karein."
        )

        return

    row = db.execute(
        """
        SELECT rules
        FROM groups
        WHERE chat_id = ?
        """,
        (
            message.chat.id,
        )
    ).fetchone()

    rules = row["rules"] if row else ""

    if not rules:

        rules = """
1️⃣ Respect everyone.
2️⃣ No spam.
3️⃣ No abuse.
4️⃣ Follow group admins.
"""

    bot.reply_to(
        message,
        f"""
📜 <b>{message.chat.title} — RULES</b>

{rules}

━━━━━━━━━━━━━━━━━━
🌌 REALMX HELPER
"""
    )


# ============================================================
# ⚙️ /FILTER
#
# /filter hello Hello {name}!
# ============================================================

@bot.message_handler(commands=["filter"])
def filter_command(message):

    if not require_group_admin(message):
        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 3:

        bot.reply_to(
            message,
            """
⚙️ <b>SET FILTER</b>

Example:

<code>/filter hello Hello {name}! 🌌</code>

Keyword ke baad auto-reply likhein.
"""
        )

        return

    keyword = parts[1].strip().lower()
    reply_text = parts[2].strip()

    if not keyword or not reply_text:

        bot.reply_to(
            message,
            "❌ Keyword aur reply dono required hain."
        )

        return

    if len(keyword) > 100:

        bot.reply_to(
            message,
            "❌ Keyword maximum 100 characters ka ho sakta hai."
        )

        return

    if len(reply_text) > 2000:

        bot.reply_to(
            message,
            "❌ Reply maximum 2000 characters ka ho sakta hai."
        )

        return

    with db_lock:

        db.execute(
            """
            INSERT INTO filters (
                chat_id,
                keyword,
                reply
            )
            VALUES (?, ?, ?)

            ON CONFLICT(chat_id, keyword)
            DO UPDATE SET
                reply = excluded.reply
            """,
            (
                message.chat.id,
                keyword,
                reply_text
            )
        )

        db.commit()

    bot.reply_to(
        message,
        f"""
⚙️ <b>FILTER SAVED</b>

🔑 Keyword:
<code>{keyword}</code>

💬 Auto Reply:
{reply_text}
"""
    )


# ============================================================
# ❌ /STOPFILTER
# ============================================================

@bot.message_handler(commands=["stopfilter"])
def stopfilter_command(message):

    if not require_group_admin(message):
        return

    parts = message.text.split(
        maxsplit=1
    )

    if len(parts) < 2:

        bot.reply_to(
            message,
            """
❌ Example:

<code>/stopfilter hello</code>
"""
        )

        return

    keyword = parts[1].strip().lower()

    with db_lock:

        cursor = db.execute(
            """
            DELETE FROM filters
            WHERE chat_id = ?
            AND keyword = ?
            """,
            (
                message.chat.id,
                keyword
            )
        )

        db.commit()

    if cursor.rowcount:

        bot.reply_to(
            message,
            f"""
✅ <b>FILTER REMOVED</b>

🔑 Keyword:
<code>{keyword}</code>
"""
        )

    else:

        bot.reply_to(
            message,
            "ℹ️ Ye filter exist nahi karta."
        )


# ============================================================
# 👋 NEW MEMBER WELCOME
# ============================================================

@bot.message_handler(
    content_types=["new_chat_members"]
)
def new_member_welcome(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        return

    if not get_group_setting(
        message.chat.id,
        "welcome_enabled"
    ):
        return

    row = db.execute(
        """
        SELECT welcome_text
        FROM groups
        WHERE chat_id = ?
        """,
        (
            message.chat.id,
        )
    ).fetchone()

    custom_text = ""

    if row:
        try:
            custom_text = row["welcome_text"] or ""
        except:
            custom_text = ""

    for user in message.new_chat_members:

        name = user.first_name or "User"

        if custom_text:

            text = custom_text.replace(
                "{name}",
                name
            ).replace(
                "{group}",
                message.chat.title or "Group"
            )

        else:

            text = f"""
🌌 <b>WELCOME TO REALMX</b>

👋 Welcome <b>{name}</b>!

🛡️ Please read the group rules.
💬 Enjoy your stay!

🌌 REALMX HELPER
"""

        bot.send_message(
            message.chat.id,
            text
        )


# ============================================================
# 🚪 MEMBER LEFT / GOODBYE
# ============================================================

@bot.message_handler(
    content_types=["left_chat_member"]
)
def member_goodbye(message):

    if message.chat.type not in [
        "group",

# ============================================================
# 🌌 REALMX HELPER — PART D
# 📢 TAG & MENTION SYSTEM
# ============================================================


# ============================================================
# 👤 MEMBER COLLECTION
# ============================================================

def get_group_members(chat_id):
    """
    Telegram Bot API arbitrary group ke saare members ki
    complete list directly provide nahi karta.
    Isliye bot sirf un users ko tag karega jinhe database
    ne activity ke through track kiya hai.
    """

    rows = db.execute(
        """
        SELECT DISTINCT user_id
        FROM activity
        WHERE chat_id = ?
        ORDER BY last_seen DESC
        """,
        (chat_id,)
    ).fetchall()

    members = []

    for row in rows:

        try:

            member = bot.get_chat_member(
                chat_id,
                row["user_id"]
            )

            if member.user.is_bot:
                continue

            if member.status in [
                "left",
                "kicked"
            ]:
                continue

            members.append(
                member.user
            )

        except:
            continue

    return members


# ============================================================
# 🛡️ TAG PERMISSION
# ============================================================

def tag_permission(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein use ho sakti hai."
        )
        return False

    if not is_owner_or_admin(message):

        bot.reply_to(
            message,
            """
🔒 <b>TAG ACCESS DENIED</b>

Sirf Admin/Authorized Staff members
tag commands use kar sakte hain.
"""
        )

        return False

    return True


# ============================================================
# 🏷️ MENTION FORMAT
# ============================================================

def mention_user(user):

    name = (
        user.first_name
        or user.username
        or "User"
    )

    # HTML escaping
    name = (
        str(name)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return (
        f'<a href="tg://user?id={user.id}">'
        f'{name}'
        f'</a>'
    )


# ============================================================
# 📦 SPLIT MENTIONS
# Telegram message length limit ko dhyan mein rakhte hue
# mentions ko multiple messages mein bheja jayega.
# ============================================================

def send_mentions(chat_id, users, title):

    if not users:

        bot.send_message(
            chat_id,
            """
📢 <b>NO MEMBERS FOUND</b>

Abhi bot ke activity database mein
koi trackable member nahi mila.
"""
        )

        return

    chunk = []
    current_length = len(title)

    for user in users:

        mention = mention_user(user)

        if (
            current_length
            + len(mention)
            + 2
            > 3500
        ):

            if chunk:

                bot.send_message(
                    chat_id,
                    title
                    + "\n\n"
                    + " ".join(chunk),
                    disable_web_page_preview=True
                )

            chunk = []
            current_length = len(title)

        chunk.append(mention)

        current_length += (
            len(mention) + 1
        )

    if chunk:

        bot.send_message(
            chat_id,
            title
            + "\n\n"
            + " ".join(chunk),
            disable_web_page_preview=True
        )


# ============================================================
# 📢 /ALL
# ============================================================

@bot.message_handler(commands=["all"])
def all_command(message):

    if not tag_permission(message):
        return

    users = get_group_members(
        message.chat.id
    )

    send_mentions(
        message.chat.id,
        users,
        """
📢 <b>REALMX ALL TAG</b>

🌌 Calling active members...
"""
    )


# ============================================================
# 📢 /TAGALL
# ============================================================

@bot.message_handler(commands=["tagall"])
def tagall_command(message):

    if not tag_permission(message):
        return

    users = get_group_members(
        message.chat.id
    )

    send_mentions(
        message.chat.id,
        users,
        """
🌌 <b>REALMX TAGALL</b>

📢 Active members, attention please!
"""
    )


# ============================================================
# 🕵️ /HIDETAG
# ============================================================

@bot.message_handler(commands=["hidetag"])
def hidetag_command(message):

    if not tag_permission(message):
        return

    users = get_group_members(
        message.chat.id
    )

    if not users:

        bot.reply_to(
            message,
            "⚠️ Tag karne ke liye tracked members nahi mile."
        )

        return

    # Telegram mein truly invisible mention possible nahi;
    # zero-width style se compact hidden-looking tag banaya gaya hai.
    mentions = []

    for user in users:

        mentions.append(
            f'<a href="tg://user?id={user.id}">‌</a>'
        )

    text = (
        "🕵️ <b>REALMX HIDDEN TAG</b>\n\n"
        + "".join(mentions)
    )

    try:

        bot.send_message(
            message.chat.id,
            text,
            disable_web_page_preview=True
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"❌ Hidden tag failed.\n<code>{e}</code>"
        )


# ============================================================
# 🛡️ ADMIN LIST
# ============================================================

def get_group_admins(chat_id):

    admins = []

    try:

        result = bot.get_chat_administrators(
            chat_id
        )

        for admin in result:

            if admin.user.is_bot:
                continue

            admins.append(
                admin.user
            )

    except:
        pass

    return admins


# ============================================================
# 👑 /ADMINS
# ============================================================

@bot.message_handler(commands=["admins"])
def admins_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "🛡️ Ye command group mein use karein."
        )

        return

    admins = get_group_admins(
        message.chat.id
    )

    send_mentions(
        message.chat.id,
        admins,
        """
🛡️ <b>REALMX GROUP ADMINS</b>

👑 Group Administration:
"""
    )


# ============================================================
# 🛡️ /TAGADMINS
# ============================================================

@bot.message_handler(commands=["tagadmins"])
def tagadmins_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein hai."
        )

        return

    if not is_owner_or_admin(message):

        bot.reply_to(
            message,
            "🔒 Sirf Admin/Staff use kar sakte hain."
        )

        return

    admins = get_group_admins(
        message.chat.id
    )

    send_mentions(
        message.chat.id,
        admins,
        """
📢 <b>ADMIN ALERT</b>

🛡️ Calling Group Admins...
"""
    )


# ============================================================
# 👑 STAFF MEMBERS
# ============================================================

def get_staff_members(chat_id):

    rows = db.execute(
        """
        SELECT user_id, rank
        FROM staff
        WHERE chat_id = ?
        AND rank > 0
        ORDER BY rank DESC
        """,
        (chat_id,)
    ).fetchall()

    members = []

    for row in rows:

        try:

            member = bot.get_chat_member(
                chat_id,
                row["user_id"]
            )

            if member.user.is_bot:
                continue

            if member.status in [
                "left",
                "kicked"
            ]:
                continue

            members.append(
                (
                    member.user,
                    row["rank"]
                )
            )

        except:
            continue

    return members


# ============================================================
# 🛡️ /STAFF
# ============================================================

@bot.message_handler(commands=["staff"])
def staff_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein use ho sakti hai."
        )

        return

    staff = get_staff_members(
        message.chat.id
    )

    if not staff:

        bot.reply_to(
            message,
            """
🛡️ <b>REALMX STAFF</b>

Abhi koi custom RealmX staff member
assigned nahi hai.
"""
        )

        return

    lines = [
        "🛡️ <b>REALMX STAFF</b>\n"
    ]

    rank_names = {
        1: "🥉 Realm Keeper",
        2: "🥈 Realm Guardian",
        3: "🥇 Realm Commander"
    }

    for user, rank in staff:

        lines.append(
            f"{mention_user(user)} — "
            f"<b>{rank_names.get(rank, 'Staff')}</b>"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
        disable_web_page_preview=True
    )


# ============================================================
# 📢 /TAGSTAFF
# ============================================================

@bot.message_handler(commands=["tagstaff"])
def tagstaff_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein hai."
        )

        return

    if not is_owner_or_admin(message):

        bot.reply_to(
            message,
            "🔒 Sirf Admin/Staff use kar sakte hain."
        )

        return

    staff = get_staff_members(
        message.chat.id
    )

    if not staff:

        bot.reply_to(
            message,
            "🛡️ Koi RealmX staff member nahi mila."
        )

        return

    users = [
        user
        for user, rank in staff
    ]

    send_mentions(
        message.chat.id,
        users,
        """
🛡️ <b>REALMX STAFF ALERT</b>

📢 Staff members, please check the group.
"""
    )


# ============================================================
# 🤖 GROUP BOTS
# ============================================================

def get_group_bots(chat_id):

    rows = db.execute(
        """
        SELECT DISTINCT user_id
        FROM activity
        WHERE chat_id = ?
        """,
        (chat_id,)
    ).fetchall()

    bots = []

    for row in rows:

        try:

            member = bot.get_chat_member(
                chat_id,
                row["user_id"]
            )

            if member.user.is_bot:

                bots.append(
                    member.user
                )

        except:
            continue

    return bots


# ============================================================
# 🤖 /TAGBOTS
# ============================================================

@bot.message_handler(commands=["tagbots"])
def tagbots_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein hai."
        )

        return

    if not is_owner_or_admin(message):

        bot.reply_to(
            message,
            "🔒 Sirf Admin/Staff use kar sakte hain."
        )

        return

    bots = get_group_bots(
        message.chat.id
    )

    if not bots:

        bot.reply_to(
            message,
            """
🤖 <b>GROUP BOTS</b>

Abhi koi tracked bot nahi mila.
"""
        )

        return

    send_mentions(
        message.chat.id,
        bots,
        """
🤖 <b>REALMX BOT ALERT</b>

Calling group bots...
"""
    )


# ============================================================
# 📊 TAG STATUS
# ============================================================

@bot.message_handler(commands=["tagstatus"])
def tagstatus_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Group mein use karein."
        )

        return

    members = get_group_members(
        message.chat.id
    )

    admins = get_group_admins(
        message.chat.id
    )

    staff = get_staff_members(
        message.chat.id
    )

    bots = get_group_bots(
        message.chat.id
    )

    bot.send_message(
        message.chat.id,
        f"""
📊 <b>REALMX TAG STATUS</b>

👥 Tracked Members:
<b>{len(members)}</b>

🛡️ Admins:
<b>{len(admins)}</b>

👑 RealmX Staff:
<b>{len(staff)}</b>

🤖 Tracked Bots:
<b>{len(bots)}</b>

━━━━━━━━━━━━━━━━━━
🌌 REALMX HELPER
"""
                )        

# ============================================================
# 🌌 REALMX HELPER — PART E
# 🛠️ GENERAL UTILITY + SOCIAL
# ============================================================

# ============================================================
# 🆔 /ID
# ============================================================

@bot.message_handler(commands=["id"])
def id_command(message):

    user = message.from_user

    text = f"""
🆔 <b>REALMX ID CARD</b>

👤 Name: <b>{user.first_name or "Unknown"}</b>
🆔 User ID: <code>{user.id}</code>
"""

    if user.username:
        text += f"📛 Username: @{user.username}\n"

    text += f"💬 Chat ID: <code>{message.chat.id}</code>"

    bot.reply_to(message, text)


# ============================================================
# 👤 /INFO
# ============================================================

@bot.message_handler(commands=["info"])
def info_command(message):

    user = message.from_user

    username = (
        f"@{user.username}"
        if user.username
        else "Not Set"
    )

    bot.reply_to(
        message,
        f"""
💎 <b>REALMX USER INFO</b>

👤 Name: <b>{user.first_name or "Unknown"}</b>
📛 Username: <b>{username}</b>
🆔 ID: <code>{user.id}</code>

🌌 Account information loaded successfully.
"""
    )


# ============================================================
# 🏓 /PING
# ============================================================

@bot.message_handler(commands=["ping"])
def ping_command(message):

    start_time = time.time()

    msg = bot.reply_to(
        message,
        "🏓 <b>Checking REALMX...</b>"
    )

    latency = round(
        (time.time() - start_time) * 1000,
        2
    )

    bot.edit_message_text(
        f"""
💎 <b>REALMX PING</b>

🏓 Status: 🟢 Online
⚡ Response: <b>{latency} ms</b>

🌌 System operational.
""",
        message.chat.id,
        msg.message_id
    )


# ============================================================
# 📢 /REPORT
# Reply karke /report
# ============================================================

@bot.message_handler(commands=["report"])
def report_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Report sirf group mein use karein."
        )
        return

    if not message.reply_to_message:

        bot.reply_to(
            message,
            """
📢 <b>REPORT</b>

Jis message ko report karna hai,
us message par reply karke:

<code>/report</code>

use karein.
"""
        )
        return

    reported = message.reply_to_message.from_user
    reporter = message.from_user

    admins = get_group_admins(
        message.chat.id
    )

    report_text = f"""
🚨 <b>REALMX REPORT</b>

👤 Reported:
<b>{reported.first_name or "Unknown"}</b>
🆔 <code>{reported.id}</code>

📢 Reported by:
<b>{reporter.first_name or "Unknown"}</b>
🆔 <code>{reporter.id}</code>

💬 Group:
<b>{message.chat.title or "Group"}</b>

🔗 <a href="https://t.me/c/{str(message.chat.id)[4:]}/{message.reply_to_message.message_id}">View Message</a>
"""

    sent = 0

    for admin in admins:

        try:

            bot.send_message(
                admin.user.id,
                report_text,
                disable_web_page_preview=True
            )

            sent += 1

        except:
            pass

    bot.reply_to(
        message,
        f"""
🚨 <b>REPORT SUBMITTED</b>

🛡️ Admins notified: <b>{sent}</b>
"""
    )


# ============================================================
# 😴 /AFK
# ============================================================

@bot.message_handler(commands=["afk"])
def afk_command(message):

    reason = message.text.partition(" ")[2].strip()

    if not reason:
        reason = "AFK"

    with db_lock:

        db.execute(
            """
            INSERT INTO afk (
                user_id,
                reason,
                since
            )
            VALUES (?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                reason = excluded.reason,
                since = excluded.since
            """,
            (
                message.from_user.id,
                reason,
                int(time.time())
            )
        )

        db.commit()

    bot.reply_to(
        message,
        f"""
😴 <b>AFK MODE ENABLED</b>

👤 {message.from_user.first_name}
📝 Reason: <b>{reason}</b>

🌌 I'll let others know you're AFK.
"""
    )


# ============================================================
# 👀 AFK CHECK ENGINE
# ============================================================

def check_afk(message):

    if not message.from_user:
        return

    # Agar khud AFK hai aur message bhej raha hai
    row = db.execute(
        """
        SELECT reason
        FROM afk
        WHERE user_id = ?
        """,
        (message.from_user.id,)
    ).fetchone()

    if row:

        db.execute(
            """
            DELETE FROM afk
            WHERE user_id = ?
            """,
            (message.from_user.id,)
        )

        db.commit()

        bot.reply_to(
            message,
            f"""
👋 <b>WELCOME BACK!</b>

😴 Your AFK status has been removed.
"""
        )

        return

    # Reply/user mention se AFK check
    target = None

    if message.reply_to_message:

        target = message.reply_to_message.from_user

    if not target:
        return

    afk = db.execute(
        """
        SELECT reason, since
        FROM afk
        WHERE user_id = ?
        """,
        (target.id,)
    ).fetchone()

    if not afk:
        return

    duration = max(
        0,
        int(time.time()) - afk["since"]
    )

    minutes = duration // 60

    bot.reply_to(
        message,
        f"""
😴 <b>{target.first_name}</b> is AFK.

📝 Reason: <b>{afk["reason"]}</b>
⏱️ AFK Time: <b>{minutes} min</b>
"""
    )


# ============================================================
# 🗑️ /SNIPE
# ============================================================

@bot.message_handler(commands=["snipe"])
def snipe_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        bot.reply_to(
            message,
            "⚠️ Snipe sirf group mein available hai."
        )
        return

    data = last_deleted_message.get(
        message.chat.id
    )

    if not data:

        bot.reply_to(
            message,
            """
🕵️ <b>NO SNIPE DATA</b>

Recently deleted message nahi mila.
"""
        )
        return

    bot.reply_to(
        message,
        f"""
🕵️ <b>REALMX SNIPE</b>

👤 User ID:
<code>{data["user_id"]}</code>

💬 Message:
<blockquote>{data["text"]}</blockquote>

🌌 Last deleted message.
"""
    )


# ============================================================
# ✏️ /EDITSNIPE
# ============================================================

@bot.message_handler(commands=["editsnipe"])
def editsnipe_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:
        bot.reply_to(
            message,
            "⚠️ Ye command sirf group mein hai."
        )
        return

    data = last_edited_message.get(
        message.chat.id
    )

    if not data:

        bot.reply_to(
            message,
            """
✏️ <b>NO EDIT SNIPE DATA</b>

Recently edited message track nahi hua.
"""
        )
        return

    bot.reply_to(
        message,
        f"""
✏️ <b>REALMX EDIT SNIPE</b>

👤 User:
<code>{data["user_id"]}</code>

🔴 Before:
<blockquote>{data["before"]}</blockquote>

🟢 After:
<blockquote>{data["after"]}</blockquote>
"""
    )


# ============================================================
# ❤️ /REP
# Reply karke /rep
# ============================================================

@bot.message_handler(commands=["rep"])
def rep_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ /rep group mein use karein."
        )
        return

    if not message.reply_to_message:

        bot.reply_to(
            message,
            """
❤️ <b>REP</b>

Kisi member ke message par reply karke:

<code>/rep</code>
"""
        )
        return

    target = message.reply_to_message.from_user
    giver = message.from_user

    if target.id == giver.id:

        bot.reply_to(
            message,
            "❌ Khud ko reputation nahi de sakte."
        )
        return

    with db_lock:

        db.execute(
            """
            INSERT OR IGNORE INTO reputation (
                user_id,
                chat_id,
                rep
            )
            VALUES (?, ?, 0)
            """,
            (
                target.id,
                message.chat.id
            )
        )

        db.execute(
            """
            UPDATE reputation
            SET rep = rep + 1
            WHERE user_id = ?
            AND chat_id = ?
            """,
            (
                target.id,
                message.chat.id
            )
        )

        db.commit()

    bot.reply_to(
        message,
        f"""
❤️ <b>REPUTATION +1</b>

👤 <b>{target.first_name or "User"}</b>

🌟 Someone gave you +1 Reputation!
"""
    )


# ============================================================
# 🏆 /TOPREP
# ============================================================

@bot.message_handler(commands=["toprep"])
def toprep_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Group mein use karein."
        )
        return

    rows = db.execute(
        """
        SELECT user_id, rep
        FROM reputation
        WHERE chat_id = ?
        ORDER BY rep DESC
        LIMIT 10
        """,
        (
            message.chat.id,
        )
    ).fetchall()

    if not rows:

        bot.reply_to(
            message,
            "🏆 Abhi reputation data available nahi hai."
        )
        return

    lines = [
        "🏆 <b>REALMX TOP REPUTATION</b>\n"
    ]

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, row in enumerate(rows):

        try:

            member = bot.get_chat_member(
                message.chat.id,
                row["user_id"]
            )

            name = member.user.first_name or "User"

        except:

            name = f"User {row['user_id']}"

        medal = (
            medals[index]
            if index < 3
            else f"{index + 1}."
        )

        lines.append(
            f"{medal} <b>{name}</b> — "
            f"❤️ {row['rep']}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# 💤 /INACTIVE
# ============================================================

@bot.message_handler(commands=["inactive"])
def inactive_command(message):

    if not require_group_admin(message):
        return

    parts = message.text.split()

    try:
        days = int(parts[1]) if len(parts) > 1 else 30
    except:
        days = 30

    if days < 1:
        days = 1

    if days > 365:
        days = 365

    cutoff = int(
        time.time()
        - (days * 86400)
    )

    rows = db.execute(
        """
        SELECT user_id, last_seen
        FROM activity
        WHERE chat_id = ?
        AND last_seen < ?
        ORDER BY last_seen ASC
        LIMIT 50
        """,
        (
            message.chat.id,
            cutoff
        )
    ).fetchall()

    if not rows:

        bot.reply_to(
            message,
            f"""
💎 <b>INACTIVE MEMBERS</b>

Last <b>{days} days</b> mein
inactive tracked members nahi mile.
"""
        )
        return

    lines = [
        f"💤 <b>INACTIVE — {days} DAYS</b>\n"
    ]

    for row in rows:

        try:

            member = bot.get_chat_member(
                message.chat.id,
                row["user_id"]
            )

            if member.status in [
                "left",
                "kicked"
            ]:
                continue

            name = (
                member.user.first_name
                or "User"
            )

        except:

            continue

        lines.append(
            f"• {name} — "
            f"<code>{row['user_id']}</code>"
        )

    if len(lines) == 1:

        bot.reply_to(
            message,
            "✅ No inactive members found."
        )
        return

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# 🔄 MESSAGE HOOK
# AFK status check
# ============================================================

@bot.message_handler(
    func=lambda message: (
        message.text is not None
        and not message.text.startswith("/")
    )
)
def social_message_hook(message):

    try:
        check_afk(message)
    except:
        pass

# ============================================================
# 🌌 REALMX HELPER — PART F
# 📊 ANALYTICS + PROFILES + RANKING
# ============================================================


# ============================================================
# 👤 PROFILE DATA
# ============================================================

def get_profile(chat_id, user_id):

    row = db.execute(
        """
        SELECT *
        FROM profiles
        WHERE chat_id = ?
        AND user_id = ?
        """,
        (
            chat_id,
            user_id
        )
    ).fetchone()

    if row:
        return row

    with db_lock:

        db.execute(
            """
            INSERT OR IGNORE INTO profiles
            (
                chat_id,
                user_id,
                xp,
                level,
                messages,
                coins
            )
            VALUES (?, ?, 0, 1, 0, 0)
            """,
            (
                chat_id,
                user_id
            )
        )

        db.commit()

    return db.execute(
        """
        SELECT *
        FROM profiles
        WHERE chat_id = ?
        AND user_id = ?
        """,
        (
            chat_id,
            user_id
        )
    ).fetchone()


# ============================================================
# ⭐ LEVEL CALCULATOR
# ============================================================

def calculate_level(xp):

    level = 1
    required = 100

    while xp >= required:

        xp -= required
        level += 1

        required = 100 + (
            (level - 1) * 50
        )

    return level, xp, required


# ============================================================
# 👤 /PROFILE
# ============================================================

@bot.message_handler(commands=["profile", "profilecard"])
def profile_command(message):

    if message.chat.type != "private":

        bot.reply_to(
            message,
            """
🔒 <b>VIP PROFILE</b>

Ye command sirf Bot ke Private DM mein available hai.

👑 Open my DM and use:
<code>/profile</code>
"""
        )
        return

    # Private chat mein group context available nahi hota.
    # Global profile use karne ke liye special chat_id.
    chat_id = 0
    user_id = message.from_user.id

    row = get_profile(
        chat_id,
        user_id
    )

    xp = row["xp"]
    level, current_xp, required_xp = calculate_level(xp)

    rep_row = db.execute(
        """
        SELECT COALESCE(SUM(rep), 0) AS rep
        FROM reputation
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    ).fetchone()

    reputation = (
        rep_row["rep"]
        if rep_row
        else 0
    )

    progress = int(
        (current_xp / required_xp) * 10
    )

    progress = max(
        0,
        min(10, progress)
    )

    bar = (
        "🟩" * progress
        + "⬜" * (10 - progress)
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "Not Set"
    )

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🎖️ Rank",
            callback_data="vip_rank"
        ),
        types.InlineKeyboardButton(
            "📊 My Stats",
            callback_data="vip_mystats"
        )
    )

    bot.send_message(
        message.chat.id,
        f"""
💎 <b>REALMX VIP PROFILE</b>

👤 Name:
<b>{message.from_user.first_name or "User"}</b>

📛 Username:
<b>{username}</b>

🆔 ID:
<code>{user_id}</code>

🎖️ Level:
<b>{level}</b>

⭐ XP:
<b>{current_xp}/{required_xp}</b>

{bar}

❤️ Reputation:
<b>{reputation}</b>

━━━━━━━━━━━━━━━━━━
🌌 <b>REALMX VIP MEMBER</b>
""",
        reply_markup=markup
    )


# ============================================================
# 🎖️ /RANK
# ============================================================

@bot.message_handler(commands=["rank", "rankcard"])
def rank_command(message):

    if message.chat.type != "private":

        bot.reply_to(
            message,
            "🔒 /rank sirf Bot DM mein available hai."
        )
        return

    row = get_profile(
        0,
        message.from_user.id
    )

    level, current_xp, required_xp = calculate_level(
        row["xp"]
    )

    progress = int(
        (current_xp / required_xp) * 10
    )

    bar = (
        "🟩" * progress
        + "⬜" * (10 - progress)
    )

    bot.send_message(
        message.chat.id,
        f"""
🎖️ <b>REALMX RANK CARD</b>

👤 <b>{message.from_user.first_name or "User"}</b>

🏅 Level:
<b>{level}</b>

⭐ XP:
<b>{current_xp} / {required_xp}</b>

{bar}

🚀 Next Level:
<b>{required_xp - current_xp} XP</b> remaining
"""
    )


# ============================================================
# 📊 /MYSTATS
# ============================================================

@bot.message_handler(commands=["mystats"])
def mystats_command(message):

    if message.chat.type != "private":

        bot.reply_to(
            message,
            "🔒 /mystats sirf Bot DM mein available hai."
        )
        return

    user_id = message.from_user.id

    row = db.execute(
        """
        SELECT
            COUNT(*) AS total_messages
        FROM activity
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    ).fetchone()

    total = (
        row["total_messages"]
        if row
        else 0
    )

    profile = get_profile(
        0,
        user_id
    )

    level, current_xp, required_xp = calculate_level(
        profile["xp"]
    )

    bot.send_message(
        message.chat.id,
        f"""
📊 <b>REALMX PERSONAL STATS</b>

👤 <b>{message.from_user.first_name or "User"}</b>

💬 Messages Tracked:
<b>{total}</b>

⭐ XP:
<b>{current_xp}</b>

🎖️ Level:
<b>{level}</b>

🌌 Account Status:
🟢 Active
"""
    )


# ============================================================
# 🏆 /LEADERBOARD
# ============================================================

@bot.message_handler(commands=["leaderboard"])
def leaderboard_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Leaderboard group mein use karein."
        )
        return

    rows = db.execute(
        """
        SELECT
            user_id,
            coins
        FROM profiles
        WHERE chat_id = ?
        ORDER BY coins DESC
        LIMIT 10
        """,
        (
            message.chat.id,
        )
    ).fetchall()

    if not rows:

        bot.reply_to(
            message,
            "🏆 Abhi leaderboard empty hai."
        )
        return

    lines = [
        "🏆 <b>REALMX COIN LEADERBOARD</b>\n"
    ]

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    position = 1

    for row in rows:

        try:

            member = bot.get_chat_member(
                message.chat.id,
                row["user_id"]
            )

            name = (
                member.user.first_name
                or "User"
            )

        except:

            name = "Unknown User"

        medal = (
            medals[position - 1]
            if position <= 3
            else f"{position}."
        )

        lines.append(
            f"{medal} <b>{name}</b> — "
            f"💰 {row['coins']}"
        )

        position += 1

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# 📅 /ACTIVITY + /TODAY
# ============================================================

@bot.message_handler(commands=["activity", "today"])
def activity_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Group mein use karein."
        )
        return

    start_of_day = int(
        datetime.now().replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        ).timestamp()
    )

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM message_stats
        WHERE chat_id = ?
        AND timestamp >= ?
        """,
        (
            message.chat.id,
            start_of_day
        )
    ).fetchone()

    total = (
        row["total"]
        if row
        else 0
    )

    bot.reply_to(
        message,
        f"""
📊 <b>TODAY'S ACTIVITY</b>

💬 Messages:
<b>{total}</b>

📅 Today:
<b>{datetime.now().strftime("%d %B %Y")}</b>

🌌 REALMX ANALYTICS
"""
    )


# ============================================================
# 📅 /WEEKLY
# ============================================================

@bot.message_handler(commands=["weekly"])
def weekly_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Group mein use karein."
        )
        return

    start = int(
        time.time() - (7 * 86400)
    )

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM message_stats
        WHERE chat_id = ?
        AND timestamp >= ?
        """,
        (
            message.chat.id,
            start
        )
    ).fetchone()

    total = (
        row["total"]
        if row
        else 0
    )

    bot.reply_to(
        message,
        f"""
📅 <b>REALMX WEEKLY REPORT</b>

💬 Total Messages:
<b>{total}</b>

🗓️ Period:
Last <b>7 days</b>
"""
    )


# ============================================================
# 🔥 TOP USERS
# ============================================================

def top_users(chat_id):

    rows = db.execute(
        """
        SELECT
            user_id,
            COUNT(*) AS messages
        FROM message_stats
        WHERE chat_id = ?
        AND timestamp >= ?
        GROUP BY user_id
        ORDER BY messages DESC
        LIMIT 10
        """,
        (
            chat_id,
            int(time.time() - (7 * 86400))
        )
    ).fetchall()

    return rows


# ============================================================
# 🔥 /TOPUSERS + /TOPACTIVE
# ============================================================

@bot.message_handler(commands=["topusers", "topactive"])
def topusers_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Group mein use karein."
        )
        return

    rows = top_users(
        message.chat.id
    )

    if not rows:

        bot.reply_to(
            message,
            "📊 Abhi activity data available nahi hai."
        )
        return

    lines = [
        "🔥 <b>REALMX TOP ACTIVE USERS</b>\n"
    ]

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, row in enumerate(rows):

        try:

            member = bot.get_chat_member(
                message.chat.id,
                row["user_id"]
            )

            name = (
                member.user.first_name
                or "User"
            )

        except:

            continue

        medal = (
            medals[index]
            if index < 3
            else f"{index + 1}."
        )

        lines.append(
            f"{medal} <b>{name}</b> — "
            f"💬 {row['messages']}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines)
    )


# ============================================================
# 📊 /GROUPSTATS + /CHATSTATS
# ============================================================

@bot.message_handler(commands=["groupstats", "chatstats"])
def groupstats_command(message):

    if message.chat.type not in [
        "group",
        "supergroup"
    ]:

        bot.reply_to(
            message,
            "⚠️ Ye command group mein use karein."
        )
        return

    total_row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM message_stats
        WHERE chat_id = ?
        """,
        (
            message.chat.id,
        )
    ).fetchone()

    users_row = db.execute(
        """
        SELECT COUNT(DISTINCT user_id) AS total
        FROM message_stats
        WHERE chat_id = ?
        """,
        (
            message.chat.id,
        )
    ).fetchone()

    total = (
        total_row["total"]
        if total_row
        else 0
    )

    users = (
        users_row["total"]
        if users_row
        else 0
    )

    bot.send_message(
        message.chat.id,
        f"""
📊 <b>REALMX GROUP ANALYTICS</b>

🌌 Group:
<b>{message.chat.title or "Unknown"}</b>

💬 Total Messages:
<b>{total}</b>

👥 Active Tracked Users:
<b>{users}</b>

🆔 Chat ID:
<code>{message.chat.id}</code>
"""
    )


# ============================================================
# 📈 MESSAGE TRACKING ENGINE
# ============================================================

@bot.message_handler(
    func=lambda message: (
        message.chat.type in [
            "group",
            "supergroup"
        ]
        and message.from_user is not None
    )
)
def analytics_tracker(message):

    try:

        chat_id = message.chat.id
        user_id = message.from_user.id

        now = int(
            time.time()
        )

        # ----------------------------------------
        # ACTIVITY
        # ----------------------------------------

        db.execute(
            """
            INSERT INTO activity
            (
                chat_id,
                user_id,
                last_seen
            )
            VALUES (?, ?, ?)

            ON CONFLICT(chat_id, user_id)
            DO UPDATE SET
                last_seen = excluded.last_seen
            """,
            (
                chat_id,
                user_id,
                now
            )
        )

        # ----------------------------------------
        # MESSAGE STATS
        # ----------------------------------------

        db.execute(
            """
            INSERT INTO message_stats
            (
                chat_id,
                user_id,
                timestamp
            )
            VALUES (?, ?, ?)
            """,
            (
                chat_id,
                user_id,
                now
            )
        )

        # ----------------------------------------
        # PROFILE XP
        # ----------------------------------------

        db.execute(
            """
            INSERT OR IGNORE INTO profiles
            (
                chat_id,
                user_id,
                xp,
                level,
                messages,
                coins
            )
            VALUES (?, ?, 0, 1, 0, 0)
            """,
            (
                chat_id,
                user_id
            )
        )

        db.execute(
            """
            UPDATE profiles
            SET
                xp = xp + 5,
                messages = messages + 1
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user_id
            )
        )

        db.commit()

    except Exception:
        pass


# ============================================================
# ✏️ EDITED MESSAGE TRACKING
# ============================================================

@bot.edited_message_handler(
    func=lambda message: (
        message.chat.type in [
            "group",
            "supergroup"
        ]
        and message.text is not None
    )
)
def track_edited_message(message):

    try:

        last_edited_message[
            message.chat.id
        ] = {
            "user_id": message.from_user.id,
            "before": "Previous version unavailable",
            "after": message.text,
            "time": time.time()
        }

    except:
        pass

        # ============================================================
# 🌌 REALMX HELPER — PART G
# 🎮 MINI GAMES & FUN
# ============================================================

import random


# ============================================================
# 🎲 /DICE
# ============================================================

@bot.message_handler(commands=["dice"])
def dice_command(message):

    number = random.randint(1, 6)

    bot.send_message(
        message.chat.id,
        f"""
🎲 <b>REALMX DICE</b>

👤 {message.from_user.first_name}

🎲 Result: <b>{number}</b>

🌌 Good luck!
"""
    )


# ============================================================
# 🪙 /COIN
# ============================================================

@bot.message_handler(commands=["coin"])
def coin_command(message):

    result = random.choice(
        ["HEADS 🪙", "TAILS 🪙"]
    )

    bot.send_message(
        message.chat.id,
        f"""
🪙 <b>REALMX COIN TOSS</b>

🎯 Result:
<b>{result}</b>
"""
    )


# ============================================================
# ✊ /RPS
# /rps rock
# /rps paper
# /rps scissors
# ============================================================

@bot.message_handler(commands=["rps"])
def rps_command(message):

    parts = message.text.split()

    if len(parts) < 2:

        bot.reply_to(
            message,
            """
✊ <b>ROCK PAPER SCISSORS</b>

Use:

<code>/rps rock</code>
<code>/rps paper</code>
<code>/rps scissors</code>
"""
        )
        return

    user_choice = parts[1].lower()

    choices = [
        "rock",
        "paper",
        "scissors"
    ]

    if user_choice not in choices:

        bot.reply_to(
            message,
            "❌ Choose rock, paper ya scissors."
        )
        return

    bot_choice = random.choice(
        choices
    )

    if user_choice == bot_choice:
        result = "🤝 DRAW!"

    elif (
        (user_choice == "rock" and bot_choice == "scissors")
        or
        (user_choice == "paper" and bot_choice == "rock")
        or
        (user_choice == "scissors" and bot_choice == "paper")
    ):
        result = "🏆 YOU WIN!"

    else:
        result = "🤖 BOT WINS!"

    bot.send_message(
        message.chat.id,
        f"""
✊ <b>REALMX RPS</b>

👤 Your Choice:
<b>{user_choice.title()}</b>

🤖 Bot Choice:
<b>{bot_choice.title()}</b>

━━━━━━━━━━━━━━
🎯 <b>{result}</b>
"""
    )


# ============================================================
# 🔢 /GUESS
# /guess 7
# ============================================================

@bot.message_handler(commands=["guess"])
def guess_command(message):

    parts = message.text.split()

    if len(parts) < 2:

        bot.reply_to(
            message,
            """
🔢 <b>NUMBER GUESS</b>

1 से 10 ke beech number choose karein.

Example:
<code>/guess 7</code>
"""
        )
        return

    try:

        user_number = int(parts[1])

    except:

        bot.reply_to(
            message,
            "❌ Sirf number enter karein."
        )
        return

    if user_number < 1 or user_number > 10:

        bot.reply_to(
            message,
            "⚠️ Number 1 se 10 ke beech hona chahiye."
        )
        return

    correct = random.randint(
        1,
        10
    )

    if user_number == correct:

        result = "🎉 CORRECT! You Win!"

    else:

        result = (
            f"❌ Wrong!\n"
            f"Correct number: <b>{correct}</b>"
        )

    bot.send_message(
        message.chat.id,
        f"""
🔢 <b>REALMX GUESS GAME</b>

👤 Your Guess:
<b>{user_number}</b>

🎯 {result}
"""
    )


# ============================================================
# 🧠 QUIZ QUESTIONS
# ============================================================

QUIZ_QUESTIONS = [
    (
        "भारत की राजधानी क्या है?",
        ["Mumbai", "Delhi", "Kolkata", "Chennai"],
        "Delhi"
    ),
    (
        "भारत का राष्ट्रीय पशु कौन सा है?",
        ["Lion", "Tiger", "Elephant", "Leopard"],
        "Tiger"
    ),
    (
        "2 + 2 कितना होता है?",
        ["3", "4", "5", "6"],
        "4"
    ),
    (
        "पृथ्वी का प्राकृतिक उपग्रह कौन है?",
        ["Sun", "Moon", "Mars", "Venus"],
        "Moon"
    ),
    (
        "Python किस प्रकार की भाषा है?",
        ["Programming", "Markup", "Database", "Browser"],
        "Programming"
    )
]


# ============================================================
# 🧠 /QUIZ
# ============================================================

@bot.message_handler(commands=["quiz"])
def quiz_command(message):

    question, options, answer = random.choice(
        QUIZ_QUESTIONS
    )

    quiz_id = random.randint(
        100000,
        999999
    )

    with db_lock:

        db.execute(
            """
            INSERT OR REPLACE INTO quizzes
            (
                quiz_id,
                chat_id,
                question,
                answer
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                quiz_id,
                message.chat.id,
                question,
                answer
            )
        )

        db.commit()

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    buttons = []

    for option in options:

        buttons.append(
            types.InlineKeyboardButton(
                option,
                callback_data=f"quiz:{quiz_id}:{option}"
            )
        )

    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f"""
🧠 <b>REALMX QUIZ</b>

❓ {question}

🎯 Choose the correct answer:
""",
        reply_markup=markup
    )


# ============================================================
# 🧠 QUIZ CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("quiz:")
    )
)
def quiz_callback(call):

    try:

        _, quiz_id, selected = (
            call.data.split(
                ":",
                2
            )
        )

        row = db.execute(
            """
            SELECT answer
            FROM quizzes
            WHERE quiz_id = ?
            """,
            (
                int(quiz_id),
            )
        ).fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "⚠️ Quiz expired."
            )
            return

        answer = row["answer"]

        if selected == answer:

            result = "🎉 Correct! You Win!"

        else:

            result = (
                f"❌ Wrong!\n"
                f"Correct Answer: <b>{answer}</b>"
            )

        bot.answer_callback_query(
            call.id,
            result[:200]
        )

        bot.edit_message_text(
            f"""
🧠 <b>REALMX QUIZ RESULT</b>

👤 Player:
<b>{call.from_user.first_name}</b>

🎯 Your Answer:
<b>{selected}</b>

🏆 {result}
""",
            call.message.chat.id,
            call.message.message_id
        )

    except:

        bot.answer_callback_query(
            call.id,
            "❌ Quiz error."
        )


# ============================================================
# ❤️ /TRUTH
# ============================================================

TRUTH_QUESTIONS = [
    "Aisi kaunsi skill hai jo tum seekhna chahte ho?",
    "Tumhara favourite hobby kya hai?",
    "Kaunsi movie ya series tumhe sabse zyada pasand hai?",
    "Aisi kaunsi jagah hai jahan tum future mein jaana chahte ho?",
    "Tumhara favourite game kaunsa hai?"
]


@bot.message_handler(commands=["truth"])
def truth_command(message):

    question = random.choice(
        TRUTH_QUESTIONS
    )

    bot.send_message(
        message.chat.id,
        f"""
❤️ <b>REALMX TRUTH</b>

👤 {message.from_user.first_name}

❓ <b>{question}</b>
"""
    )


# ============================================================
# 🎯 /DARE
# ============================================================

DARES = [
    "Apna favourite emoji bhejo. 😎",
    "Group mein ek funny joke share karo. 😂",
    "Apna favourite song ka naam batao. 🎵",
    "3 random emojis bhejo. 🔥",
    "Ek positive message group mein bhejo. ✨"
]


@bot.message_handler(commands=["dare"])
def dare_command(message):

    dare = random.choice(
        DARES
    )

    bot.send_message(
        message.chat.id,
        f"""
🎯 <b>REALMX DARE</b>

👤 {message.from_user.first_name}

🔥 Your Dare:

<b>{dare}</b>
"""
    )


# ============================================================
# 🎱 /8BALL
# ============================================================

EIGHT_BALL = [
    "🎱 Yes, definitely.",
    "🎱 Most likely.",
    "🎱 Ask again later.",
    "🎱 It is possible.",
    "🎱 Don't count on it.",
    "🎱 Very unlikely.",
    "🎱 The signs point to yes.",
    "🎱 The signs are unclear."
]


@bot.message_handler(commands=["8ball"])
def eightball_command(message):

    question = message.text.partition(
        " "
    )[2].strip()

    if not question:

        bot.reply_to(
            message,
            """
🎱 <b>MAGIC 8-BALL</b>

Question ke saath command use karein.

Example:
<code>/8ball Will I win?</code>
"""
        )
        return

    answer = random.choice(
        EIGHT_BALL
    )

    bot.send_message(
        message.chat.id,
        f"""
🎱 <b>REALMX MAGIC 8-BALL</b>

❓ Question:
<b>{question}</b>

🔮 Answer:
<b>{answer}</b>
"""
    )


# ============================================================
# ❌⭕ TIC TAC TOE
# ============================================================

def ttt_board(
    game_id,
    board
):

    markup = types.InlineKeyboardMarkup(
        row_width=3
    )

    buttons = []

    for index, value in enumerate(board):

        display = value if value else "⬜"

        buttons.append(
            types.InlineKeyboardButton(
                display,
                callback_data=f"ttt:{game_id}:{index}"
            )
        )

    markup.add(*buttons)

    return markup


def ttt_winner(board):

    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6)
    ]

    for a, b, c in winning_lines:

        if (
            board[a]
            and board[a] == board[b]
            and board[a] == board[c]
        ):
            return board[a]

    if all(board):
        return "DRAW"

    return None


# ============================================================
# 🎮 /TICTAC
# ============================================================

@bot.message_handler(commands=["tictac"])
def tictac_command(message):

    game_id = random.randint(
        100000,
        999999
    )

    board = [""] * 9

    with db_lock:

        db.execute(
            """
            INSERT OR REPLACE INTO tictactoe
            (
                game_id,
                chat_id,
                player_id,
                board,
                turn
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                game_id,
                message.chat.id,
                message.from_user.id,
                json.dumps(board),
                "X"
            )
        )

        db.commit()

    bot.send_message(
        message.chat.id,
        f"""
🎮 <b>REALMX TIC TAC TOE</b>

👤 Player:
<b>{message.from_user.first_name}</b>

❌ You are <b>X</b>
🤖 Bot is <b>O</b>

👇 Make your move:
""",
        reply_markup=ttt_board(
            game_id,
            board
        )
    )


# ============================================================
# 🎮 TIC TAC TOE CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("ttt:")
    )
)
def tictac_callback(call):

    try:

        _, game_id, position = (
            call.data.split(":")
        )

        game_id = int(game_id)
        position = int(position)

        row = db.execute(
            """
            SELECT *
            FROM tictactoe
            WHERE game_id = ?
            """,
            (
                game_id,
            )
        ).fetchone()

        if not row:

            bot.answer_callback_query(
                call.id,
                "⚠️ Game expired."
            )
            return

        if row["player_id"] != call.from_user.id:

            bot.answer_callback_query(
                call.id,
                "❌ Ye game kisi aur player ka hai."
            )
            return

        board = json.loads(
            row["board"]
        )

        if board[position]:

            bot.answer_callback_query(
                call.id,
                "⚠️ Ye box already filled hai."
            )
            return

        board[position] = "❌"

        winner = ttt_winner(
            board
        )

        if winner:

            result = (
                "🎉 YOU WIN!"
                if winner == "❌"
                else "🤝 DRAW!"
                if winner == "DRAW"
                else "🤖 BOT WINS!"
            )

            db.execute(
                """
                DELETE FROM tictactoe
                WHERE game_id = ?
                """,
                (game_id,)
            )

            db.commit()

            bot.edit_message_text(
                f"""
🎮 <b>REALMX TIC TAC TOE</b>

🏆 <b>{result}</b>
""",
                call.message.chat.id,
                call.message.message_id
            )

            bot.answer_callback_query(
                call.id
            )

            return

        # ----------------------------------------------------
        # 🤖 BOT MOVE
        # ----------------------------------------------------

        empty = [
            i
            for i, value in enumerate(board)
            if not value
        ]

        if empty:

            bot_position = random.choice(
                empty
            )

            board[bot_position] = "⭕"

        winner = ttt_winner(
            board
        )

        if winner:

            result = (
                "🎉 YOU WIN!"
                if winner == "❌"
                else "🤝 DRAW!"
                if winner == "DRAW"
                else "🤖 BOT WINS!"
            )

            db.execute(
                """
                DELETE FROM tictactoe
                WHERE game_id = ?
                """,
                (game_id,)
            )

            db.commit()

            bot.edit_message_text(
                f"""
🎮 <b>REALMX TIC TAC TOE</b>

🏆 <b>{result}</b>
""",
                call.message.chat.id,
                call.message.message_id
            )

            bot.answer_callback_query(
                call.id
            )

            return

        db.execute(
            """
            UPDATE tictactoe
            SET board = ?
            WHERE game_id = ?
            """,
            (
                json.dumps(board),
                game_id
            )
        )

        db.commit()

        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=ttt_board(
                game_id,
                board
            )
        )

        bot.answer_callback_query(
            call.id
        )

    except Exception:

        bot.answer_callback_query(
            call.id,
            "❌ Game error."
        )


# ============================================================
# 🎮 GAME MENU
# ============================================================

@bot.message_handler(commands=["games"])
def games_command(message):

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🎲 Dice",
            callback_data="game_dice"
        ),
        types.InlineKeyboardButton(
            "🪙 Coin",
            callback_data="game_coin"
        ),
        types.InlineKeyboardButton(
            "✊ RPS",
            callback_data="game_rps"
        ),
        types.InlineKeyboardButton(
            "🧠 Quiz",
            callback_data="game_quiz"
        ),
        types.InlineKeyboardButton(
            "❤️ Truth",
            callback_data="game_truth"
        ),
        types.InlineKeyboardButton(
            "🎯 Dare",
            callback_data="game_dare"
        ),
        types.InlineKeyboardButton(
            "🎱 8-Ball",
            callback_data="game_8ball"
        ),
        types.InlineKeyboardButton(
            "❌⭕ Tic Tac Toe",
            callback_data="game_ttt"
        )
    )

    bot.send_message(
        message.chat.id,
        """
🎮 <b>REALMX GAME ZONE</b>

🔥 Choose a game below:

🎲 Dice
🪙 Coin Toss
✊ Rock Paper Scissors
🧠 Quiz
❤️ Truth
🎯 Dare
🎱 Magic 8-Ball
❌⭕ Tic Tac Toe
""",
        reply_markup=markup
    )


# ============================================================
# 🎮 GAME MENU CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("game_")
    )
)
def game_menu_callback(call):

    action = call.data

    bot.answer_callback_query(
        call.id
    )

    if action == "game_dice":

        bot.send_message(
            call.message.chat.id,
            f"🎲 You rolled: <b>{random.randint(1, 6)}</b>"
        )

    elif action == "game_coin":

        bot.send_message(
            call.message.chat.id,
            f"🪙 Result: <b>{random.choice(['HEADS', 'TAILS'])}</b>"
        )

    elif action == "game_rps":

        bot.send_message(
            call.message.chat.id,
            "✊ Use <code>/rps rock</code>, <code>/rps paper</code> or <code>/rps scissors</code>"
        )

    elif action == "game_quiz":

        quiz_command(call.message)

    elif action == "game_truth":

        truth_command(call.message)

    elif action == "game_dare":

        dare_command(call.message)

    elif action == "game_8ball":

        bot.send_message(
            call.message.chat.id,
            "🎱 Question ke saath <code>/8ball your question</code> use karein."
        )

    elif action == "game_ttt":

        tictac_command(call.message)

    # ============================================================
# 🌌 REALMX HELPER — FINAL PART
# 👑 OWNER COMMANDS + HELP + FINAL START
# ============================================================

# ============================================================
# 👑 OWNER CHECK
# ============================================================

def is_owner(message):

    return (
        message.from_user
        and message.from_user.id == OWNER_ID
    )


def owner_only(message):

    if not is_owner(message):

        bot.reply_to(
            message,
            """
🚫 <b>ACCESS DENIED</b>

👑 Ye command sirf REALMX Owner ke liye hai.
"""
        )

        return False

    return True


# ============================================================
# 👑 /PANEL
# ============================================================

@bot.message_handler(commands=["panel"])
def owner_panel(message):

    if message.chat.type != "private":
        return

    if not owner_only(message):
        return

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "📊 Stats",
            callback_data="owner_stats"
        ),
        types.InlineKeyboardButton(
            "📢 Broadcast",
            callback_data="owner_broadcast"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🌐 GCast",
            callback_data="owner_gcast"
        ),
        types.InlineKeyboardButton(
            "💾 Backup",
            callback_data="owner_backup"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🔄 Restart",
            callback_data="owner_restart"
        )
    )

    bot.send_message(
        message.chat.id,
        """
👑 <b>REALMX OWNER PANEL</b>

🌌 Welcome, Owner.

Select an option below:

📊 Bot Statistics
📢 Private Broadcast
🌐 Group Broadcast
💾 Database Backup
🔄 Restart Bot
""",
        reply_markup=markup
    )


# ============================================================
# 📊 /STATS
# ============================================================

@bot.message_handler(commands=["stats"])
def owner_stats(message):

    if not owner_only(message):
        return

    try:

        users = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM users
            """
        ).fetchone()["total"]

    except:

        users = 0

    try:

        groups = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM groups
            """
        ).fetchone()["total"]

    except:

        groups = 0

    try:

        messages = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM message_stats
            """
        ).fetchone()["total"]

    except:

        messages = 0

    bot.send_message(
        message.chat.id,
        f"""
📊 <b>REALMX BOT STATISTICS</b>

👤 Users:
<b>{users}</b>

👥 Groups:
<b>{groups}</b>

💬 Messages:
<b>{messages}</b>

🟢 Bot Status:
<b>ONLINE</b>

🌌 REALMX HELPER
"""
    )


# ============================================================
# 📢 /BROADCAST
# ============================================================

@bot.message_handler(commands=["broadcast"])
def broadcast_command(message):

    if not owner_only(message):
        return

    text = message.text.partition(
        " "
    )[2].strip()

    if not text:

        bot.reply_to(
            message,
            """
📢 <b>BROADCAST</b>

Use:

<code>/broadcast Your message</code>
"""
        )
        return

    try:

        rows = db.execute(
            """
            SELECT user_id
            FROM users
            """
        ).fetchall()

    except:

        rows = []

    sent = 0
    failed = 0

    for row in rows:

        try:

            bot.send_message(
                row["user_id"],
                f"""
📢 <b>REALMX BROADCAST</b>

{text}

━━━━━━━━━━━━━━
👑 REALMX OWNER
"""
            )

            sent += 1

        except:

            failed += 1

    bot.reply_to(
        message,
        f"""
📢 <b>BROADCAST COMPLETE</b>

✅ Sent: <b>{sent}</b>
❌ Failed: <b>{failed}</b>
"""
    )


# ============================================================
# 🌐 /GCAST
# ============================================================

@bot.message_handler(commands=["gcast"])
def gcast_command(message):

    if not owner_only(message):
        return

    text = message.text.partition(
        " "
    )[2].strip()

    if not text:

        bot.reply_to(
            message,
            """
🌐 <b>GLOBAL GROUP CAST</b>

Use:

<code>/gcast Your message</code>
"""
        )
        return

    try:

        rows = db.execute(
            """
            SELECT chat_id
            FROM groups
            """
        ).fetchall()

    except:

        rows = []

    sent = 0
    failed = 0

    for row in rows:

        try:

            bot.send_message(
                row["chat_id"],
                f"""
🌐 <b>REALMX GLOBAL CAST</b>

{text}

━━━━━━━━━━━━━━
👑 REALMX OWNER
"""
            )

            sent += 1

        except:

            failed += 1

    bot.reply_to(
        message,
        f"""
🌐 <b>GLOBAL CAST COMPLETE</b>

✅ Groups reached:
<b>{sent}</b>

❌ Failed:
<b>{failed}</b>
"""
    )


# ============================================================
# 💾 /BACKUP
# ============================================================

@bot.message_handler(commands=["backup"])
def backup_command(message):

    if not owner_only(message):
        return

    try:

        db.commit()

        backup_name = (
            "realmx_backup_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".db"
        )

        shutil.copy(
            DB_FILE,
            backup_name
        )

        with open(
            backup_name,
            "rb"
        ) as file:

            bot.send_document(
                message.chat.id,
                file,
                caption="""
💾 <b>REALMX DATABASE BACKUP</b>

✅ Backup created successfully.
"""
            )

    except Exception as e:

        bot.reply_to(
            message,
            f"""
❌ <b>BACKUP FAILED</b>

<code>{str(e)[:500]}</code>
"""
        )


# ============================================================
# 🔄 /RESTART
# ============================================================

@bot.message_handler(commands=["restart"])
def restart_command(message):

    if not owner_only(message):
        return

    bot.reply_to(
        message,
        """
🔄 <b>REALMX RESTART</b>

♻️ Restart signal sent.

🌌 Railway will restart the service.
"""
    )

    # Railway/container process restart
    try:

        import os
        import sys

        os.execl(
            sys.executable,
            sys.executable,
            *sys.argv
        )

    except Exception:

        pass


# ============================================================
# 🆘 /HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    markup = types.InlineKeyboardMarkup(
        row_width=2
    )

    markup.add(
        types.InlineKeyboardButton(
            "🛡️ Moderation",
            callback_data="help_moderation"
        ),
        types.InlineKeyboardButton(
            "🎮 Games",
            callback_data="help_games"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "📊 Analytics",
            callback_data="help_analytics"
        ),
        types.InlineKeyboardButton(
            "⚙️ AutoMod",
            callback_data="help_automod"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🛠️ Utility",
            callback_data="help_utility"
        )
    )

    bot.send_message(
        message.chat.id,
        """
🌌 <b>REALMX HELPER</b>

💎 <b>VIP COMMAND CENTER</b>

Choose a category below 👇
""",
        reply_markup=markup
    )


# ============================================================
# 🆘 HELP CALLBACK
# ============================================================

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("help_")
    )
)
def help_callback(call):

    category = call.data.replace(
        "help_",
        ""
    )

    if category == "moderation":

        text = """
🛡️ <b>MODERATION</b>

/ban
/unban
/kick
/mute
/unmute
/warn
/unwarn
/purge
/pin
/unpin

👑 Staff:
/promote1
/promote2
/promote3
/demote
"""

    elif category == "games":

        text = """
🎮 <b>GAMES</b>

/dice
/coin
/rps
/guess
/quiz
/truth
/dare
/8ball
/tictac
/games
"""

    elif category == "analytics":

        text = """
📊 <b>ANALYTICS</b>

/profile
/rank
/mystats
/leaderboard
/activity
/today
/weekly
/topusers
/topactive
/groupstats
/chatstats
"""

    elif category == "automod":

        text = """
⚙️ <b>AUTOMOD</b>

/antispam
/antiflood
/blocklist
/welcome
/goodbye
/setwelcome
/setrules
/rules
/filter
/stopfilter
"""

    else:

        text = """
🛠️ <b>UTILITY</b>

/start
/help
/id
/info
/ping
/report
/afk
/snipe
/editsnipe
/rep
/toprep
/inactive
"""

    bot.answer_callback_query(
        call.id
    )

    bot.send_message(
        call.message.chat.id,
        f"""
🌌 <b>REALMX HELPER</b>

{text}
""",
    )


# ============================================================
# 👑 OWNER CALLBACKS
# ============================================================

@bot.callback_query_handler(
    func=lambda call: (
        call.data.startswith("owner_")
    )
)
def owner_callback(call):

    if call.from_user.id != OWNER_ID:

        bot.answer_callback_query(
            call.id,
            "🚫 Owner only."
        )

        return

    action = call.data.replace(
        "owner_",
        ""
    )

    bot.answer_callback_query(
        call.id
    )

    if action == "stats":

        owner_stats(
            call.message
        )

    elif action == "broadcast":

        bot.send_message(
            call.message.chat.id,
            """
📢 <b>BROADCAST</b>

Use:

<code>/broadcast Your message</code>
"""
        )

    elif action == "gcast":

        bot.send_message(
            call.message.chat.id,
            """
🌐 <b>GLOBAL CAST</b>

Use:

<code>/gcast Your message</code>
"""
        )

    elif action == "backup":

        backup_command(
            call.message
        )

    elif action == "restart":

        restart_command(
            call.message
        )


# ============================================================
# 🌌 FINAL STARTUP
# ============================================================

print(
    "🌌 REALMX HELPER BOT STARTED"
)

print(
    f"👑 OWNER: {OWNER_ID}"
)

print(
    f"🤖 BOT: @{BOT_USERNAME}"
)

print(
    "🟢 Railway polling started..."
)

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
)
