import telebot

# =========================
# BOT CONFIG
# =========================

TOKEN = "8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w"

OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"

SUPPORT_CHANNEL = "https://t.me/realmXsupport"
SUPPORT_GROUP = "https://t.me/+6BXS6AfvJPQ2OTI1"

BOT_NAME = "REALMX HELPER BOT"

# =========================
# BOT START
# =========================

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    text = f"""
🌌 {BOT_NAME}

👑 Owner: {OWNER_USERNAME}

📢 Support Channel:
{SUPPORT_CHANNEL}

💬 Support Group:
{SUPPORT_GROUP}
"""

    bot.reply_to(message, text)


@bot.message_handler(commands=['owner'])
def owner(message):
    bot.reply_to(
        message,
        f"👑 Owner: {OWNER_USERNAME}\n🆔 Owner ID: {OWNER_ID}"
    )


@bot.message_handler(commands=['support'])
def support(message):
    bot.reply_to(
        message,
        f"📢 Channel:\n{SUPPORT_CHANNEL}\n\n💬 Group:\n{SUPPORT_GROUP}"
    )


bot.infinity_polling()
