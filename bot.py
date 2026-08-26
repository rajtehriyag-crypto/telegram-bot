import sqlite3
import time
import random
import threading
import re
from datetime import datetime, timezone, timedelta

import telebot
from telebot import types

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
BOT_USERNAME = "zynoxgamingbot"
OWNER_ID = 8727799160
OWNER_USERNAME = "internationalpanditG"
SUPPORT_CHANNEL = "https://t.me/+CS-ZvjWSB1oxZjZl"
SUPPORT_GROUP = "https://t.me/+97rox0VQWXNiMzg1"
SUPPORT_CHANNEL_ID = None   # optional: set numeric channel id for auto-verify
SUPPORT_GROUP_ID = None     # optional: set numeric group id for auto-verify
IST = timezone(timedelta(hours=5, minutes=30))
DB_PATH = "zynox.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db_lock = threading.Lock()

# ============================================================
# DATABASE
# ============================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        coins INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        rank TEXT DEFAULT 'Bronze',
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        daily_claim_date TEXT,
        dice_rolls_today INTEGER DEFAULT 0,
        dice_date TEXT,
        streak INTEGER DEFAULT 0,
        started_bot INTEGER DEFAULT 0,
        created_at TEXT,
        is_vip INTEGER DEFAULT 0,
        vip_expiry TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS groups(
        group_id INTEGER PRIMARY KEY,
        title TEXT,
        added_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS group_stats(
        group_id INTEGER,
        user_id INTEGER,
        xp INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        PRIMARY KEY(group_id, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS wallet(
        id INTEGER PRIMARY KEY CHECK(id=1),
        balance INTEGER DEFAULT 0
    )""")
    c.execute("INSERT OR IGNORE INTO wallet(id, balance) VALUES(1, 0)")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions(
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        type TEXT,
        note TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS matches(
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game TEXT,
        group_id INTEGER,
        host_id INTEGER,
        bet INTEGER,
        player2_id INTEGER,
        status TEXT,
        created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS vip_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        plan TEXT,
        payment_proof TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )""")
    conn.commit()
    conn.close()

def now_str():
    return datetime.now(IST).isoformat()

def today_ist():
    return datetime.now(IST).strftime("%Y-%m-%d")

def log_tx(user_id, amount, ttype, note=""):
    conn = get_conn()
    conn.execute("INSERT INTO transactions(user_id,amount,type,note,created_at) VALUES(?,?,?,?,?)",
                 (user_id, amount, ttype, note, now_str()))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def create_user_if_missing(user_id, username, first_name):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        exists = c.fetchone()
        if not exists:
            c.execute("""INSERT INTO users(user_id, username, first_name, created_at)
                         VALUES(?,?,?,?)""", (user_id, username or "", first_name or "", now_str()))
            conn.commit()
        else:
            c.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                       (username or "", first_name or "", user_id))
            conn.commit()
        conn.close()

def mark_started(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET started_bot=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def add_coins(user_id, amount, note=""):
    """Atomic coin add/subtract. Prevents negative balance."""
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        new_balance = row[0] + amount
        if new_balance < 0:
            conn.close()
            return False
        c.execute("UPDATE users SET coins=? WHERE user_id=?", (new_balance, user_id))
        conn.commit()
        conn.close()
    log_tx(user_id, amount, "coin_change", note)
    return True

def wallet_balance():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT balance FROM wallet WHERE id=1")
    b = c.fetchone()[0]
    conn.close()
    return b

def wallet_add(amount):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE wallet SET balance = balance + ? WHERE id=1", (amount,))
        conn.commit()
        conn.close()

# ============================================================
# LEVEL / RANK LOGIC
# ============================================================
LEVEL_TABLE = [0, 0, 100, 250, 500, 800, 1150, 1550, 2000, 2500, 3100]

def xp_for_level(level):
    if level <= 10:
        return LEVEL_TABLE[level]
    extra = level - 10
    return 3100 + extra * (600 + extra * 50)

def level_from_xp(xp):
    level = 1
    while xp_for_level(level + 1) <= xp:
        level += 1
    return level

def rank_from_level(level):
    if level >= 40:
        return "🔥 Legend"
    if level >= 30:
        return "👑 Master"
    if level >= 20:
        return "💎 Diamond"
    if level >= 12:
        return "🥇 Gold"
    if level >= 6:
        return "🥈 Silver"
    return "🥉 Bronze"

def add_xp(user_id, amount):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT xp FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return
        new_xp = row[0] + amount
        new_level = level_from_xp(new_xp)
        new_rank = rank_from_level(new_level)
        c.execute("UPDATE users SET xp=?, level=?, rank=? WHERE user_id=?",
                   (new_xp, new_level, new_rank, user_id))
        conn.commit()
        conn.close()

def add_group_stat(group_id, user_id, xp=0, coins=0, wins=0):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO group_stats(group_id,user_id) VALUES(?,?)", (group_id, user_id))
    c.execute("""UPDATE group_stats SET xp=xp+?, coins=coins+?, wins=wins+?
                 WHERE group_id=? AND user_id=?""", (xp, coins, wins, group_id, user_id))
    conn.commit()
    conn.close()

# ============================================================
# VIP FUNCTIONS
# ============================================================
VIP_BENEFITS = {
    "weekly": {"price": 2000, "duration": 7, "daily_bonus": 100, "dice_bonus": 2},
    "monthly": {"price": 7000, "duration": 30, "daily_bonus": 300, "dice_bonus": 4},
    "yearly": {"price": 75000, "duration": 365, "daily_bonus": 1000, "dice_bonus": 6}
}

def check_vip(user_id):
    """Check if user has active VIP"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    is_vip, expiry = row
    if is_vip and expiry:
        expiry_date = datetime.fromisoformat(expiry)
        if expiry_date > datetime.now(IST):
            return True
        # Expired - auto reset
        conn = get_conn()
        conn.execute("UPDATE users SET is_vip=0, vip_expiry=NULL WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        return False
    return False

def get_vip_benefits(user_id):
    """Get VIP benefits for user"""
    if not check_vip(user_id):
        return None
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT vip_expiry FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    days_left = (datetime.fromisoformat(row[0]) - datetime.now(IST)).days
    return {
        "daily_bonus": 300,  # Default monthly benefits
        "dice_extra_rolls": 4,
        "days_left": days_left
    }

def activate_vip(user_id, plan):
    """Activate VIP for user"""
    if plan not in VIP_BENEFITS:
        return False
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT vip_expiry FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    current_expiry = datetime.now(IST)
    if row and row[0]:
        current_expiry = datetime.fromisoformat(row[0])
        if current_expiry < datetime.now(IST):
            current_expiry = datetime.now(IST)
    new_expiry = current_expiry + timedelta(days=VIP_BENEFITS[plan]["duration"])
    c.execute("UPDATE users SET is_vip=1, vip_expiry=? WHERE user_id=?", 
              (new_expiry.isoformat(), user_id))
    conn.commit()
    conn.close()
    return True

# ============================================================
# MEMBERSHIP CHECK
# ============================================================
def is_member(user_id, chat_id):
    if chat_id is None:
        return True
    try:
        m = bot.get_chat_member(chat_id, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False

def check_support_membership(user_id):
    """If channel/group IDs configured, verify. Else assume pass (manual config needed)."""
    ok_channel = is_member(user_id, SUPPORT_CHANNEL_ID) if SUPPORT_CHANNEL_ID else True
    ok_group = is_member(user_id, SUPPORT_GROUP_ID) if SUPPORT_GROUP_ID else True
    return ok_channel and ok_group

def membership_prompt(m):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL))
    kb.add(types.InlineKeyboardButton("👥 Support Group", url=SUPPORT_GROUP))
    kb.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_join"))
    bot.reply_to(m, box("⚠️ VERIFICATION REQUIRED",
        "🚫 Join Support Channel + Group\nto claim rewards!"), reply_markup=kb)

# ============================================================
# MESSAGE STYLE HELPER
# ============================================================
def box(title, body, footer=None):
    txt = f"╔══════════════════════╗\n{title}\n╚══════════════════════╝\n\n{body}"
    if footer:
        txt += f"\n\n━━━━━━━━━━━━━━━━━━━━━━\n{footer}\n━━━━━━━━━━━━━━━━━━━━━━"
    return txt

# ============================================================
# /start (DM ONLY)
# ============================================================
@bot.message_handler(commands=["start"])
def cmd_start(m):
    if m.chat.type != "private":
        return
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    mark_started(u.id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🎮 Games", callback_data="menu_games"),
            types.InlineKeyboardButton("👤 Profile", callback_data="menu_profile"))
    kb.add(types.InlineKeyboardButton("🪙 Balance", callback_data="menu_balance"),
            types.InlineKeyboardButton("🏆 Rank", callback_data="menu_rank"))
    kb.add(types.InlineKeyboardButton("📊 Leaderboard", callback_data="menu_leaderboard"),
            types.InlineKeyboardButton("🎁 Daily", callback_data="menu_daily"))
    kb.add(types.InlineKeyboardButton("👑 VIP", callback_data="menu_vip"),
            types.InlineKeyboardButton("❓ Help", callback_data="menu_help"))
    text = box("✅ 𝐙𝐘𝐍𝐎𝐗 𝐆𝐀𝐌𝐈𝐍𝐆 ✅",
        f"👋 Welcome, {u.first_name} 💎\n\n🎮 Games • 🪙 Coins • ⭐ XP\n📈 Levels • 🏆 Ranks\n👑 VIP Benefits",
        "🚀 Choose an option below")
    bot.send_message(m.chat.id, text, reply_markup=kb)

# ============================================================
# VIP COMMANDS
# ============================================================
@bot.message_handler(commands=["vip"])
def cmd_vip(m):
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    
    is_vip = check_vip(u.id)
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    
    if is_vip:
        benefits = get_vip_benefits(u.id)
        text = box("👑 VIP STATUS",
            f"✅ You are a VIP Member!\n\n"
            f"📅 Days Left: {benefits['days_left']}\n"
            f"🎁 Daily Bonus: +{benefits['daily_bonus']} Coins\n"
            f"🎲 Extra Dice Rolls: +{benefits['dice_extra_rolls']} per day\n\n"
            f"💎 VIP Perks:\n"
            f"• 2x daily rewards\n"
            f"• Exclusive games\n"
            f"• Priority support\n"
            f"• Special badges")
        kb.add(types.InlineKeyboardButton("🔄 Renew VIP", callback_data="vip_renew"))
        kb.add(types.InlineKeyboardButton("📋 Benefits", callback_data="vip_benefits"))
    else:
        text = box("👑 VIP MEMBERSHIP",
            "🚀 Unlock Premium Features!\n\n"
            "💎 VIP Benefits:\n"
            "• 2x Daily Rewards\n"
            "• Extra Dice Rolls\n"
            "• Exclusive Games\n"
            "• Priority Support\n"
            "• Special Rank Badge\n\n"
            "💰 Plans:\n"
            "Weekly: 2,000 Coins\n"
            "Monthly: 7,000 Coins\n"
            "Yearly: 75,000 Coins")
        kb.add(types.InlineKeyboardButton("💰 Buy VIP", callback_data="vip_buy"))
        kb.add(types.InlineKeyboardButton("📋 Benefits", callback_data="vip_benefits"))
    
    bot.reply_to(m, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vip_"))
def cb_vip(call):
    bot.answer_callback_query(call.id)
    u = call.from_user
    data = call.data
    
    if data == "vip_buy":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("📅 Weekly (2,000)", callback_data="vip_pay_weekly"))
        kb.add(types.InlineKeyboardButton("📆 Monthly (7,000)", callback_data="vip_pay_monthly"))
        kb.add(types.InlineKeyboardButton("📅 Yearly (75,000)", callback_data="vip_pay_yearly"))
        kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="vip_back"))
        bot.edit_message_text(box("💰 VIP PURCHASE", "Select your plan:"),
                             call.message.chat.id, call.message.message_id, reply_markup=kb)
    
    elif data.startswith("vip_pay_"):
        plan = data.split("_")[2]
        price = VIP_BENEFITS[plan]["price"]
        user_row = get_user(u.id)
        if user_row[3] < price:
            bot.edit_message_text(box("❌ INSUFFICIENT BALANCE", 
                f"You need {price} Coins for {plan} VIP.\nYour balance: {user_row[3]} Coins"),
                call.message.chat.id, call.message.message_id)
            return
        
        # Deduct coins and activate VIP
        if add_coins(u.id, -price, f"vip_{plan}"):
            activate_vip(u.id, plan)
            wallet_add(price)  # Add to bot wallet
            
            text = box("✅ VIP ACTIVATED",
                f"🎉 Congratulations! You are now a VIP Member!\n\n"
                f"📅 Plan: {plan.title()}\n"
                f"💎 Benefits activated!\n\n"
                f"Use /vip to view your status.")
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👑 VIP Panel", callback_data="vip_back"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            bot.edit_message_text("❌ Failed to process payment.", 
                                 call.message.chat.id, call.message.message_id)
    
    elif data == "vip_benefits":
        text = box("💎 VIP BENEFITS",
            "✨ VIP Perks:\n\n"
            "🎁 Daily Bonus: 2x coins\n"
            "🎲 Extra Dice Rolls: +4 per day\n"
            "🎮 Exclusive Games Access\n"
            "⭐ Special VIP Badge\n"
            "🛡️ Priority Support\n"
            "🏆 Higher XP Gain\n"
            "💰 Special Discounts\n\n"
            "💎 Become VIP today!")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="vip_back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    
    elif data == "vip_renew":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("📅 Weekly (2,000)", callback_data="vip_pay_weekly"))
        kb.add(types.InlineKeyboardButton("📆 Monthly (7,000)", callback_data="vip_pay_monthly"))
        kb.add(types.InlineKeyboardButton("📅 Yearly (75,000)", callback_data="vip_pay_yearly"))
        kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="vip_back"))
        bot.edit_message_text(box("🔄 RENEW VIP", "Extend your VIP membership:"),
                             call.message.chat.id, call.message.message_id, reply_markup=kb)
    
    elif data == "vip_back":
        cmd_vip(call.message)

# ============================================================
# MODIFIED DAILY WITH VIP
# ============================================================
DAILY_REWARD = 250
VIP_DAILY_BONUS = 500  # 2x for VIP

@bot.message_handler(commands=["daily"])
def cmd_daily(m):
    if m.chat.type != "private":
        return
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    row = get_user(u.id)
    if not row[15]:  # started_bot
        mark_started(u.id)
    if not check_support_membership(u.id):
        membership_prompt(m)
        return
    today = today_ist()
    last_claim = row[11]
    if last_claim == today:
        bot.reply_to(m, box("⚠️ ALREADY CLAIMED", "🕛 Come back after 12:00 AM IST reset!"))
        return
    
    # VIP bonus
    is_vip = check_vip(u.id)
    reward = DAILY_REWARD * 2 if is_vip else DAILY_REWARD
    vip_text = "💎 VIP Bonus Active! (2x)" if is_vip else ""
    
    conn = get_conn()
    conn.execute("UPDATE users SET daily_claim_date=? WHERE user_id=?", (today, u.id))
    conn.commit()
    conn.close()
    add_coins(u.id, reward, "daily_reward")
    bal = get_user(u.id)[3]
    
    text = box("🎁 DAILY REWARD",
        f"🎉 Daily Reward Claimed!\n\n"
        f"🪙 +{reward} Coins\n"
        f"💰 Balance : {bal}\n"
        f"{vip_text}\n\n"
        f"🔥 Come Back Tomorrow!")
    bot.reply_to(m, text)

# ============================================================
# MODIFIED DICE WITH VIP
# ============================================================
DICE_MAX = 6
DICE_REWARDS = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 100}
VIP_DICE_EXTRA = 4  # VIP gets 4 extra rolls

@bot.message_handler(commands=["dice"])
def cmd_dice(m):
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    today = today_ist()
    row = get_user(u.id)
    dice_date, rolls_today = row[13], row[12]
    
    if dice_date != today:
        rolls_today = 0
        conn = get_conn()
        conn.execute("UPDATE users SET dice_date=?, dice_rolls_today=0 WHERE user_id=?", (today, u.id))
        conn.commit()
        conn.close()
    
    # VIP extra rolls
    is_vip = check_vip(u.id)
    max_rolls = DICE_MAX + (VIP_DICE_EXTRA if is_vip else 0)
    vip_text = f"💎 VIP: {max_rolls} rolls/day" if is_vip else ""
    
    if rolls_today >= max_rolls:
        bot.reply_to(m, box("⚠️ NO ROLLS LEFT", 
            f"🕛 Rolls reset at 12:00 AM IST!\n{vip_text}"))
        return
    
    result = random.randint(1, 6)
    reward = DICE_REWARDS[result]
    # VIP bonus on dice
    if is_vip and result == 6:
        reward = 200  # Double reward for VIP on roll 6
    rolls_today += 1
    conn = get_conn()
    conn.execute("UPDATE users SET dice_rolls_today=? WHERE user_id=?", (rolls_today, u.id))
    conn.commit()
    conn.close()
    add_coins(u.id, reward, "dice_roll")
    if m.chat.type in ("group", "supergroup"):
        add_group_stat(m.chat.id, u.id, coins=reward)
    bal = get_user(u.id)[3]
    remaining = max_rolls - rolls_today
    
    if result == 6:
        text = box("⚡ STRIKE ⚡",
            f"🎲 Roll Result : 6️⃣\n\n💥 STRIKE!\n\n🪙 Reward : +{reward} Coins\n💰 Balance : {bal}\n{vip_text}",
            f"🎯 Rolls Left : {remaining}/{max_rolls}")
    else:
        text = box("🎲 DICE ROLL",
            f"🎲 Roll Result : {result}️⃣\n\n🪙 Reward : +{reward} Coins\n💰 Balance : {bal}\n{vip_text}",
            f"🎯 Rolls Left : {remaining}/{max_rolls}")
    bot.reply_to(m, text)

# ============================================================
# GROUP WELCOME
# ============================================================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(m):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO groups(group_id,title,added_at) VALUES(?,?,?)",
                 (m.chat.id, m.chat.title, now_str()))
    conn.commit()
    conn.close()
    for member in m.new_chat_members:
        if member.id == bot.get_me().id:
            continue
        create_user_if_missing(member.id, member.username, member.first_name)
        uname = f"@{member.username}" if member.username else "N/A"
        text = (f"╔═ 🎉✨ WELCOME ✨🎉 ═╗\n\n"
                f"👋 Welcome, {member.first_name} 💎\n\n"
                f"🆔 User ID : {member.id}\n"
                f"👤 Username : {uname}\n\n"
                f"🎮 Welcome To 🎮\n"
                f"✅ 𝐙𝐘𝐍𝐎𝐗 𝐆𝐀𝐌𝐈𝐍𝐆 ✅\n\n"
                f"╚══ 🚀💓 ENJOY 💓🚀 ══╝")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎮 START BOT", url=f"https://t.me/{BOT_USERNAME}?start=welcome"))
        bot.send_message(m.chat.id, text, reply_markup=kb)

# ============================================================
# /profile (UPDATED WITH VIP)
# ============================================================
def profile_text(row):
    user_id, username, first_name, coins, xp, level, rank_, games_played, wins, losses = row[:10]
    total = wins + losses
    winrate = round((wins / total) * 100, 1) if total else 0.0
    uname = f"@{username}" if username else "N/A"
    
    # Check VIP status
    is_vip = check_vip(user_id)
    vip_badge = " 👑 VIP" if is_vip else ""
    
    return box("👤 PROFILE",
        f"👤 Name : {first_name}{vip_badge}\n"
        f"🆔 User ID : {user_id}\n"
        f"👤 Username : {uname}\n\n"
        f"⭐ XP : {xp}\n"
        f"📈 Level : {level}\n"
        f"🥇 Rank : {rank_}\n\n"
        f"🪙 Coins : {coins}\n"
        f"🎮 Games Played : {games_played}\n"
        f"🏆 Wins : {wins}\n"
        f"💔 Losses : {losses}\n"
        f"📊 Win Rate : {winrate}%")

@bot.message_handler(commands=["profile"])
def cmd_profile(m):
    target_id = None
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
    else:
        parts = m.text.split()
        if len(parts) > 1 and parts[1].startswith("@"):
            uname = parts[1][1:]
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE username=?", (uname,))
            r = c.fetchone()
            conn.close()
            if r:
                target_id = r[0]
            else:
                bot.reply_to(m, "❌ User not found in database.")
                return
    if target_id is None:
        target_id = m.from_user.id
        create_user_if_missing(m.from_user.id, m.from_user.username, m.from_user.first_name)
    row = get_user(target_id)
    if not row:
        bot.reply_to(m, "❌ User not found.")
        return
    bot.reply_to(m, profile_text(row))

# ============================================================
# /rank
# ============================================================
@bot.message_handler(commands=["rank"])
def cmd_rank(m):
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    row = get_user(u.id)
    xp, level, rank_ = row[4], row[5], row[6]
    next_xp = xp_for_level(level + 1)
    to_next = next_xp - xp
    
    is_vip = check_vip(u.id)
    vip_badge = " 👑 VIP" if is_vip else ""
    
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE xp > ?", (xp,))
    global_pos = c.fetchone()[0] + 1
    group_pos = "N/A"
    if m.chat.type in ("group", "supergroup"):
        c.execute("SELECT COUNT(*) FROM group_stats WHERE group_id=? AND xp > (SELECT xp FROM group_stats WHERE group_id=? AND user_id=?)",
                   (m.chat.id, m.chat.id, u.id))
        group_pos = c.fetchone()[0] + 1
    conn.close()
    
    text = box("🏆 YOUR RANK",
        f"👤 {u.first_name}{vip_badge}\n\n"
        f"⭐ Level : {level}\n"
        f"📈 XP : {xp} / {next_xp}\n\n"
        f"🥇 Rank : {rank_}\n\n"
        f"🌎 Global : #{global_pos}\n"
        f"👥 This Group : #{group_pos}",
        f"🔥 {to_next} XP to Level {level+1}")
    bot.reply_to(m, text)

# ============================================================
# /leaderboard
# ============================================================
@bot.message_handler(commands=["leaderboard"])
def cmd_leaderboard(m):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🌎 GLOBAL", callback_data="lb_global_xp"),
            types.InlineKeyboardButton("👥 GROUP", callback_data=f"lb_group_xp_{m.chat.id}"))
    kb.add(types.InlineKeyboardButton("⭐ XP", callback_data="lb_global_xp"),
            types.InlineKeyboardButton("🪙 COINS", callback_data="lb_global_coins"))
    kb.add(types.InlineKeyboardButton("🏆 WINS", callback_data="lb_global_wins"))
    bot.reply_to(m, box("📊 LEADERBOARD", "Select a category below 👇"), reply_markup=kb)

def build_leaderboard(scope, metric, group_id=None):
    conn = get_conn()
    c = conn.cursor()
    if scope == "global":
        col = {"xp": "xp", "coins": "coins", "wins": "wins"}[metric]
        c.execute(f"SELECT first_name, {col}, is_vip FROM users ORDER BY {col} DESC LIMIT 10")
        rows = c.fetchall()
    else:
        col = {"xp": "xp", "coins": "coins", "wins": "wins"}[metric]
        c.execute(f"""SELECT u.first_name, g.{col}, u.is_vip FROM group_stats g 
                      JOIN users u ON u.user_id=g.user_id
                      WHERE g.group_id=? ORDER BY g.{col} DESC LIMIT 10""", (group_id,))
        rows = c.fetchall()
    conn.close()
    if not rows:
        return "No data yet."
    lines = []
    for i, (name, val, is_vip) in enumerate(rows):
        vip = "👑 " if is_vip else ""
        lines.append(f"{i+1}. {vip}{name} — {val}")
    return "\n".join(lines)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lb_"))
def cb_leaderboard(call):
    data = call.data
    if data.startswith("lb_global_"):
        metric = data.split("_")[2]
        body = build_leaderboard("global", metric)
        title = f"🌎 GLOBAL — {metric.upper()}"
    elif data.startswith("lb_group_"):
        parts = data.split("_")
        metric = parts[2]
        group_id = int(parts[3])
        body = build_leaderboard("group", metric, group_id)
        title = f"👥 GROUP — {metric.upper()}"
    else:
        return
    bot.answer_callback_query(call.id)
    bot.edit_message_text(box(title, body), call.message.chat.id, call.message.message_id)

# ============================================================
# /help + /guide (UPDATED WITH VIP)
# ============================================================
HELP_TEXT = box("📖 HELP MENU", "Choose a category below 👇")

@bot.message_handler(commands=["help"])
def cmd_help(m):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🎮 GAMES", callback_data="help_games"),
            types.InlineKeyboardButton("🪙 ECONOMY", callback_data="help_economy"))
    kb.add(types.InlineKeyboardButton("👤 PROFILE", callback_data="help_profile"),
            types.InlineKeyboardButton("🎁 REWARDS", callback_data="help_rewards"))
    kb.add(types.InlineKeyboardButton("👑 VIP", callback_data="help_vip"),
            types.InlineKeyboardButton("📖 GUIDE", callback_data="help_guide"))
    bot.reply_to(m, HELP_TEXT, reply_markup=kb)

HELP_SECTIONS = {
    "help_games": box("🎮 GAME COMMANDS",
        "/ttt <bet> — Tic Tac Toe PvP\n"
        "/rps <bet> — Rock Paper Scissors PvP\n"
        "DM practice vs bot also available (no rewards)"),
    "help_economy": box("🪙 ECONOMY COMMANDS",
        "/daily — Claim 250 Coins (DM only)\n"
        "/dice — Roll dice, earn Coins (6/day)\n"
        "Min PvP bet : 50 Coins"),
    "help_profile": box("👤 PROFILE & RANKING",
        "/profile — View your profile\n"
        "/rank — View level, XP, rank & position\n"
        "/leaderboard — Global/Group leaderboards"),
    "help_rewards": box("🎁 REWARD COMMANDS",
        "/daily — 250 Coins/day\n"
        "/dice — up to 600 Coins/day\n"
        "Must join Support Channel & Group"),
    "help_vip": box("👑 VIP COMMANDS",
        "/vip — View VIP status and purchase\n\n"
        "💎 VIP Benefits:\n"
        "• 2x Daily Rewards\n"
        "• Extra Dice Rolls (+4/day)\n"
        "• Exclusive Games Access\n"
        "• Special VIP Badge\n"
        "• Priority Support\n\n"
        "💰 Plans: Weekly: 2,000 | Monthly: 7,000 | Yearly: 75,000")
}

@bot.callback_query_handler(func=lambda call: call.data in HELP_SECTIONS)
def cb_help_section(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(HELP_SECTIONS[call.data], call.message.chat.id, call.message.message_id)

GUIDE_TEXT = box("📖 COMMAND GUIDE", """
/start — DM only. Registers you & opens main menu.

/help — Shows command categories.

/daily — DM only. +250 Coins once/day (500 for VIP). 
       Reset 12AM IST. Needs Support Channel + Group joined.

/dice — Roll dice up to 6x/day (10x for VIP). 
       Rewards 10-100 Coins. Reset 12AM IST.

/profile [@user] — View your or another user's stats. 
       Works in DM & groups.

/rank — Shows Level, XP, Rank, Global & Group position.

/leaderboard — Global/Group leaderboards by XP, Coins, Wins.

/vip — View VIP status, benefits, and purchase plans.

/ttt <bet> — Tic Tac Toe PvP. Min bet 50 Coins. 
       Winner gets 95% of pool.

/rps <bet> — Rock Paper Scissors PvP. 
       Same betting rules as TTT.

⚠️ DM practice games vs bot give NO coins/XP/stats.
""")

@bot.callback_query_handler(func=lambda call: call.data == "help_guide")
def cb_guide(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text(GUIDE_TEXT, call.message.chat.id, call.message.message_id)

# ============================================================
# menu_* callbacks (from /start menu)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def cb_menu(call):
    bot.answer_callback_query(call.id)
    action = call.data
    fake_msg = call.message
    fake_msg.from_user = call.from_user
    if action == "menu_profile":
        create_user_if_missing(call.from_user.id, call.from_user.username, call.from_user.first_name)
        row = get_user(call.from_user.id)
        bot.send_message(call.message.chat.id, profile_text(row))
    elif action == "menu_balance":
        row = get_user(call.from_user.id)
        bot.send_message(call.message.chat.id, box("🪙 BALANCE", f"💰 Coins : {row[3]}"))
    elif action == "menu_rank":
        cmd_rank(fake_msg)
    elif action == "menu_leaderboard":
        cmd_leaderboard(fake_msg)
    elif action == "menu_daily":
        cmd_daily(fake_msg)
    elif action == "menu_help":
        cmd_help(fake_msg)
    elif action == "menu_vip":
        cmd_vip(fake_msg)
    elif action == "menu_games":
        bot.send_message(call.message.chat.id, box("🎮 GAMES",
            "Use in a group:\n/ttt <bet>\n/rps <bet>\n\nOr message me in DM for free practice!"))

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def cb_check_join(call):
    if check_support_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified! Try the command again.")
    else:
        bot.answer_callback_query(call.id, "❌ Please join both first.", show_alert=True)

# ============================================================
# OWNER PANEL (UPDATED WITH VIP)
# ============================================================
def is_owner(user_id):
    return user_id == OWNER_ID

@bot.message_handler(commands=["panel"])
def cmd_panel(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("👥 USERS", callback_data="panel_users"),
            types.InlineKeyboardButton("👥 GROUPS", callback_data="panel_groups"))
    kb.add(types.InlineKeyboardButton("🏦 WALLET", callback_data="panel_wallet"),
            types.InlineKeyboardButton("🎮 GAMES", callback_data="panel_games"))
    kb.add(types.InlineKeyboardButton("📊 STATS", callback_data="panel_stats"),
            types.InlineKeyboardButton("📢 BROADCAST", callback_data="panel_broadcast"))
    kb.add(types.InlineKeyboardButton("👑 VIP MGMT", callback_data="panel_vip"),
            types.InlineKeyboardButton("⚙️ SETTINGS", callback_data="panel_settings"))
    bot.send_message(m.chat.id, box("👑 OWNER PANEL", "Manage Zynox Gaming below 👇"), reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("panel_"))
def cb_panel(call):
    if not is_owner(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Owner only.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    conn = get_conn()
    c = conn.cursor()
    
    if call.data == "panel_users":
        c.execute("SELECT COUNT(*) FROM users")
        c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
        vip_count = c.fetchone()[0]
        body = f"👥 Total Users : {c.fetchone()[0]}\n👑 VIP Users : {vip_count}"
    elif call.data == "panel_groups":
        c.execute("SELECT COUNT(*) FROM groups")
        body = f"👥 Total Groups : {c.fetchone()[0]}"
    elif call.data == "panel_wallet":
        body = f"🏦 Wallet Balance : {wallet_balance()} Coins"
    elif call.data == "panel_games":
        c.execute("SELECT COUNT(*) FROM matches")
        body = f"🎮 Total Matches : {c.fetchone()[0]}"
    elif call.data == "panel_stats":
        c.execute("SELECT SUM(coins), SUM(xp) FROM users")
        s = c.fetchone()
        body = f"🪙 Total Coins In Circulation : {s[0] or 0}\n⭐ Total XP : {s[1] or 0}"
    elif call.data == "panel_broadcast":
        body = "📢 Send: /broadcast <message>"
    elif call.data == "panel_vip":
        c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
        vip_count = c.fetchone()[0]
        c.execute("SELECT user_id, username, vip_expiry FROM users WHERE is_vip=1 ORDER BY vip_expiry ASC LIMIT 10")
        vip_users = c.fetchall()
        body = f"👑 VIP Users: {vip_count}\n\n"
        for uid, uname, expiry in vip_users:
            body += f"• {uname or uid} — Expires: {expiry[:10]}\n"
    else:
        body = "⚙️ Settings coming soon."
    
    conn.close()
    bot.edit_message_text(box("👑 OWNER PANEL", body), call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    text = m.text.partition(" ")[2]
    if not text:
        bot.reply_to(m, "Usage: /broadcast <message>")
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    sent = 0
    for uid in ids:
        try:
            bot.send_message(uid, box("📢 ANNOUNCEMENT", text))
            sent += 1
        except Exception:
            pass
    bot.reply_to(m, f"✅ Broadcast sent to {sent} users.")

@bot.message_handler(commands=["wallet"])
def cmd_wallet(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    bot.reply_to(m, box("🏦 BOT WALLET", f"💰 Balance : {wallet_balance()} Coins"))

# VIP Management for Owner
@bot.message_handler(commands=["vipgive"])
def cmd_vipgive(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    parts = m.text.split()
    if len(parts) != 4:
        bot.reply_to(m, "Usage: /vipgive @username|user_id plan days\nPlans: weekly, monthly, yearly")
        return
    
    target = resolve_user(parts[1])
    plan = parts[2].lower()
    if plan not in VIP_BENEFITS:
        bot.reply_to(m, "❌ Invalid plan. Use: weekly, monthly, yearly")
        return
    
    try:
        days = int(parts[3])
        if days <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(m, "❌ Invalid days. Must be positive number.")
        return
    
    if target is None:
        bot.reply_to(m, "❌ User not found.")
        return
    
    activate_vip(target, plan)
    # Update expiry to add extra days
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT vip_expiry FROM users WHERE user_id=?", (target,))
    row = c.fetchone()
    if row and row[0]:
        expiry = datetime.fromisoformat(row[0])
        new_expiry = expiry + timedelta(days=days)
        c.execute("UPDATE users SET vip_expiry=? WHERE user_id=?", (new_expiry.isoformat(), target))
    conn.commit()
    conn.close()
    
    bot.reply_to(m, box("👑 VIP GIVEN", f"✅ VIP {plan} given to {parts[1]}\n📅 Extra {days} days added."))

def resolve_user(identifier):
    identifier = identifier.strip()
    if identifier.startswith("@"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username=?", (identifier[1:],))
        r = c.fetchone()
        conn.close()
        return r[0] if r else None
    if identifier.isdigit():
        return int(identifier)
    return None

@bot.message_handler(commands=["give"])
def cmd_give(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    parts = m.text.split()
    if len(parts) != 3:
        bot.reply_to(m, "Usage: /give @username|user_id amount")
        return
    target = resolve_user(parts[1])
    try:
        amount = int(parts[2])
    except ValueError:
        bot.reply_to(m, "❌ Invalid amount.")
        return
    if target is None or amount <= 0:
        bot.reply_to(m, "❌ Invalid user or amount.")
        return
    if wallet_balance() < amount:
        bot.reply_to(m, "❌ Insufficient wallet balance.")
        return
    wallet_add(-amount)
    add_coins(target, amount, "owner_give")
    bot.reply_to(m, box("🏦 WALLET TRANSFER", f"✅ Sent {amount} Coins to {parts[1]}"))

@bot.message_handler(commands=["take"])
def cmd_take(m):
    if m.chat.type != "private" or not is_owner(m.from_user.id):
        return
    parts = m.text.split()
    if len(parts) != 3:
        bot.reply_to(m, "Usage: /take @username|user_id amount")
        return
    target = resolve_user(parts[1])
    try:
        amount = int(parts[2])
    except ValueError:
        bot.reply_to(m, "❌ Invalid amount.")
        return
    if target is None or amount <= 0:
        bot.reply_to(m, "❌ Invalid user or amount.")
        return
    ok = add_coins(target, -amount, "owner_take")
    if not ok:
        bot.reply_to(m, "❌ User has insufficient balance.")
        return
    wallet_add(amount)
    bot.reply_to(m, box("🏦 WALLET TRANSFER", f"✅ Took {amount} Coins from {parts[1]}"))

# ============================================================
# PvP GAME ENGINE (shared)
# ============================================================
MIN_BET = 50
active_lobbies = {}   # key: (chat_id, msg_id) -> lobby dict
lobby_lock = threading.Lock()
active_games = {}     # key: game_id -> game state

def parse_bet(m):
    parts = m.text.split()
    if len(parts) != 2:
        return None
    try:
        bet = int(parts[1])
    except ValueError:
        return None
    if bet < MIN_BET:
        return None
    return bet

def settle_match(game, winner_id, loser_id, draw=False, group_id=None):
    pool = game["bet"] * 2
    if draw:
        add_coins(game["host_id"], game["bet"], "game_refund")
        add_coins(game["p2_id"], game["bet"], "game_refund")
        add_xp(game["host_id"], 20)
        add_xp(game["p2_id"], 20)
        conn = get_conn()
        conn.execute("UPDATE users SET games_played=games_played+1, draws=draws+1 WHERE user_id IN (?,?)",
                     (game["host_id"], game["p2_id"]))
        conn.commit()
        conn.close()
        return None
    fee = pool * 5 // 100
    payout = pool - fee
    wallet_add(fee)
    add_coins(winner_id, payout, "pvp_win")
    add_xp(winner_id, 50)
    add_xp(loser_id, 10)
    conn = get_conn()
    conn.execute("UPDATE users SET games_played=games_played+1, wins=wins+1 WHERE user_id=?", (winner_id,))
    conn.execute("UPDATE users SET games_played=games_played+1, losses=losses+1 WHERE user_id=?", (loser_id,))
    conn.commit()
    conn.close()
    if group_id:
        add_group_stat(group_id, winner_id, xp=50, coins=payout, wins=1)
        add_group_stat(group_id, loser_id, xp=10)
    return payout, fee

# ---------------- TIC TAC TOE ----------------
def ttt_board_kb(board, game_id):
    kb = types.InlineKeyboardMarkup(row_width=3)
    syms = {0: "⬜", 1: "❌", 2: "⭕"}
    for r in range(3):
        row = []
        for cidx in range(3):
            i = r * 3 + cidx
            label = syms[board[i]] if board[i] else str(i + 1)
            row.append(types.InlineKeyboardButton(label, callback_data=f"ttt_move_{game_id}_{i}"))
        kb.row(*row)
    return kb

def ttt_check_winner(board):
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,b,c in lines:
        if board[a] != 0 and board[a] == board[b] == board[c]:
            return board[a]
    if 0 not in board:
        return 3  # draw
    return 0

@bot.message_handler(commands=["ttt"])
def cmd_ttt(m):
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    if m.chat.type == "private":
        bot.reply_to(m, box("🎮 PRACTICE MODE", "DM practice not enabled in this build.\nUse /ttt in a group for real PvP!"))
        return
    bet = parse_bet(m)
    if bet is None:
        bot.reply_to(m, f"❌ Usage: /ttt <bet>\nMinimum bet: {MIN_BET} Coins")
        return
    row = get_user(u.id)
    if row[3] < bet:
        bot.reply_to(m, "❌ Insufficient balance for this bet.")
        return
    ok = add_coins(u.id, -bet, "ttt_escrow")
    if not ok:
        bot.reply_to(m, "❌ Insufficient balance.")
        return
    uname = f"@{u.username}" if u.username else u.first_name
    text = box("🎮 TIC TAC TOE",
        f"👤 Host : {uname}\n\n🪙 Entry : {bet} Coins\n🏆 Prize Pool : {bet*2} Coins\n🏦 Fee : 5%",
        "⚡ Waiting for Player 2")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎮 JOIN GAME", callback_data=f"ttt_join_{u.id}_{bet}"))
    sent = bot.send_message(m.chat.id, text, reply_markup=kb)
    with lobby_lock:
        active_lobbies[(m.chat.id, sent.message_id)] = {"game": "ttt", "host_id": u.id, "bet": bet, "joined": False}

@bot.callback_query_handler(func=lambda call: call.data.startswith("ttt_join_"))
def cb_ttt_join(call):
    _, _, host_id, bet = call.data.split("_")
    host_id, bet = int(host_id), int(bet)
    key = (call.message.chat.id, call.message.message_id)
    with lobby_lock:
        lobby = active_lobbies.get(key)
        if not lobby or lobby["joined"]:
            bot.answer_callback_query(call.id, "❌ Lobby closed.", show_alert=True)
            return
        if call.from_user.id == host_id:
            bot.answer_callback_query(call.id, "❌ You can't join your own lobby.", show_alert=True)
            return
        p2 = call.from_user
        create_user_if_missing(p2.id, p2.username, p2.first_name)
        row = get_user(p2.id)
        if row[3] < bet:
            bot.answer_callback_query(call.id, "❌ Insufficient balance.", show_alert=True)
            return
        ok = add_coins(p2.id, -bet, "ttt_escrow")
        if not ok:
            bot.answer_callback_query(call.id, "❌ Insufficient balance.", show_alert=True)
            return
        lobby["joined"] = True
        lobby["p2_id"] = p2.id
    bot.answer_callback_query(call.id, "✅ Joined!")
    game_id = f"{key[0]}_{key[1]}"
    active_games[game_id] = {"host_id": host_id, "p2_id": p2.id, "bet": bet, "board": [0]*9,
                               "turn": host_id, "group_id": call.message.chat.id}
    bot.edit_message_text(box("🎮 TIC TAC TOE", "⚡ Game Started!\n❌ Host  vs  ⭕ Player 2"),
                            key[0], key[1], reply_markup=ttt_board_kb([0]*9, game_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("ttt_move_"))
def cb_ttt_move(call):
    _, _, game_id, idx = call.data.split("_")
    idx = int(idx)
    game = active_games.get(game_id)
    if not game:
        bot.answer_callback_query(call.id, "❌ Game not found.", show_alert=True)
        return
    if call.from_user.id != game["turn"]:
        bot.answer_callback_query(call.id, "⏳ Not your turn.", show_alert=True)
        return
    if game["board"][idx] != 0:
        bot.answer_callback_query(call.id, "❌ Cell taken.", show_alert=True)
        return
    symbol = 1 if call.from_user.id == game["host_id"] else 2
    game["board"][idx] = symbol
    result = ttt_check_winner(game["board"])
    chat_id, msg_id = map(int, game_id.split("_"))
    if result == 0:
        game["turn"] = game["p2_id"] if game["turn"] == game["host_id"] else game["host_id"]
        bot.answer_callback_query(call.id)
        bot.edit_message_text(box("🎮 TIC TAC TOE", "❌ Host  vs  ⭕ Player 2\nGame in progress..."),
                                chat_id, msg_id, reply_markup=ttt_board_kb(game["board"], game_id))
    else:
        bot.answer_callback_query(call.id)
        if result == 3:
            settle_match(game, None, None, draw=True, group_id=game["group_id"])
            outcome = "🤝 DRAW! Bets refunded, no fee charged."
        else:
            winner_id = game["host_id"] if result == 1 else game["p2_id"]
            loser_id = game["p2_id"] if result == 1 else game["host_id"]
            payout, fee = settle_match(game, winner_id, loser_id, group_id=game["group_id"])
            outcome = f"🏆 Winner gets {payout} Coins!\n🏦 Fee : {fee} Coins"
        bot.edit_message_text(box("🎮 GAME OVER", outcome), chat_id, msg_id,
                                reply_markup=ttt_board_kb(game["board"], game_id))
        del active_games[game_id]

# ---------------- RPS ----------------
RPS_CHOICES = {"rock": "🪨 ROCK", "paper": "📄 PAPER", "scissors": "✂️ SCISSORS"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

@bot.message_handler(commands=["rps"])
def cmd_rps(m):
    u = m.from_user
    create_user_if_missing(u.id, u.username, u.first_name)
    if m.chat.type == "private":
        bot.reply_to(m, box("✊ PRACTICE MODE", "DM practice not enabled in this build.\nUse /rps in a group for real PvP!"))
        return
    bet = parse_bet(m)
    if bet is None:
        bot.reply_to(m, f"❌ Usage: /rps <bet>\nMinimum bet: {MIN_BET} Coins")
        return
    row = get_user(u.id)
    if row[3] < bet:
        bot.reply_to(m, "❌ Insufficient balance for this bet.")
        return
    ok = add_coins(u.id, -bet, "rps_escrow")
    if not ok:
        bot.reply_to(m, "❌ Insufficient balance.")
        return
    uname = f"@{u.username}" if u.username else u.first_name
    text = box("✊ RPS BATTLE",
        f"👤 Host : {uname}\n\n🪙 Entry : {bet} Coins\n🏆 Prize Pool : {bet*2} Coins\n🏦 Fee : 5%",
        "⚡ Waiting for Player 2")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎮 JOIN GAME", callback_data=f"rps_join_{u.id}_{bet}"))
    sent = bot.send_message(m.chat.id, text, reply_markup=kb)
    with lobby_lock:
        active_lobbies[(m.chat.id, sent.message_id)] = {"game": "rps", "host_id": u.id, "bet": bet, "joined": False}

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps_join_"))
def cb_rps_join(call):
    _, _, host_id, bet = call.data.split("_")
    host_id, bet = int(host_id), int(bet)
    key = (call.message.chat.id, call.message.message_id)
    with lobby_lock:
        lobby = active_lobbies.get(key)
        if not lobby or lobby["joined"]:
            bot.answer_callback_query(call.id, "❌ Lobby closed.", show_alert=True)
            return
        if call.from_user.id == host_id:
            bot.answer_callback_query(call.id, "❌ You can't join your own lobby.", show_alert=True)
            return
        p2 = call.from_user
        create_user_if_missing(p2.id, p2.username, p2.first_name)
        row = get_user(p2.id)
        if row[3] < bet:
            bot.answer_callback_query(call.id, "❌ Insufficient balance.", show_alert=True)
            return
        ok = add_coins(p2.id, -bet, "rps_escrow")
        if not ok:
            bot.answer_callback_query(call.id, "❌ Insufficient balance.", show_alert=True)
            return
        lobby["joined"] = True
        lobby["p2_id"] = p2.id
    bot.answer_callback_query(call.id, "✅ Joined!")
    game_id = f"{key[0]}_{key[1]}"
    active_games[game_id] = {"host_id": host_id, "p2_id": p2.id, "bet": bet, "choices": {},
                               "group_id": call.message.chat.id}
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[types.InlineKeyboardButton(v, callback_data=f"rps_pick_{game_id}_{k}") for k, v in RPS_CHOICES.items()])
    bot.edit_message_text(box("✊ RPS BATTLE", "⚡ Both players pick your move!"), key[0], key[1], reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rps_pick_"))
def cb_rps_pick(call):
    _, _, game_id, choice = call.data.split("_")
    game = active_games.get(game_id)
    if not game:
        bot.answer_callback_query(call.id, "❌ Game not found.", show_alert=True)
        return
    uid = call.from_user.id
    if uid not in (game["host_id"], game["p2_id"]):
        bot.answer_callback_query(call.id, "❌ Not your game.", show_alert=True)
        return
    if uid in game["choices"]:
        bot.answer_callback_query(call.id, "✅ Already picked.", show_alert=True)
        return
    game["choices"][uid] = choice
    bot.answer_callback_query(call.id, f"✅ You picked {RPS_CHOICES[choice]}")
    if len(game["choices"]) < 2:
        return
    chat_id, msg_id = map(int, game_id.split("_"))
    c1, c2 = game["choices"][game["host_id"]], game["choices"][game["p2_id"]]
    if c1 == c2:
        settle_match(game, None, None, draw=True, group_id=game["group_id"])
        outcome = f"🤝 Both picked {RPS_CHOICES[c1]} — DRAW! Bets refunded."
    elif RPS_BEATS[c1] == c2:
        payout, fee = settle_match(game, game["host_id"], game["p2_id"], group_id=game["group_id"])
        outcome = f"🏆 Host wins with {RPS_CHOICES[c1]} vs {RPS_CHOICES[c2]}!\n🪙 Payout : {payout} | 🏦 Fee : {fee}"
    else:
        payout, fee = settle_match(game, game["p2_id"], game["host_id"], group_id=game["group_id"])
        outcome = f"🏆 Player 2 wins with {RPS_CHOICES[c2]} vs {RPS_CHOICES[c1]}!\n🪙 Payout : {payout} | 🏦 Fee : {fee}"
    bot.edit_message_text(box("✊ RESULT", outcome), chat_id, msg_id)
    del active_games[game_id]

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    init_db()
    print("🎮 Zynox Gaming Bot is starting...")
    print("👑 VIP System Activated!")
    print("💎 Commands: /vip, /vipgive (owner only)")
    bot.infinity_polling(skip_pending=True)
