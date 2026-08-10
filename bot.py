import telebot

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot Online Hai 🚀")

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "Pong 🏓")

bot.infinity_polling()
