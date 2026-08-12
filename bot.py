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

# ==========================================
# REALMX VIP MODERATION — PART 1A (NEXT)
# WARN / UNWARN / PURGE / PIN / UNPIN
# ==========================================


# ==========================================
# /WARN
# 3 WARNINGS = AUTO BAN
# ==========================================

@bot.message_handler(commands=['warn'])
def warn_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "⚠️ Reply to a member's message and use /warn"
        )
        return

    target = message.reply_to_message.from_user

    # Bot ya admin ko warn na kare
    if target.is_bot:
        bot.reply_to(message, "❌ Bots cannot be warned.")
        return

    if is_admin(message.chat.id, target.id):
        bot.reply_to(message, "❌ You cannot warn a group administrator.")
        return

    key = (message.chat.id, target.id)

    warnings_db[key] = warnings_db.get(key, 0) + 1
    count = warnings_db[key]

    # 3 warnings = automatic ban
    if count >= 3:

        try:
            bot.ban_chat_member(
                message.chat.id,
                target.id
            )

            warnings_db[key] = 0

            bot.send_message(
                message.chat.id,
                f"""
╔══════════════════════╗
║ 🚨 REALMX SECURITY 🚨 ║
╚══════════════════════╝

🔨 ACTION
Automatic Ban

👤 USER
{target.first_name}

🆔 USER ID
{target.id}

⚠️ WARNINGS
3 / 3

🛡️ MODERATOR
{message.from_user.first_name}

🚫 STATUS
3 Warnings Reached
User Permanently Banned
""",
                reply_markup=vip_panel()
            )

        except Exception as e:
            bot.reply_to(message, f"❌ {e}")

        return

    bot.send_message(
        message.chat.id,
        f"""
╔══════════════════════╗
║ ⚠️ REALMX WARNING ⚠️ ║
╚══════════════════════╝

👤 USER
{target.first_name}

🆔 USER ID
{target.id}

⚠️ WARNING
{count} / 3

🛡️ ISSUED BY
{message.from_user.first_name}

📌 NOTICE
3 Warnings = Automatic Ban
""",
        reply_markup=vip_panel()
    )


# ==========================================
# /UNWARN
# ==========================================

@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "🟢 Reply to the member's message and use /unwarn"
        )
        return

    target = message.reply_to_message.from_user
    key = (message.chat.id, target.id)

    current = warnings_db.get(key, 0)

    if current <= 0:
        bot.reply_to(
            message,
            f"ℹ️ {target.first_name} has no active warnings."
        )
        return

    warnings_db[key] = current - 1

    bot.send_message(
        message.chat.id,
        f"""
╔══════════════════════╗
║ 🟢 REALMX WARNING 🟢 ║
╚══════════════════════╝

👤 USER
{target.first_name}

🆔 USER ID
{target.id}

➖ WARNING REMOVED

⚠️ CURRENT WARNINGS
{warnings_db[key]} / 3

🛡️ MODERATOR
{message.from_user.first_name}

✅ STATUS
Warning Record Updated
""",
        reply_markup=vip_panel()
    )


# ==========================================
# /PURGE
# Usage: /purge 20
# Reply to a message and use /purge 20
# Maximum: 100 messages
# ==========================================

@bot.message_handler(commands=['purge'])
def purge_messages(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "🧹 Reply to the first message and use:\n/purge 20"
        )
        return

    try:

        parts = message.text.split()

        if len(parts) < 2:
            count = 10
        else:
            count = int(parts[1])

        if count < 1:
            bot.reply_to(
                message,
                "❌ Count must be at least 1."
            )
            return

        if count > 100:
            count = 100

        start_id = message.reply_to_message.message_id

        deleted = 0

        for msg_id in range(start_id, start_id + count):

            try:
                bot.delete_message(
                    message.chat.id,
                    msg_id
                )
                deleted += 1
            except:
                pass

        # Command message bhi delete karne ki koshish
        try:
            bot.delete_message(
                message.chat.id,
                message.message_id
            )
        except:
            pass

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 🧹 REALMX CLEANUP 🧹 ║
╚══════════════════════╝

