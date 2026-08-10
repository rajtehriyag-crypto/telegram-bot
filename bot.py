import telebot

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot Online Hai 🚀")

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "Pong 🏓")

@bot.message_handler(commands=['id'])
def get_id(message):
    bot.reply_to(message, f"👤 User ID: {message.from_user.id}\n💬 Chat ID: {message.chat.id}")
@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(message, "🤖 Bot Version 1.0\n👑 Owner: Prashant Sharma")

@bot.message_handler(commands=['info'])
def info(message):
    user = message.from_user
    bot.reply_to(
        message,
        f"👤 Name: {user.first_name}\n🆔 ID: {user.id}\n📛 Username: @{user.username}"
    )

@bot.message_handler(commands=['rules'])
def rules(message):
    bot.reply_to(message, "📜 Group Rules:\n1. No Spam\n2. Respect Everyone")

@bot.message_handler(commands=['admins'])
def admins(message):
    bot.reply_to(message, "🛡️ Use Telegram admin list to view admins.")

@bot.message_handler(commands=['dice'])
def dice(message):
    bot.send_dice(message.chat.id)

@bot.message_handler(commands=['coin'])
def coin(message):
    import random
    bot.reply_to(message, random.choice(["🪙 Head", "🪙 Tail"]))

@bot.message_handler(commands=['version'])
def version(message):
    bot.reply_to(message, "🤖 Version: 1.0")

@bot.message_handler(commands=['uptime'])
def uptime(message):
    bot.reply_to(message, "🟢 Bot is Online")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(
        message,
        "/start\n/ping\n/id\n/about\n/info\n/rules\n/admins\n/dice\n/coin\n/version\n/uptime"
    )

@bot.message_handler(commands=['report'])
def report(message):
    bot.reply_to(message, "📢 Report received.")
    from telebot import types

@bot.message_handler(commands=['kick'])
def kick_user(message):
    if message.reply_to_message:
        bot.kick_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, "👢 User kicked.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.reply_to_message:
        bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        bot.reply_to(message, "🔨 User banned.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    bot.reply_to(message, "ℹ️ Unban command setup later with user ID support.")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if message.reply_to_message:
        permissions = types.ChatPermissions(can_send_messages=False)
        bot.restrict_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id,
            permissions
        )
        bot.reply_to(message, "🔇 User muted.")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if message.reply_to_message:
        permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        bot.restrict_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id,
            permissions
        )
        bot.reply_to(message, "🔊 User unmuted.")

@bot.message_handler(commands=['delete'])
def delete_msg(message):
    if message.reply_to_message:
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)

@bot.message_handler(commands=['pin'])
def pin_msg(message):
    if message.reply_to_message:
        bot.pin_chat_message(
            message.chat.id,
            message.reply_to_message.message_id
        )
        bot.reply_to(message, "📌 Message pinned.")

@bot.message_handler(commands=['unpin'])
def unpin_msg(message):
    bot.unpin_all_chat_messages(message.chat.id)
    bot.reply_to(message, "📍 Messages unpinned.")
    
bot.infinity_polling()
