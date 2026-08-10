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

bot.infinity_polling()