🗑️ MESSAGES REMOVED
{deleted}

🛡️ MODERATOR
{message.from_user.first_name}

⚡ STATUS
Chat Successfully Cleaned
""",
            reply_markup=vip_panel()
        )

    except ValueError:
        bot.reply_to(
            message,
            "❌ Invalid number.\nExample: /purge 20"
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Purge Error: {e}"
        )


# ==========================================
# /PIN
# ==========================================

@bot.message_handler(commands=['pin'])
def pin_message(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "📌 Reply to a message and use /pin"
        )
        return

    try:

        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id,
            disable_notification=False
        )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 📌 REALMX NOTICE 📌 ║
╚══════════════════════╝

📍 MESSAGE
Pinned Successfully

🛡️ PINNED BY
{message.from_user.first_name}

⚡ STATUS
Important Message Secured
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Pin Error: {e}"
        )


# ==========================================
# /UNPIN
# ==========================================

@bot.message_handler(commands=['unpin'])
def unpin_message(message):

    if not is_admin(message.chat.id, message.from_user.id):
        return

    try:

        if message.reply_to_message:

            bot.unpin_chat_message(
                message.chat.id,
                message.reply_to_message.message_id
            )

        else:

            bot.unpin_all_chat_messages(
                message.chat.id
            )

        bot.send_message(
            message.chat.id,
            f"""
╔══════════════════════╗
║ 📍 REALMX NOTICE 📍 ║
╚══════════════════════╝

📌 ACTION
Pinned Message Removed

🛡️ MODERATOR
{message.from_user.first_name}

✅ STATUS
Successfully Unpinned
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Unpin Error: {e}"
        )

# ==========================================
# REALMX VIP STAFF MANAGEMENT — PART 1B
# ==========================================

# Staff ranks are stored in memory.
# Bot restart hone par ranks reset ho jayenge.

staff_ranks = {}


def get_staff_rank(chat_id, user_id):
    return staff_ranks.get((chat_id, user_id))


def set_staff_rank(chat_id, user_id, rank):
    staff_ranks[(chat_id, user_id)] = rank


def remove_staff_rank(chat_id, user_id):
    staff_ranks.pop((chat_id, user_id), None)


def staff_target(message):
    if not message.reply_to_message:
        bot.reply_to(
            message,
            "❌ Kisi member ke message ko reply karke command use karo."
        )
        return None

    return message.reply_to_message.from_user


def can_manage_staff(message):
    return is_admin(message.chat.id, message.from_user.id)


# ==========================================
# /PROMOTE1
# REALM KEEPER
# ==========================================

@bot.message_handler(commands=['promote1'])
def promote1(message):

    if not can_manage_staff(message):
        return

    target = staff_target(message)

    if not target:
        return

    if target.is_bot:
        bot.reply_to(message, "❌ Bot ko staff rank nahi diya ja sakta.")
        return

    if target.id == message.from_user.id:
        bot.reply_to(message, "❌ Khud ko promote nahi kar sakte.")
        return

    if is_admin(message.chat.id, target.id):
        bot.reply_to(
            message,
            "❌ Telegram Administrator ko custom staff rank nahi diya ja sakta."
        )
        return

    set_staff_rank(
        message.chat.id,
        target.id,
        "Realm Keeper"
    )

    bot.send_message(
        message.chat.id,
        f"""
╔══════════════════════════╗
║ 🥉 REALMX STAFF SYSTEM 🥉 ║
╚══════════════════════════╝

👤 MEMBER
{target.first_name}

🎖️ NEW RANK
Realm Keeper

🛡️ PERMISSIONS
• Warn
• Delete

👑 APPOINTED BY
{message.from_user.first_name}

✅ STATUS
Staff Rank Activated
""",
        reply_markup=vip_panel()
    )


# ==========================================
# /PROMOTE2
# REALM GUARDIAN
# ==========================================

