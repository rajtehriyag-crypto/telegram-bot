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
    
bot.infinity_polling()
