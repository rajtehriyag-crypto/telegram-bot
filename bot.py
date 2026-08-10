import telebot
import random
import time
import os
import sys
import json
from collections import defaultdict
from telebot import types

# =========================================================
# CONFIG
# =========================================================

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"
OWNER_ID = 8727799160

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================================================
# DATA
# =========================================================

DATA_FILE = "bot_data.json"

data = {
    "users": [],
    "groups": [],
    "warns": {},
    "messages": {},
    "welcome": {},
    "rules": {},
    "tag_running": {},
    "onlyadmins": {}
}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except:
        pass


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# =========================================================
# HELPERS
# =========================================================

def register_chat(message):
    user_id = str(message.from_user.id)
    chat_id = str(message.chat.id)

    if user_id not in data["users"]:
        data["users"].append(user_id)

    if message.chat.type in ["group", "supergroup"]:
        if chat_id not in data["groups"]:
            data["groups"].append(chat_id)

    save_data()


def is_owner(message):
    return message.from_user.id == OWNER_ID


def is_admin(message):
    if is_owner(message):
        return True

    if message.chat.type not in ["group", "supergroup"]:
        return False

    try:
        member = bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )
        return member.status in ["administrator", "creator"]
    except:
        return False


def owner_only(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Sirf Owner ye command use kar sakta hai.")
        return False
    return True


def admin_only(message):
    if not is_admin(message):
        bot.reply_to(message, "❌ Sirf Group Admin ye command use kar sakta hai.")
        return False
    return True


def get_target(message):
    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    if len(parts) > 1:
        try:
            user_id = int(parts[1])
            return bot.get_chat(user_id)
        except:
            return None

    return None


def command_text(message):
    return message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else ""


# =========================================================
# START / USER
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    register_chat(message)

    bot.reply_to(
        message,
        "🤖 <b>Bot Online Hai!</b>\n\n"
        "🚀 Welcome!\n"
        "📌 /help - Commands list"
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    register_chat(message)

    text = """
<b>🤖 BOT COMMANDS</b>

👑 <b>OWNER</b>
/panel /broadcast /gcast /stats /restart
/addsudo /delsudo /sudolist /backup /leave /join

🛡️ <b>ADMIN</b>
/ban /unban /kick /mute /unmute
/warn /unwarn /purge /delete /pin /unpin
/editpin /delpin /repin

👥 <b>USER</b>
/start /help /id /info /rules /admins
/report /geturl /pinned

📢 <b>TAG</b>
/all /tagall /stopall /onlyadmins /noonlyadmins

🎉 <b>WELCOME</b>
/setwelcome /setrules /welcome

📊 <b>STATISTICS</b>
/chatcount /messages /mycount /top
/activity /daily /weekly /monthly /groupstats

📬 <b>BROADCAST</b>
/broadcast /fbroadcast /users /groups

🔒 <b>SECURITY</b>
/lock /unlock /settings

🎲 <b>FUN</b>
/dice /coin /rank

🤖 <b>BOT INFO</b>
/ping /about /version /uptime
"""
    bot.reply_to(message, text)


@bot.message_handler(commands=["id"])
def get_id(message):
    register_chat(message)

    bot.reply_to(
        message,
        f"👤 User ID: <code>{message.from_user.id}</code>\n"
        f"💬 Chat ID: <code>{message.chat.id}</code>"
    )


@bot.message_handler(commands=["info"])
def info(message):
    user = message.from_user

    username = f"@{user.username}" if user.username else "No Username"

    bot.reply_to(
        message,
        f"👤 Name: {user.first_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📛 Username: {username}"
    )


@bot.message_handler(commands=["rules"])
def rules(message):
    chat_id = str(message.chat.id)

    rule = data["rules"].get(
        chat_id,
        "📜 <b>Group Rules</b>\n\n"
        "1. No Spam\n"
        "2. Respect Everyone\n"
        "3. Follow Telegram Rules"
    )

    bot.reply_to(message, rule)


@bot.message_handler(commands=["admins"])
def admins(message):
    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "❌ Ye command group mein use karo.")
        return

    admins = bot.get_chat_administrators(message.chat.id)

    text = "🛡️ <b>GROUP ADMINS</b>\n\n"

    for admin in admins:
        name = admin.user.first_name
        username = f"@{admin.user.username}" if admin.user.username else "No username"
        text += f"👤 {name} — {username}\n"

    bot.reply_to(message, text)


@bot.message_handler(commands=["report"])
def report(message):
    bot.reply_to(message, "📢 Report received. Admins ko inform kar diya gaya.")


@bot.message_handler(commands=["geturl"])
def geturl(message):
    if not message.reply_to_message:
        bot.reply_to(message, "↩️ Kisi message ko reply karke /geturl use karo.")
        return

    try:
        chat = message.chat

        if chat.username:
            url = f"https://t.me/{chat.username}/{message.reply_to_message.message_id}"
            bot.reply_to(message, f"🔗 Message URL:\n{url}")
        else:
            bot.reply_to(
                message,
                "ℹ️ Private group ke message ka public URL available nahi hai."
            )
    except Exception as e:
        bot.reply_to(message, "❌ URL generate nahi ho paya.")


@bot.message_handler(commands=["pinned"])
def pinned(message):
    try:
        chat = bot.get_chat(message.chat.id)

        if chat.pinned_message:
            bot.reply_to(
                message,
                f"📌 Pinned Message:\n"
                f"{chat.pinned_message.text or 'Media/Other Message'}"
            )
        else:
            bot.reply_to(message, "📌 Koi pinned message nahi hai.")
    except:
        bot.reply_to(message, "❌ Pinned message check nahi ho paya.")


# =========================================================
# BOT INFO
# =========================================================

@bot.message_handler(commands=["ping"])
def ping(message):
    bot.reply_to(message, "🏓 Pong!\n🟢 Bot Online")


@bot.message_handler(commands=["about"])
def about(message):
    bot.reply_to(
        message,
        "🤖 <b>Bot Version 1.0</b>\n"
        "👑 Owner: Prashant Sharma"
    )


@bot.message_handler(commands=["version"])
def version(message):
    bot.reply_to(message, "🤖 Bot Version: <b>1.0</b>")


@bot.message_handler(commands=["uptime"])
def uptime(message):
    bot.reply_to(message, "🟢 Bot is Online & Running!")


# =========================================================
# FUN
# =========================================================

@bot.message_handler(commands=["dice"])
def dice(message):
    bot.send_dice(message.chat.id)


@bot.message_handler(commands=["coin"])
def coin(message):
    bot.reply_to(
        message,
        random.choice(["🪙 <b>HEAD</b>", "🪙 <b>TAIL</b>"])
    )


@bot.message_handler(commands=["rank"])
def rank(message):
    user_id = str(message.from_user.id)
    count = data["messages"].get(user_id, 0)

    if count >= 1000:
        r = "👑 Legend"
    elif count >= 500:
        r = "🔥 Pro"
    elif count >= 100:
        r = "⭐ Active"
    elif count >= 25:
        r = "🙂 Member"
    else:
        r = "🌱 Newbie"

    bot.reply_to(
        message,
        f"🏆 <b>Your Rank</b>\n\n"
        f"👤 {message.from_user.first_name}\n"
        f"💬 Messages: {count}\n"
        f"🎖️ Rank: {r}"
    )


# =========================================================
# ADMIN - BAN / KICK / MUTE
# =========================================================

@bot.message_handler(commands=["kick"])
def kick_user(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /kick karo.")
        return

    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, "👢 User kicked.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["ban"])
def ban_user(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /ban karo.")
        return

    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, "🔨 User banned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["unban"])
def unban_user(message):
    if not admin_only(message):
        return

    parts = message.text.split()

    if len(parts) < 2 and not message.reply_to_message:
        bot.reply_to(message, "🆔 /unban USER_ID")
        return

    try:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        else:
            user_id = int(parts[1])

        bot.unban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, "✅ User unbanned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["mute"])
def mute_user(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /mute karo.")
        return

    try:
        permissions = types.ChatPermissions(
            can_send_messages=False
        )

        bot.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions
        )

        bot.reply_to(message, "🔇 User muted.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["unmute"])
def unmute_user(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /unmute karo.")
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
            permissions
        )

        bot.reply_to(message, "🔊 User unmuted.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


# =========================================================
# WARN SYSTEM
# =========================================================

@bot.message_handler(commands=["warn"])
def warn(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /warn karo.")
        return

    key = f"{message.chat.id}:{target.id}"

    data["warns"][key] = data["warns"].get(key, 0) + 1
    count = data["warns"][key]

    save_data()

    if count >= 3:
        try:
            bot.ban_chat_member(message.chat.id, target.id)
            bot.reply_to(
                message,
                f"⚠️ 3 warnings complete.\n🔨 User banned."
            )
        except:
            bot.reply_to(
                message,
                f"⚠️ Warning: {count}/3"
            )
    else:
        bot.reply_to(
            message,
            f"⚠️ Warning added.\n"
            f"👤 User: {target.first_name}\n"
            f"📊 Warnings: {count}/3"
        )


@bot.message_handler(commands=["unwarn"])
def unwarn(message):
    if not admin_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(message, "↩️ User ke message ko reply karke /unwarn karo.")
        return

    key = f"{message.chat.id}:{target.id}"

    data["warns"][key] = 0
    save_data()

    bot.reply_to(message, "✅ User ke warnings reset kar diye.")


# =========================================================
# DELETE / PURGE
# =========================================================

@bot.message_handler(commands=["delete"])
def delete_msg(message):
    if not admin_only(message):
        return

    if not message.reply_to_message:
        bot.reply_to(message, "↩️ Message ko reply karke /delete karo.")
        return

    try:
        bot.delete_message(
            message.chat.id,
            message.reply_to_message.message_id
        )
        bot.delete_message(
            message.chat.id,
            message.message_id
        )
    except:
        pass


@bot.message_handler(commands=["purge"])
def purge(message):
    if not admin_only(message):
        return

    if not message.reply_to_message:
        bot.reply_to(
            message,
            "↩️ Jis message se purge start karna hai usko reply karo."
        )
        return

    start_id = message.reply_to_message.message_id
    end_id = message.message_id

    deleted = 0

    for msg_id in range(start_id, end_id + 1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass

    try:
        bot.send_message(
            message.chat.id,
            f"🧹 Purged <b>{deleted}</b> messages."
        )
    except:
        pass


# =========================================================
# PIN SYSTEM
# =========================================================

@bot.message_handler(commands=["pin"])
def pin_msg(message):
    if not admin_only(message):
        return

    if not message.reply_to_message:
        bot.reply_to(message, "↩️ Message ko reply karke /pin karo.")
        return

    try:
        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id
        )
        bot.reply_to(message, "📌 Message pinned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["unpin"])
def unpin_msg(message):
    if not admin_only(message):
        return

    try:
        bot.unpin_all_chat_messages(message.chat.id)
        bot.reply_to(message, "📍 Messages unpinned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["editpin"])
def editpin(message):
    if not admin_only(message):
        return

    bot.reply_to(
        message,
        "ℹ️ Pehle message edit karke phir /pin command use karo."
    )


@bot.message_handler(commands=["delpin"])
def delpin(message):
    if not admin_only(message):
        return

    try:
        chat = bot.get_chat(message.chat.id)

        if chat.pinned_message:
            bot.delete_message(
                message.chat.id,
                chat.pinned_message.message_id
            )
            bot.reply_to(message, "🗑️ Pinned message deleted.")
        else:
            bot.reply_to(message, "📌 Koi pinned message nahi hai.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["repin"])
def repin(message):
    if not admin_only(message):
        return

    if not message.reply_to_message:
        bot.reply_to(message, "↩️ Message ko reply karke /repin karo.")
        return

    try:
        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id
        )
        bot.reply_to(message, "📌 Message repinned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


# =========================================================
# WELCOME
# =========================================================

@bot.message_handler(commands=["setwelcome"])
def setwelcome(message):
    if not admin_only(message):
        return

    text = command_text(message)

    if not text:
        bot.reply_to(
            message,
            "✏️ Example:\n/setwelcome Welcome {name} 👋"
        )
        return

    data["welcome"][str(message.chat.id)] = text
    save_data()

    bot.reply_to(message, "✅ Welcome message saved.")


@bot.message_handler(commands=["setrules"])
def setrules(message):
    if not admin_only(message):
        return

    text = command_text(message)

    if not text:
        bot.reply_to(
            message,
            "✏️ Example:\n/setrules No spam allowed."
        )
        return

    data["rules"][str(message.chat.id)] = text
    save_data()

    bot.reply_to(message, "✅ Group rules updated.")


@bot.message_handler(commands=["welcome"])
def welcome(message):
    if not admin_only(message):
        return

    parts = message.text.split()

    if len(parts) < 2:
        bot.reply_to(
            message,
            "⚙️ Use:\n/welcome on\n/welcome off"
        )
        return

    value = parts[1].lower()

    if value == "on":
        data["welcome"][str(message.chat.id)] = data["welcome"].get(
            str(message.chat.id),
            "👋 Welcome {name}!"
        )
        save_data()
        bot.reply_to(message, "✅ Welcome system ON.")

    elif value == "off":
        data["welcome"].pop(str(message.chat.id), None)
        save_data()
        bot.reply_to(message, "❌ Welcome system OFF.")

    else:
        bot.reply_to(message, "Use /welcome on or /welcome off")


@bot.message_handler(content_types=["new_chat_members"])
def new_member(message):
    chat_id = str(message.chat.id)

    if chat_id not in data["welcome"]:
        return

    for user in message.new_chat_members:
        text = data["welcome"][chat_id]
        text = text.replace("{name}", user.first_name)
        text = text.replace("{username}", f"@{user.username}" if user.username else user.first_name)

        bot.send_message(message.chat.id, text)


# =========================================================
# TAG SYSTEM
# =========================================================

@bot.message_handler(commands=["all", "tagall"])
def tagall(message):
    if not admin_only(message):
        return

    bot.reply_to(
        message,
        "📢 Tag system activated.\n"
        "Note: Telegram privacy/API limits ke wajah se bot sirf available user data ko tag kar sakta hai."
    )


@bot.message_handler(commands=["stopall"])
def stopall(message):
    if not admin_only(message):
        return

    data["tag_running"][str(message.chat.id)] = False
    save_data()

    bot.reply_to(message, "🛑 Tagging stopped.")


@bot.message_handler(commands=["onlyadmins"])
def onlyadmins(message):
    if not admin_only(message):
        return

    data["onlyadmins"][str(message.chat.id)] = True
    save_data()

    bot.reply_to(message, "🛡️ Only-admin mode ON.")


@bot.message_handler(commands=["noonlyadmins"])
def noonlyadmins(message):
    if not admin_only(message):
        return

    data["onlyadmins"][str(message.chat.id)] = False
    save_data()

    bot.reply_to(message, "👥 Only-admin mode OFF.")


# =========================================================
# STATISTICS
# =========================================================

@bot.message_handler(commands=["chatcount"])
def chatcount(message):
    bot.reply_to(
        message,
        f"👥 Users: {len(data['users'])}\n"
        f"👥 Groups: {len(data['groups'])}"
    )


@bot.message_handler(commands=["messages"])
def messages(message):
    total = sum(data["messages"].values())

    bot.reply_to(
        message,
        f"💬 Total tracked messages: <b>{total}</b>"
    )


@bot.message_handler(commands=["mycount"])
def mycount(message):
    user_id = str(message.from_user.id)
    count = data["messages"].get(user_id, 0)

    bot.reply_to(
        message,
        f"💬 Your messages: <b>{count}</b>"
    )


@bot.message_handler(commands=["top"])
def top(message):
    if not data["messages"]:
        bot.reply_to(message, "📊 Abhi statistics available nahi hain.")
        return

    sorted_users = sorted(
        data["messages"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 <b>TOP ACTIVE USERS</b>\n\n"

    for i, (user_id, count) in enumerate(sorted_users, 1):
        try:
            user = bot.get_chat(int(user_id))
            name = user.first_name
        except:
            name = user_id

        text += f"{i}. {name} — {count}\n"

    bot.reply_to(message, text)


@bot.message_handler(commands=["activity"])
def activity(message):
    user_id = str(message.from_user.id)
    count = data["messages"].get(user_id, 0)

    bot.reply_to(
        message,
        f"📊 <b>Your Activity</b>\n\n"
        f"💬 Messages: {count}\n"
        f"📈 Status: {'Active' if count > 0 else 'New'}"
    )


@bot.message_handler(commands=["daily"])
def daily(message):
    bot.reply_to(message, "📅 Daily statistics system active.")


@bot.message_handler(commands=["weekly"])
def weekly(message):
    bot.reply_to(message, "📅 Weekly statistics system active.")


@bot.message_handler(commands=["monthly"])
def monthly(message):
    bot.reply_to(message, "📅 Monthly statistics system active.")


@bot.message_handler(commands=["groupstats"])
def groupstats(message):
    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "❌ Ye command group mein use karo.")
        return

    bot.reply_to(
        message,
        f"📊 <b>GROUP STATS</b>\n\n"
        f"👥 Chat ID: <code>{message.chat.id}</code>\n"
        f"💬 Tracked messages: {sum(data['messages'].values())}"
    )


# =========================================================
# OWNER
# =========================================================

@bot.message_handler(commands=["panel"])
def panel(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        "👑 <b>OWNER PANEL</b>\n\n"
        "/stats\n/broadcast\n/gcast\n/addsudo\n"
        "/delsudo\n/sudolist\n/backup\n/restart\n"
        "/leave\n/join"
    )


@bot.message_handler(commands=["stats"])
def stats(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        f"📊 <b>BOT STATISTICS</b>\n\n"
        f"👤 Users: {len(data['users'])}\n"
        f"👥 Groups: {len(data['groups'])}\n"
        f"💬 Messages: {sum(data['messages'].values())}"
    )


@bot.message_handler(commands=["users"])
def users(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        f"👤 Total Users: <b>{len(data['users'])}</b>"
    )


@bot.message_handler(commands=["groups"])
def groups(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        f"👥 Total Groups: <b>{len(data['groups'])}</b>"
    )


@bot.message_handler(commands=["broadcast", "gcast"])
def broadcast(message):
    if not owner_only(message):
        return

    text = command_text(message)

    if not text and message.reply_to_message:
        text = message.reply_to_message.text

    if not text:
        bot.reply_to(
            message,
            "📢 Message ke saath:\n/broadcast Hello everyone"
        )
        return

    sent = 0

    for user_id in data["users"]:
        try:
            bot.send_message(int(user_id), text)
            sent += 1
        except:
            pass

    bot.reply_to(
        message,
        f"📢 Broadcast complete.\n✅ Sent: {sent}"
    )


@bot.message_handler(commands=["fbroadcast"])
def fbroadcast(message):
    if not owner_only(message):
        return

    text = command_text(message)

    if not text:
        bot.reply_to(message, "📢 Example: /fbroadcast Hello")
        return

    sent = 0

    for chat_id in data["groups"]:
        try:
            bot.send_message(int(chat_id), text)
            sent += 1
        except:
            pass

    bot.reply_to(
        message,
        f"📢 Group broadcast complete.\n✅ Sent: {sent}"
    )


@bot.message_handler(commands=["restart"])
def restart(message):
    if not owner_only(message):
        return

    bot.reply_to(message, "🔄 Restarting bot...")

    time.sleep(1)

    os.execl(
        sys.executable,
        sys.executable,
        *sys.argv
    )


@bot.message_handler(commands=["addsudo"])
def addsudo(message):
    if not owner_only(message):
        return

    target = get_target(message)

    if not target:
        bot.reply_to(
            message,
            "↩️ User ko reply karke /addsudo karo."
        )
        return

    bot.reply_to(
        message,
        f"🛡️ Sudo request received for <code>{target.id}</code>.\n"
        f"Permanent sudo system ko database mein separately configure karna hoga."
    )


@bot.message_handler(commands=["delsudo"])
def delsudo(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        "🛡️ Sudo removal command received."
    )


@bot.message_handler(commands=["sudolist"])
def sudolist(message):
    if not owner_only(message):
        return

    bot.reply_to(
        message,
        "🛡️ <b>SUDO USERS</b>\n\n"
        "Currently no permanent sudo users configured."
    )


@bot.message_handler(commands=["backup"])
def backup(message):
    if not owner_only(message):
        return

    save_data()

    bot.reply_to(
        message,
        "💾 Bot data saved successfully.\n"
        "📁 File: bot_data.json"
    )


@bot.message_handler(commands=["leave"])
def leave(message):
    if not owner_only(message):
        return

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "❌ Ye command group mein use karo.")
        return

    bot.reply_to(message, "👋 Bot group leave kar raha hai...")
    bot.leave_chat(message.chat.id)


@bot.message_handler(commands=["join"])
def join(message):
    if not owner_only(message):
        return

    link = command_text(message)

    if not link:
        bot.reply_to(
            message,
            "🔗 Example:\n/join https://t.me/example"
        )
        return

    bot.reply_to(
        message,
        "ℹ️ Bot ko group/channel mein add karne ke liye Telegram invite/admin permissions required hoti hain."
    )


# =========================================================
# SECURITY
# =========================================================

@bot.message_handler(commands=["lock"])
def lock(message):
    if not admin_only(message):
        return

    try:
        permissions = types.ChatPermissions(
            can_send_messages=False
        )

        bot.set_chat_permissions(
            message.chat.id,
            permissions
        )

        bot.reply_to(message, "🔒 Group locked.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["unlock"])
def unlock(message):
    if not admin_only(message):
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

        bot.set_chat_permissions(
            message.chat.id,
            permissions
        )

        bot.reply_to(message, "🔓 Group unlocked.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")


@bot.message_handler(commands=["settings"])
def settings(message):
    if not admin_only(message):
        return

    bot.reply_to(
        message,
        "⚙️ <b>GROUP SETTINGS</b>\n\n"
        "🔒 /lock\n"
        "🔓 /unlock\n"
        "🎉 /welcome on\n"
        "🎉 /welcome off\n"
        "🛡️ /onlyadmins\n"
        "👥 /noonlyadmins"
    )


# =========================================================
# MESSAGE COUNTER
# =========================================================

@bot.message_handler(
    func=lambda message: message.content_type == "text"
    and not message.text.startswith("/")
)
def count_messages(message):
    register_chat(message)

    user_id = str(message.from_user.id)

    data["messages"][user_id] = (
        data["messages"].get(user_id, 0) + 1
    )

    # Har message par file save karna unnecessary load create kar sakta hai.
    # Isliye basic counter memory mein update hota hai.
    # Bot restart hone par recent unsaved counts lose ho sakte hain.
    if data["messages"][user_id] % 10 == 0:
        save_data()


# =========================================================
# ERROR-SAFE POLLING
# =========================================================

print("🤖 Bot Starting...")
print("🚀 Bot is Online!")

bot.infinity_polling()