@bot.message_handler(commands=['promote2'])
def promote2(message):

    if not can_manage_staff(message):
        return

    target = staff_target(message)

    if not target:
        return

    if target.is_bot:
        bot.reply_to(message, "❌ Bot ko staff rank nahi diya ja sakta.")
        return

    if target.id == message.from_user.id:
        bot.reply_to(message, "❌ Khud ko promote nahi kar sakte.")
        return

    if is_admin(message.chat.id, target.id):
        bot.reply_to(
            message,
            "❌ Telegram Administrator ko custom staff rank nahi diya ja sakta."
        )
        return

    set_staff_rank(
        message.chat.id,
        target.id,
        "Realm Guardian"
    )

    bot.send_message(
        message.chat.id,
        f"""
╔══════════════════════════╗
║ 🥈 REALMX STAFF SYSTEM 🥈 ║
╚══════════════════════════╝

👤 MEMBER
{target.first_name}

🎖️ NEW RANK
Realm Guardian

🛡️ PERMISSIONS
• Warn
• Delete
• Mute
• Pin

👑 APPOINTED BY
{message.from_user.first_name}

✅ STATUS
Staff Rank Activated
""",
        reply_markup=vip_panel()
    )


# ==========================================
# /PROMOTE3
# REALM COMMANDER
# ==========================================

@bot.message_handler(commands=['promote3'])
def promote3(message):

    if not can_manage_staff(message):
        return

    target = staff_target(message)

    if not target:
        return

    if target.is_bot:
        bot.reply_to(message, "❌ Bot ko staff rank nahi diya ja sakta.")
        return

    if target.id == message.from_user.id:
        bot.reply_to(message, "❌ Khud ko promote nahi kar sakte.")
        return

    if is_admin(message.chat.id, target.id):
        bot.reply_to(
            message,
            "❌ Ye user already Telegram Administrator hai."
        )
        return

    try:
        bot.promote_chat_member(
            message.chat.id,
            target.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_invite_users=True,
            can_change_info=False,
            can_promote_members=False
        )

        set_staff_rank(
            message.chat.id,
            target.id,
            "Realm Commander"
        )

        bot.send_message(
            message.chat.id,
            f"""
╔════════════════════════════╗
║ 🥇 REALMX COMMANDER 🥇 ║
╚════════════════════════════╝

👤 MEMBER
{target.first_name}

🎖️ RANK
Realm Commander

🛡️ ACCESS
Full Moderation Admin

⚔️ PERMISSIONS
• Manage Chat
• Delete Messages
• Ban / Restrict
• Pin Messages
• Invite Users

👑 APPOINTED BY
{message.from_user.first_name}

✅ STATUS
Commander Activated
""",
            reply_markup=vip_panel()
        )

    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Telegram Admin Promotion Failed:\n{e}"
        )


# ==========================================
# /DEMOTE
# ==========================================

@bot.message_handler(commands=['demote'])
def demote(message):

    if not can_manage_staff(message):
        return

    target = staff_target(message)

    if not target:
        return

    # Custom staff rank remove
    old_rank = get_staff_rank(
        message.chat.id,
        target.id
    )

    if old_rank:
        remove_staff_rank(
            message.chat.id,
            target.id
        )

    # Agar Telegram admin hai to demote bhi karo
    try:

        member = bot.get_chat_member(
            message.chat.id,
            target.id
        )

        if member.status == "administrator":

            # Bot sirf apne diye hue admin ko demote kar sakta hai,
            # aur bot ke paas can_promote_members permission honi chahiye.
            bot.promote_chat_member(
                message.chat.id,
                target.id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )

    except:
        pass

    bot.send_message(
        message.chat.id,
        f"""
╔══════════════════════════╗
║ ⬇️ REALMX STAFF SYSTEM ⬇️ ║
╚══════════════════════════╝

👤 MEMBER
{target.first_name}

🎖️ PREVIOUS RANK
{old_rank or "No Custom Rank"}

❌ STATUS
Staff Access Removed

🛡️ ACTION BY
{message.from_user.first_name}

✅ REALMX STAFF SYSTEM
Updated Successfully
""",
        reply_markup=vip_panel()
            )

bot.infinity_polling()
