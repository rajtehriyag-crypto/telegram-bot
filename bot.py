import telebot
from telebot import types

# =========================
# CONFIG
# =========================

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"

SUPPORT_CHANNEL = "https://t.me/realmXsupport"
SUPPORT_GROUP = "https://t.me/+6BXS6AfvJPQ2OTI1"

BOT_USERNAME = "@realmXhelperbot"  # @ ke bina

# =========================
# BOT START
# =========================

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):

    # Group me use hua
    if message.chat.type != "private":

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "🌌 Open Bot In DM",
                url=f"https://t.me/{BOT_USERNAME}"
            )
        )

        bot.reply_to(
            message,
            "🤖 Please start me in private chat.",
            reply_markup=markup
        )
        return

    # DM Welcome Panel
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
🌌 REALMX HELPER BOT 🌌

🛡️ Advanced Moderation
📊 Statistics System
💰 Economy Features
🎮 Fun Commands

👑 Owner: {OWNER_USERNAME}

Welcome to the RealmX Network.
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )

# ==========================================
# REALMX VIP MODERATION SYSTEM
# ==========================================

import time

warnings_db = {}

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


def vip_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton(
            "📢 Support",
            url=SUPPORT_CHANNEL
        ),
        types.InlineKeyboardButton(
            "💬 Group",
            url=SUPPORT_GROUP
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👑 Owner",
            url="https://t.me/internationalpanditG"
        )
    )

    return markup


# ==========================================
# /BAN
# ==========================================

@bot.message_handler(commands=['ban'])
def ban_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Reply to a user and use /ban"
        )
        return

    target = message.reply_to_message.from_user

    try:

        bot.ban_chat_member(
            message.chat.id,
            target.id
        )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 🔨 REALMX SECURITY 🔨 ║
╚══════════════════════╝

🚫 ACTION
Permanent Ban

👤 USER
{target.first_name}

🆔 USER ID
{target.id}

🛡️ MODERATOR
{message.from_user.first_name}

✅ STATUS
User Banned Successfully
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(message, f"❌ {e}")


# ==========================================
# /UNBAN
# ==========================================

@bot.message_handler(commands=['unban'])
def unban_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Reply to a user and use /unban"
        )
        return

    target = message.reply_to_message.from_user

    try:

        bot.unban_chat_member(
            message.chat.id,
            target.id
        )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ ✅ REALMX RESTORE ✅ ║
╚══════════════════════╝

👤 USER
{target.first_name}

🆔 USER ID
{target.id}

⚡ STATUS
Access Restored

🛡️ MODERATOR
{message.from_user.first_name}
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(message, f"❌ {e}")


# ==========================================
# /KICK
# ==========================================

@bot.message_handler(commands=['kick'])
def kick_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Reply to a user and use /kick"
        )
        return

    target = message.reply_to_message.from_user

    try:

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
╔══════════════════════╗
║ 👢 REALMX ACTION 👢 ║
╚══════════════════════╝

👤 USER
{target.first_name}

⚡ ACTION
Temporary Kick

🛡️ MODERATOR
{message.from_user.first_name}

✅ STATUS
User Removed Successfully
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(message, f"❌ {e}")


# ==========================================
# /MUTE
# Example: /mute 30
# ==========================================

@bot.message_handler(commands=['mute'])
def mute_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Reply to user\nExample: /mute 30"
        )
        return

    target = message.reply_to_message.from_user

    try:

        parts = message.text.split()

        minutes = 30

        if len(parts) > 1:
            minutes = int(parts[1])

        until_date = int(time.time()) + (minutes * 60)

        permissions = types.ChatPermissions(
            can_send_messages=False
        )

        bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions,
            until_date=until_date
        )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 🔇 REALMX SILENCE 🔇 ║
╚══════════════════════╝

👤 USER
{target.first_name}

⏳ DURATION
{minutes} Minutes

🛡️ MODERATOR
{message.from_user.first_name}

✅ STATUS
User Muted Successfully
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(message, f"❌ {e}")


# ==========================================
# /UNMUTE
# ==========================================

@bot.message_handler(commands=['unmute'])
def unmute_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Reply to muted user"
        )
        return

    target = message.reply_to_message.from_user

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
            permissions
        )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 🔊 REALMX RESTORE 🔊 ║
╚══════════════════════╝

👤 USER
{target.first_name}

⚡ STATUS
Permissions Restored

🛡️ MODERATOR
{message.from_user.first_name}
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(message, f"❌ {e}")

bot.infinity_polling()
