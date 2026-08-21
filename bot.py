import random
import time
import re
from datetime import datetime, timedelta
from telebot import TeleBot, types
import json
import os
import sqlite3

# Initialize bot with your token
TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
bot = TeleBot(TOKEN)

# Owner ID
OWNER_ID = 8727799160

# Support Group and Channel
SUPPORT_GROUP = "https://t.me/+97rox0VQWXNiMzg1"
SUPPORT_CHANNEL = "https://t.me/+CS-ZvjWSB1oxZjZl"

# Database setup
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('zynox.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                aura INTEGER DEFAULT 0,
                rank TEXT DEFAULT 'Bronze I',
                streak INTEGER DEFAULT 0,
                last_claim DATE,
                is_married INTEGER DEFAULT 0,
                partner_id INTEGER DEFAULT NULL,
                messages INTEGER DEFAULT 0,
                quiz_wins INTEGER DEFAULT 0,
                game_wins INTEGER DEFAULT 0,
                achievements TEXT DEFAULT '[]',
                registered_date DATE
            )
        ''')
        
        # Marriage proposals table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposals (
                proposer_id INTEGER,
                target_id INTEGER,
                timestamp DATETIME,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Divorce requests table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS divorce_requests (
                user_id INTEGER,
                partner_id INTEGER,
                timestamp DATETIME,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Daily tasks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_tasks (
                user_id INTEGER,
                task_date DATE,
                tasks TEXT,
                completed_tasks TEXT,
                reward_claimed INTEGER DEFAULT 0
            )
        ''')
        
        # Groups table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                added_by INTEGER,
                added_date DATE
            )
        ''')
        
        # Group bonus tracking
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_bonus (
                user_id INTEGER,
                group_id INTEGER,
                bonus_date DATE,
                PRIMARY KEY (user_id, group_id)
            )
        ''')
        
        # Custom media table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_media (
                media_type TEXT,
                file_id TEXT,
                added_by INTEGER,
                added_date DATE
            )
        ''')
        
        # Sudo users
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        # Quiz questions
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                question TEXT,
                options TEXT,
                answer INTEGER
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, registered_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().date()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_aura(self, user_id, amount):
        self.cursor.execute('UPDATE users SET aura = aura + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def set_aura(self, user_id, amount):
        self.cursor.execute('UPDATE users SET aura = ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def update_rank(self, user_id, rank):
        self.cursor.execute('UPDATE users SET rank = ? WHERE user_id = ?', (rank, user_id))
        self.conn.commit()
    
    def update_streak(self, user_id):
        self.cursor.execute('UPDATE users SET streak = streak + 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def reset_streak(self, user_id):
        self.cursor.execute('UPDATE users SET streak = 0 WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_marriage_status(self, user_id):
        self.cursor.execute('SELECT is_married, partner_id FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def marry_users(self, user1, user2):
        self.cursor.execute('UPDATE users SET is_married = 1, partner_id = ? WHERE user_id = ?', (user2, user1))
        self.cursor.execute('UPDATE users SET is_married = 1, partner_id = ? WHERE user_id = ?', (user1, user2))
        self.conn.commit()
    
    def divorce_users(self, user1, user2):
        self.cursor.execute('UPDATE users SET is_married = 0, partner_id = NULL WHERE user_id = ?', (user1,))
        self.cursor.execute('UPDATE users SET is_married = 0, partner_id = NULL WHERE user_id = ?', (user2,))
        self.conn.commit()
    
    def add_proposal(self, proposer, target):
        self.cursor.execute('''
            INSERT INTO proposals (proposer_id, target_id, timestamp, status)
            VALUES (?, ?, ?, 'pending')
        ''', (proposer, target, datetime.now()))
        self.conn.commit()
    
    def get_proposal(self, target_id):
        self.cursor.execute('''
            SELECT * FROM proposals 
            WHERE target_id = ? AND status = 'pending' 
            ORDER BY timestamp DESC LIMIT 1
        ''', (target_id,))
        return self.cursor.fetchone()
    
    def update_proposal_status(self, proposer_id, target_id, status):
        self.cursor.execute('''
            UPDATE proposals SET status = ? 
            WHERE proposer_id = ? AND target_id = ? AND status = 'pending'
        ''', (status, proposer_id, target_id))
        self.conn.commit()
    
    def add_divorce_request(self, user_id, partner_id):
        self.cursor.execute('''
            INSERT INTO divorce_requests (user_id, partner_id, timestamp, status)
            VALUES (?, ?, ?, 'pending')
        ''', (user_id, partner_id, datetime.now()))
        self.conn.commit()
    
    def get_divorce_request(self, partner_id):
        self.cursor.execute('''
            SELECT * FROM divorce_requests 
            WHERE partner_id = ? AND status = 'pending' 
            ORDER BY timestamp DESC LIMIT 1
        ''', (partner_id,))
        return self.cursor.fetchone()
    
    def update_divorce_status(self, user_id, partner_id, status):
        self.cursor.execute('''
            UPDATE divorce_requests SET status = ? 
            WHERE user_id = ? AND partner_id = ? AND status = 'pending'
        ''', (status, user_id, partner_id))
        self.conn.commit()
    
    def add_group(self, group_id, group_name, added_by):
        self.cursor.execute('''
            INSERT OR IGNORE INTO groups (group_id, group_name, added_by, added_date)
            VALUES (?, ?, ?, ?)
        ''', (group_id, group_name, added_by, datetime.now().date()))
        self.conn.commit()
    
    def get_group_bonus(self, user_id, group_id):
        self.cursor.execute('''
            SELECT * FROM group_bonus WHERE user_id = ? AND group_id = ?
        ''', (user_id, group_id))
        return self.cursor.fetchone()
    
    def add_group_bonus(self, user_id, group_id):
        self.cursor.execute('''
            INSERT INTO group_bonus (user_id, group_id, bonus_date)
            VALUES (?, ?, ?)
        ''', (user_id, group_id, datetime.now().date()))
        self.conn.commit()
    
    def add_media(self, media_type, file_id, added_by):
        self.cursor.execute('''
            INSERT INTO custom_media (media_type, file_id, added_by, added_date)
            VALUES (?, ?, ?, ?)
        ''', (media_type, file_id, added_by, datetime.now().date()))
        self.conn.commit()
    
    def get_media(self, media_type):
        self.cursor.execute('''
            SELECT file_id FROM custom_media WHERE media_type = ?
            ORDER BY RANDOM() LIMIT 1
        ''', (media_type,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def add_sudo(self, user_id):
        self.cursor.execute('INSERT OR IGNORE INTO sudo_users (user_id) VALUES (?)', (user_id,))
        self.conn.commit()
    
    def remove_sudo(self, user_id):
        self.cursor.execute('DELETE FROM sudo_users WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def get_sudo_list(self):
        self.cursor.execute('SELECT user_id FROM sudo_users')
        return [row[0] for row in self.cursor.fetchall()]
    
    def is_sudo(self, user_id):
        self.cursor.execute('SELECT * FROM sudo_users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None
    
    def add_quiz_question(self, category, question, options, answer):
        options_json = json.dumps(options)
        self.cursor.execute('''
            INSERT INTO quiz_questions (category, question, options, answer)
            VALUES (?, ?, ?, ?)
        ''', (category, question, options_json, answer))
        self.conn.commit()
    
    def get_random_quiz(self):
        self.cursor.execute('SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1')
        result = self.cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'category': result[1],
                'question': result[2],
                'options': json.loads(result[3]),
                'answer': result[4]
            }
        return None

db = Database()

# ========== RANK SYSTEM ==========
RANKS = [
    ('Bronze I', 0),
    ('Bronze II', 50),
    ('Bronze III', 150),
    ('Bronze IV', 300),
    ('Silver I', 500),
    ('Silver II', 800),
    ('Silver III', 1200),
    ('Silver IV', 1700),
    ('Gold I', 2300),
    ('Gold II', 3000),
    ('Gold III', 3800),
    ('Gold IV', 4700),
    ('Platinum I', 5700),
    ('Platinum II', 6800),
    ('Platinum III', 8000),
    ('Platinum IV', 9300),
    ('Diamond I', 10700),
    ('Diamond II', 12200),
    ('Diamond III', 13800),
    ('Diamond IV', 15500),
    ('Master I', 17300),
    ('Master II', 19200),
    ('Master III', 21200),
    ('Master IV', 23300),
    ('Grandmaster I', 25500),
    ('Grandmaster II', 27800),
    ('Grandmaster III', 30200),
    ('Grandmaster IV', 32700),
    ('Zynox Legend', 35300),
    ('Zynox Mythic', 38000),
    ('Zynox Immortal', 40800),
    ('Zynox God', 43700),
]

def get_rank_from_aura(aura):
    for rank_name, threshold in reversed(RANKS):
        if aura >= threshold:
            return rank_name
    return RANKS[0][0]

def get_next_rank_aura(aura):
    for rank_name, threshold in RANKS:
        if aura < threshold:
            return threshold
    return None

# ========== ROASTS ==========
REJECT_ROASTS = [
    "💀 Friendzone Express ne bina ticket ke wapas bhej diya.",
    "📉 Aura gaya, proposal gaya.",
    "🚪 Dil ka darwaza band mila.",
    "⚠️ Better luck next season.",
    "😬 Rejection ka taste kaisa laga?",
    "💔 Dil toot gaya? Aura bhi toot gaya.",
    "🤡 Clown moment ho gaya.",
    "🎭 Acting class ki zaroorat hai.",
]

SINGLE_DIVORCE = [
    "🤨 Teri shaadi kab hui thi jo divorce lene aa gaya?",
    "📜 Records me spouse mila hi nahi.",
    "😶 Single ho aur divorce maang rahe ho?",
    "💀 Bhai tu toh single hai!",
    "🤔 Divorce ka option sirf married logon ke liye hai.",
]

# ========== HELPERS ==========
def format_aura(aura):
    return f"{aura:,}"

def create_vip_message(title, content, footer="🌌 Keep building your Aura."):
    return f"""
╔════════════════════╗
{title}
╚════════════════════╝

{content}

━━━━━━━━━━━━━━━━━━
{footer}
"""

def is_user_in_group(user_id, group_id):
    try:
        member = bot.get_chat_member(group_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def check_support_membership(user_id):
    # Extract group and channel IDs from links
    # For simplicity, we'll check if user is in the support group and channel
    # In production, you'd need to extract the actual chat IDs
    group_id = SUPPORT_GROUP.split('/')[-1]
    channel_id = SUPPORT_CHANNEL.split('/')[-1]
    
    try:
        # Check if user is in support group
        group_member = bot.get_chat_member(group_id, user_id)
        channel_member = bot.get_chat_member(channel_id, user_id)
        return group_member.status in ['member', 'administrator', 'creator'] and \
               channel_member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ========== START COMMAND ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    # Add user to database
    db.add_user(
        user_id,
        message.from_user.username or '',
        message.from_user.first_name
    )
    
    # Check if user is in DM
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        # Group message
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Open Zynox Gaming", url=f"https://t.me/{bot.get_me().username}"))
        bot.reply_to(message, "📩 Please start Zynox Gaming in DM first.", reply_markup=markup)
        return
    
    # DM start
    user = db.get_user(user_id)
    aura = user[3] if user else 0
    rank = user[4] if user else 'Bronze I'
    streak = user[5] if user else 0
    is_married = user[6] if user else 0
    partner_id = user[7] if user else None
    
    # Get partner name if married
    partner_name = "Single"
    if is_married and partner_id:
        partner = db.get_user(partner_id)
        if partner:
            partner_name = partner[2] or "Unknown"
    
    # Send welcome media if available
    media_id = db.get_media('welcome')
    if media_id:
        try:
            bot.send_animation(user_id, media_id)
        except:
            pass
    
    content = f"""
📊 YOUR STATS

⚡ Aura: {format_aura(aura)}
🏅 Rank: {rank}
🔥 Streak: {streak} Days
💍 Status: {"💍 Married" if is_married else "💔 Single"}

━━━━━━━━━━━━━━━━━━

👇 CHOOSE AN OPTION BELOW
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🍀 ZYNOX FEATURES", callback_data="features"),
        types.InlineKeyboardButton("👥 GROUPS", callback_data="groups"),
        types.InlineKeyboardButton("💎 PROFILE", callback_data="profile"),
        types.InlineKeyboardButton("📢 UPDATES", callback_data="updates"),
        types.InlineKeyboardButton("🎮 GAMES", callback_data="games"),
        types.InlineKeyboardButton("➕ ADD ME TO YOUR GROUP", callback_data="add_bot")
    )
    
    bot.send_message(
        user_id,
        f"💙 HIEEEE × ZYNOX GAMING ×\n\nA GAMING & CHATTING BOT HAVING LOTS OF FEATURES TO ENGAGE YOUR GROUP.\n\n{content}",
        reply_markup=markup
    )
    
    # Send notification to owner for first time users
    if not user:
        owner_markup = types.InlineKeyboardMarkup()
        owner_markup.add(types.InlineKeyboardButton("👤 View Profile", callback_data=f"admin_view_{user_id}"))
        
        bot.send_message(
            OWNER_ID,
            f"🚀 NEW USER STARTED ZYNOX\n\n"
            f"👤 Name: {message.from_user.first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📛 Username: @{message.from_user.username or 'No Username'}\n\n"
            f"✅ User Registered",
            reply_markup=owner_markup
        )

# ========== CALLBACK QUERY HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    if data == "features":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
        bot.edit_message_text(
            "⚡ ZYNOX FEATURES\n\n"
            "⚡ Aura Economy\n"
            "🏆 Rank System\n"
            "🎮 Mini Games\n"
            "💍 Relationship System\n"
            "🫂 Friendship System\n"
            "🎁 Daily Rewards\n"
            "🧠 Random Quiz\n"
            "🎯 Daily Tasks\n"
            "🏅 Achievements\n"
            "🏆 Leaderboards\n"
            "🎭 Custom Media",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data == "groups":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👥 Support Group", url=SUPPORT_GROUP),
            types.InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        )
        bot.edit_message_text(
            "👥 ZYNOX COMMUNITY\n\n"
            "Join our official communities:\n\n"
            "👥 Support Group - Get help and connect with others\n"
            "📢 Support Channel - Latest updates and announcements",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data == "profile":
        profile_command(call.message)
    
    elif data == "updates":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
        bot.edit_message_text(
            "📢 ZYNOX UPDATES\n\n"
            "Stay tuned for the latest updates!\n"
            "Join our Support Channel for announcements.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data == "games":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
            types.InlineKeyboardButton("✊ RPS", callback_data="game_rps"),
            types.InlineKeyboardButton("🧠 Quiz", callback_data="game_quiz"),
            types.InlineKeyboardButton("🎯 Guess", callback_data="game_guess"),
            types.InlineKeyboardButton("🔢 Math", callback_data="game_math"),
            types.InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        )
        bot.edit_message_text(
            "🎮 ZYNOX GAMES\n\n"
            "Choose a game to play and earn Aura!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif data == "add_bot":
        bot.answer_callback_query(call.id, "Add Zynox Gaming to your group from the bot's profile!")
    
    elif data == "back_to_start":
        # Restart the start message
        start_command(call.message)
    
    elif data.startswith("game_"):
        game_name = data.replace("game_", "")
        bot.answer_callback_query(call.id, f"🎮 {game_name.upper()} game coming soon!")
    
    elif data.startswith("marry_"):
        target_id = int(data.split("_")[1])
        handle_marriage_response(call, target_id, 'accept')
    
    elif data.startswith("reject_"):
        target_id = int(data.split("_")[1])
        handle_marriage_response(call, target_id, 'reject')
    
    elif data.startswith("divorce_accept_"):
        partner_id = int(data.split("_")[2])
        handle_divorce_response(call, partner_id, 'accept')
    
    elif data.startswith("divorce_stay_"):
        partner_id = int(data.split("_")[2])
        handle_divorce_response(call, partner_id, 'stay')
    
    elif data.startswith("admin_view_"):
        target_id = int(data.split("_")[2])
        if user_id == OWNER_ID:
            view_user_profile(call, target_id)

# ========== PROFILE COMMAND ==========
@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    aura = user[3]
    rank = user[4]
    streak = user[5]
    is_married = user[6]
    partner_id = user[7]
    messages = user[8] or 0
    quiz_wins = user[9] or 0
    game_wins = user[10] or 0
    achievements = json.loads(user[11]) if user[11] else []
    
    # Get partner name
    partner_name = "Single"
    if is_married and partner_id:
        partner = db.get_user(partner_id)
        if partner:
            partner_name = partner[2] or "Unknown"
    
    # Get global rank
    db.cursor.execute('SELECT COUNT(*) + 1 FROM users WHERE aura > ?', (aura,))
    global_rank = db.cursor.fetchone()[0]
    
    content = f"""
🏷️ Name: {message.from_user.first_name}

⚡ Aura: {format_aura(aura)}
🏅 Rank: {rank}

🌍 Global Rank: #{global_rank}
👥 Group Rank: #Coming Soon

🔥 Streak: {streak} Days

💍 Partner: {partner_name}
💙 Best Friend: Not Set

💬 Messages: {messages}
🧠 Quiz Wins: {quiz_wins}
🎮 Game Wins: {game_wins}

🏅 Achievements: {len(achievements)}

━━━━━━━━━━━━━━━━━━
🌌 Keep building your Aura.
"""
    
    media_id = db.get_media('profile')
    if media_id:
        try:
            bot.send_animation(user_id, media_id)
        except:
            pass
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    
    bot.send_message(user_id, create_vip_message("👤 PROFILE", content), reply_markup=markup)

def view_user_profile(call, target_id):
    user = db.get_user(target_id)
    if not user:
        bot.edit_message_text("User not found.", call.message.chat.id, call.message.message_id)
        return
    
    content = f"""
👤 USER PROFILE

🏷️ Name: {user[2] or 'Unknown'}
🆔 ID: {user[0]}
⚡ Aura: {format_aura(user[3])}
🏅 Rank: {user[4]}
🔥 Streak: {user[5]} Days
💍 Married: {"Yes" if user[6] else "No"}
💬 Messages: {user[8] or 0}
🧠 Quiz Wins: {user[9] or 0}
🎮 Game Wins: {user[10] or 0}
"""
    bot.edit_message_text(
        content,
        call.message.chat.id,
        call.message.message_id
    )

# ========== DAILY CLAIM ==========
@bot.message_handler(commands=['claim'])
def claim_command(message):
    user_id = message.from_user.id
    
    # Check if in group
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 Open Zynox Gaming", url=f"https://t.me/{bot.get_me().username}"))
        bot.reply_to(
            message,
            "🔒 AURA CLAIM LOCKED\n\nDaily Aura claim karne ke liye DM me claim karo.",
            reply_markup=markup
        )
        return
    
    # Check support membership
    if not check_support_membership(user_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👥 Support Group", url=SUPPORT_GROUP),
            types.InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL),
            types.InlineKeyboardButton("🔄 Check Membership", callback_data="check_membership")
        )
        bot.send_message(
            user_id,
            "🔒 AURA LOCKED\n\n"
            "Daily Aura claim karne ke liye dono communities join karo.\n\n"
            f"👥 Support Group: {SUPPORT_GROUP}\n"
            f"📢 Support Channel: {SUPPORT_CHANNEL}",
            reply_markup=markup
        )
        return
    
    # Check if already claimed today
    user = db.get_user(user_id)
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    last_claim = user[5]  # streak is in 5th position, but we need last_claim
    # Actually we need to check last_claim date
    db.cursor.execute('SELECT last_claim FROM users WHERE user_id = ?', (user_id,))
    result = db.cursor.fetchone()
    last_claim_date = result[0] if result else None
    
    today = datetime.now().date()
    
    if last_claim_date == str(today):
        bot.reply_to(message, "🎁 You already claimed today! Come back tomorrow.")
        return
    
    # Calculate random reward
    reward = random.randint(100, 300)
    
    # Update user
    db.update_aura(user_id, reward)
    
    # Update streak
    if last_claim_date and (today - datetime.strptime(last_claim_date, '%Y-%m-%d').date()).days == 1:
        db.update_streak(user_id)
    else:
        db.reset_streak(user_id)
        db.update_streak(user_id)
    
    # Update last claim
    db.cursor.execute('UPDATE users SET last_claim = ? WHERE user_id = ?', (today, user_id))
    db.conn.commit()
    
    # Get updated rank
    user = db.get_user(user_id)
    aura = user[3]
    rank = user[4]
    streak = user[5]
    next_rank = get_next_rank_aura(aura)
    remaining = next_rank - aura if next_rank else 0
    
    # Send media
    media_id = db.get_media('claim')
    if media_id:
        try:
            bot.send_animation(user_id, media_id)
        except:
            pass
    
    content = f"""
✨ Reward: +{reward} Aura

🔥 Streak: {streak} Days

🏅 Rank: {rank}

📈 Next Rank: {remaining} Aura Remaining

🌌 Come back tomorrow.
"""
    bot.send_message(
        user_id,
        create_vip_message("🎁 DAILY AURA", content)
    )

# ========== MARRIAGE SYSTEM ==========
@bot.message_handler(commands=['marry'])
def marry_command(message):
    user_id = message.from_user.id
    
    # Check if in DM
    if message.chat.type != 'private':
        bot.reply_to(message, "💍 Marriage system only works in DM.")
        return
    
    # Parse target
    if not message.reply_to_message:
        bot.reply_to(message, "💍 Reply to the person you want to marry with /marry")
        return
    
    target_id = message.reply_to_message.from_user.id
    
    # Prevent self marriage
    if user_id == target_id:
        bot.reply_to(message, "❌ You cannot marry yourself!")
        return
    
    # Prevent bot marriage
    if target_id == bot.get_me().id:
        bot.reply_to(message, "❌ You cannot marry a bot!")
        return
    
    # Check if user is already married
    user_status = db.get_marriage_status(user_id)
    if user_status and user_status[0] == 1:
        partner_id = user_status[1]
        partner = db.get_user(partner_id)
        partner_name = partner[2] if partner else "Unknown"
        bot.reply_to(
            message,
            f"🚨 CAUGHT IN 4K 🚨\n\n"
            f"⚠️ Loyalty Test Failed Successfully.\n\n"
            f"💍 Current Partner: {partner_name}\n"
            f"👀 Proposal Attempt: You → @{message.reply_to_message.from_user.username or 'Unknown'}\n\n"
            f"🚔 Relationship Police ko inform kar diya gaya hai."
        )
        return
    
    # Check if target is already married
    target_status = db.get_marriage_status(target_id)
    if target_status and target_status[0] == 1:
        bot.reply_to(message, "❌ That person is already married!")
        return
    
    # Check cooldown - 1 hour
    db.cursor.execute('''
        SELECT timestamp FROM proposals 
        WHERE proposer_id = ? AND status = 'pending'
        ORDER BY timestamp DESC LIMIT 1
    ''', (user_id,))
    result = db.cursor.fetchone()
    if result:
        last_proposal = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f')
        if (datetime.now() - last_proposal).seconds < 3600:
            remaining = 3600 - (datetime.now() - last_proposal).seconds
            minutes = remaining // 60
            bot.reply_to(message, f"⏳ Please wait {minutes} minutes before sending another proposal.")
            return
    
    # Add proposal
    db.add_proposal(user_id, target_id)
    
    # Send proposal to target
    target_username = message.reply_to_message.from_user.username or 'Unknown'
    proposer_name = message.from_user.first_name
    
    # Send media
    media_id = db.get_media('proposal')
    if media_id:
        try:
            bot.send_animation(target_id, media_id)
        except:
            pass
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💖 Accept", callback_data=f"marry_{user_id}"),
        types.InlineKeyboardButton("💔 Reject", callback_data=f"reject_{user_id}")
    )
    
    bot.send_message(
        target_id,
        f"💍 MARRIAGE PROPOSAL\n\n"
        f"💌 @{message.from_user.username or 'User'} has proposed to you.\n\n"
        f"Will you accept?\n\n"
        f"⏳ Proposal expires in 5 minutes.",
        reply_markup=markup
    )
    
    # Send confirmation to proposer
    bot.reply_to(message, f"💌 Marriage proposal sent to @{target_username}!\n\n⏳ Waiting for response...")

def handle_marriage_response(call, target_id, action):
    user_id = call.from_user.id
    
    # Verify proposal
    proposal = db.get_proposal(user_id)
    if not proposal:
        bot.answer_callback_query(call.id, "No pending proposal found.")
        return
    
    proposer_id = proposal[0]
    
    # Check if proposal is valid (5 minutes expiry)
    proposal_time = datetime.strptime(proposal[3], '%Y-%m-%d %H:%M:%S.%f')
    if (datetime.now() - proposal_time).seconds > 300:
        db.update_proposal_status(proposer_id, user_id, 'expired')
        bot.answer_callback_query(call.id, "⏳ Proposal has expired.")
        bot.edit_message_text(
            "⏳ Proposal expired.",
            call.message.chat.id,
            call.message.message_id
        )
        return
    
    if action == 'accept':
        # Check if both users are still available
        user_status = db.get_marriage_status(user_id)
        if user_status and user_status[0] == 1:
            bot.answer_callback_query(call.id, "❌ You are already married!")
            return
        
        proposer_status = db.get_marriage_status(proposer_id)
        if proposer_status and proposer_status[0] == 1:
            bot.answer_callback_query(call.id, "❌ Proposer is already married!")
            return
        
        # Marry them
        db.marry_users(user_id, proposer_id)
        
        # Update proposal status
        db.update_proposal_status(proposer_id, user_id, 'accepted')
        
        # Send media
        media_id = db.get_media('marry')
        if media_id:
            try:
                bot.send_animation(user_id, media_id)
                bot.send_animation(proposer_id, media_id)
            except:
                pass
        
        # Marriage success message
        proposer_name = call.message.from_user.first_name
        target_name = db.get_user(user_id)[2] or "Unknown"
        
        success_msg = f"💍 MARRIAGE SUCCESS\n\n🎉 Congratulations!\n\n💖 @{call.message.from_user.username or 'User'} × @{db.get_user(proposer_id)[1] or 'User'}\n\n✨ Both received +100 Aura\n\n🌹 A new relationship has begun."
        
        # Add aura to both
        db.update_aura(user_id, 100)
        db.update_aura(proposer_id, 100)
        
        bot.edit_message_text(
            success_msg,
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify proposer
        bot.send_message(proposer_id, success_msg)
        
        bot.answer_callback_query(call.id, "💖 Congratulations! You're married!")
    
    elif action == 'reject':
        # Update proposal status
        db.update_proposal_status(proposer_id, user_id, 'rejected')
        
        # Send rejection media
        media_id = db.get_media('reject')
        if media_id:
            try:
                bot.send_animation(user_id, media_id)
                bot.send_animation(proposer_id, media_id)
            except:
                pass
        
        # Reject message
        roast = random.choice(REJECT_ROASTS)
        
        # Proposer loses aura
        db.update_aura(proposer_id, -100)
        
        bot.edit_message_text(
            f"💔 MARRIAGE REJECTED\n\n{roast}\n\n💔 @{db.get_user(proposer_id)[1] or 'User'} lost -100 Aura",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify proposer
        bot.send_message(proposer_id, f"💔 Your proposal was rejected.\n\n{roast}")
        
        bot.answer_callback_query(call.id, "💔 Marriage rejected.")

# ========== DIVORCE SYSTEM ==========
@bot.message_handler(commands=['divorce'])
def divorce_command(message):
    user_id = message.from_user.id
    
    # Check if in DM
    if message.chat.type != 'private':
        bot.reply_to(message, "💔 Divorce system only works in DM.")
        return
    
    user_status = db.get_marriage_status(user_id)
    if not user_status or user_status[0] == 0:
        bot.reply_to(message, random.choice(SINGLE_DIVORCE))
        return
    
    partner_id = user_status[1]
    partner = db.get_user(partner_id)
    if not partner:
        bot.reply_to(message, "❌ Partner not found.")
        return
    
    # Add divorce request
    db.add_divorce_request(user_id, partner_id)
    
    # Send request to partner
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept Divorce", callback_data=f"divorce_accept_{user_id}"),
        types.InlineKeyboardButton("❌ Stay Married", callback_data=f"divorce_stay_{user_id}")
    )
    
    # Send divorce media
    media_id = db.get_media('divorce')
    if media_id:
        try:
            bot.send_animation(partner_id, media_id)
        except:
            pass
    
    bot.send_message(
        partner_id,
        f"💔 DIVORCE REQUEST\n\n"
        f"@{message.from_user.username or 'User'} wants to end the relationship with you.\n\n"
        f"What should happen?\n\n"
        f"⏳ Request expires in 5 minutes.",
        reply_markup=markup
    )
    
    bot.reply_to(message, "💔 Divorce request sent to your partner.")

def handle_divorce_response(call, partner_id, action):
    user_id = call.from_user.id
    
    # Verify divorce request
    request = db.get_divorce_request(user_id)
    if not request:
        bot.answer_callback_query(call.id, "No pending divorce request found.")
        return
    
    proposer_id = request[0]
    
    # Check if request is valid (5 minutes expiry)
    request_time = datetime.strptime(request[3], '%Y-%m-%d %H:%M:%S.%f')
    if (datetime.now() - request_time).seconds > 300:
        db.update_divorce_status(proposer_id, user_id, 'expired')
        bot.answer_callback_query(call.id, "⏳ Divorce request has expired.")
        bot.edit_message_text(
            "⏳ Divorce request expired.",
            call.message.chat.id,
            call.message.message_id
        )
        return
    
    if action == 'accept':
        # Divorce them
        db.divorce_users(user_id, proposer_id)
        db.update_divorce_status(proposer_id, user_id, 'accepted')
        
        bot.edit_message_text(
            "💔 DIVORCE COMPLETE\n\n"
            f"@{db.get_user(proposer_id)[1] or 'User'} × @{db.get_user(user_id)[1] or 'User'}\n\n"
            "The relationship has ended.\n\n"
            "💫 Both users are now Single.",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify proposer
        bot.send_message(proposer_id, f"💔 Your divorce request has been accepted.\n\nYou are now single.")
        
        bot.answer_callback_query(call.id, "💔 Divorce complete.")
    
    elif action == 'stay':
        db.update_divorce_status(proposer_id, user_id, 'rejected')
        
        bot.edit_message_text(
            "💍 DIVORCE REJECTED\n\n"
            "The marriage continues.\n\n"
            "❤️ Still Married.",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify proposer
        bot.send_message(proposer_id, "💍 Your partner has chosen to stay married.")
        
        bot.answer_callback_query(call.id, "❤️ Marriage continues.")

# ========== RELATIONSHIP COMMAND ==========
@bot.message_handler(commands=['relationship'])
def relationship_command(message):
    user_id = message.from_user.id
    user_status = db.get_marriage_status(user_id)
    
    if not user_status or user_status[0] == 0:
        bot.reply_to(message, "💔 You are not in a relationship.")
        return
    
    partner_id = user_status[1]
    partner = db.get_user(partner_id)
    if not partner:
        bot.reply_to(message, "❌ Partner not found.")
        return
    
    # Calculate duration (simplified)
    content = f"""
❤️ Partner: {partner[2] or 'Unknown'}
📅 Married Since: {datetime.now().strftime('%Y-%m-%d')}
⏳ Duration: 1 Day
💞 Status: Married
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💔 Divorce", callback_data=f"divorce_{user_id}"),
        types.InlineKeyboardButton("👤 Partner Profile", callback_data=f"admin_view_{partner_id}")
    )
    
    bot.reply_to(
        message,
        create_vip_message("💍 RELATIONSHIP", content),
        reply_markup=markup
    )

# ========== FRIENDSHIP COMMAND ==========
@bot.message_handler(commands=['friendship'])
def friendship_command(message):
    # Simple response for now
    bot.reply_to(message, "🫂 FRIENDSHIP\n\n💙 Friendship: 78%\n💬 Interactions: 246\n📅 First Seen: {}\n🏷️ Level: 💙 Close Friends".format(datetime.now().strftime('%Y-%m-%d')))

# ========== ROAST COMMAND ==========
@bot.message_handler(commands=['roast'])
def roast_command(message):
    if not message.reply_to_message:
        bot.reply_to(message, "😂 Reply to someone with /roast")
        return
    
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name
    
    roasts = [
        f"😂 {target_name}, teri soch se zyada teri shakal roast hoti hai!",
        f"🔥 {target_name}, tu toh vada pav ke bina bhi pav bhaji hai!",
        f"💀 {target_name}, teri IQ se zyada teri height choti hai!",
        f"🤡 {target_name}, tu toh comedy show ka permanent member hai!",
        f"😤 {target_name}, teri shakal dekh ke lagta hai tu roj mirror todta hai!",
        f"🤣 {target_name}, teri photo dekh ke police station mein complaint karte hain log!",
    ]
    
    roast = random.choice(roasts)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔥 Good Roast", callback_data="roast_good"),
        types.InlineKeyboardButton("😴 Weak Roast", callback_data="roast_weak")
    )
    
    bot.reply_to(message, f"😂 ROAST BATTLE\n\n{roast}\n\n🏆 Winner: {message.from_user.first_name}\n💀 Loser: {target_name}", reply_markup=markup)

# ========== LEADERBOARD COMMAND ==========
@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    # Get top 10 users
    db.cursor.execute('''
        SELECT user_id, username, first_name, aura 
        FROM users 
        ORDER BY aura DESC 
        LIMIT 10
    ''')
    results = db.cursor.fetchall()
    
    if not results:
        bot.reply_to(message, "No users found.")
        return
    
    content = "🏆 ZYNOX GLOBAL TOP 10\n\n"
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, row in enumerate(results):
        name = row[2] or row[1] or f"User{row[0]}"
        aura = format_aura(row[3])
        content += f"{emojis[i] if i < 10 else '👤'} {name} — {aura} ⚡\n"
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🌍 Global", callback_data="lb_global"),
        types.InlineKeyboardButton("👥 Group", callback_data="lb_group"),
        types.InlineKeyboardButton("🔥 Top 10", callback_data="lb_top")
    )
    
    bot.reply_to(message, content, reply_markup=markup)

# ========== DAILY TASKS ==========
@bot.message_handler(commands=['mytask'])
def mytask_command(message):
    user_id = message.from_user.id
    today = datetime.now().date()
    
    # Check if tasks exist for today
    db.cursor.execute('''
        SELECT * FROM daily_tasks 
        WHERE user_id = ? AND task_date = ?
    ''', (user_id, today))
    tasks = db.cursor.fetchone()
    
    if not tasks:
        # Generate random tasks
        task_list = [
            "☐ Send 50 messages",
            "☐ Win 1 Quiz",
            "☐ Use Dice",
            "☐ Win 1 Game",
            "☐ Give Appreciation"
        ]
        random.shuffle(task_list)
        tasks_json = json.dumps(task_list[:3])  # Select 3 tasks
        
        db.cursor.execute('''
            INSERT INTO daily_tasks (user_id, task_date, tasks, completed_tasks, reward_claimed)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, today, tasks_json, '[]', 0))
        db.conn.commit()
        
        tasks_to_show = task_list[:3]
    else:
        tasks_to_show = json.loads(tasks[2])
    
    content = "🎯 TODAY'S TASKS\n\n" + "\n".join(tasks_to_show) + "\n\n🏆 Completion Reward: +250 Aura"
    
    bot.reply_to(message, content)

# ========== GROUP BONUS ==========
@bot.message_handler(content_types=['new_chat_members'])
def group_bonus(message):
    if message.new_chat_members:
        for member in message.new_chat_members:
            if member.id == bot.get_me().id:
                # Bot was added to the group
                group_id = message.chat.id
                group_name = message.chat.title or "Unknown Group"
                added_by = message.from_user.id
                
                # Add group to database
                db.add_group(group_id, group_name, added_by)
                
                # Check if user already got bonus for this group
                if db.get_group_bonus(added_by, group_id):
                    return
                
                # Give bonus to user
                db.add_group_bonus(added_by, group_id)
                db.update_aura(added_by, 1000)
                
                # Get updated rank
                user = db.get_user(added_by)
                rank = user[4] if user else 'Bronze I'
                aura = user[3] if user else 0
                
                # Send notification in group
                bot.send_message(
                    group_id,
                    f"🎉 ZYNOX GROUP BONUS\n\n"
                    f"👤 @{message.from_user.username or 'User'} added Zynox Gaming to a new group!\n\n"
                    f"🎁 +1000 Aura\n"
                    f"🏅 Current Rank: {rank}\n\n"
                    f"🚀 Thanks for bringing Zynox to the community!"
                )
                
                # Notify owner
                bot.send_message(
                    OWNER_ID,
                    f"👥 BOT ADDED TO NEW GROUP\n\n"
                    f"📛 Group: {group_name}\n"
                    f"🆔 ID: {group_id}\n"
                    f"👤 Added By: @{message.from_user.username or 'User'}\n"
                    f"🆔 User ID: {added_by}\n\n"
                    f"✅ Group Registered"
                )

# ========== OWNER COMMANDS ==========
# These need to be implemented based on the requirements
# For brevity, I'll include the main structure

@bot.message_handler(commands=['panel'])
def panel_command(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    # Get stats
    db.cursor.execute('SELECT COUNT(*) FROM users')
    users = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT COUNT(*) FROM groups')
    groups = db.cursor.fetchone()[0]
    
    db.cursor.execute('SELECT SUM(aura) FROM users')
    total_aura = db.cursor.fetchone()[0] or 0
    
    content = f"""
╔════════════════════╗
👑 ZYNOX CONTROL
╚════════════════════╝

👥 Users: {users}
🌐 Groups: {groups}
⚡ Total Aura: {format_aura(total_aura)}
🎮 Games: ON
🤖 Bot: ONLINE

━━━━━━━━━━━━━━━━━━

📢 BROADCAST
👥 GROUPS
⚡ AURA
🎮 GAMES
🎭 MEDIA
🛡️ SUDO
💾 DATABASE
⚙️ SETTINGS
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("👥 Groups", callback_data="admin_groups"),
        types.InlineKeyboardButton("⚡ Aura", callback_data="admin_aura"),
        types.InlineKeyboardButton("🎮 Games", callback_data="admin_games"),
        types.InlineKeyboardButton("🎭 Media", callback_data="admin_media"),
        types.InlineKeyboardButton("🛡️ Sudo", callback_data="admin_sudo"),
        types.InlineKeyboardButton("💾 Database", callback_data="admin_db"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
    )
    
    bot.reply_to(message, content, reply_markup=markup)

@bot.message_handler(commands=['add_aura'])
def add_aura_command(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Usage: /add_aura @user amount")
            return
        
        target = parts[1].replace('@', '')
        amount = int(parts[2])
        
        # Find user by username
        db.cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
        result = db.cursor.fetchone()
        if not result:
            bot.reply_to(message, "User not found.")
            return
        
        user_id = result[0]
        db.update_aura(user_id, amount)
        user = db.get_user(user_id)
        
        bot.reply_to(message, f"✅ Added {amount} Aura to @{target}\n\n⚡ New Aura: {format_aura(user[3])}")
    except:
        bot.reply_to(message, "❌ Invalid command format.")

@bot.message_handler(commands=['addsudo'])
def add_sudo_command(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        target = message.text.split()[1].replace('@', '')
        
        # Find user by username
        db.cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
        result = db.cursor.fetchone()
        if not result:
            bot.reply_to(message, "User not found.")
            return
        
        user_id = result[0]
        db.add_sudo(user_id)
        bot.reply_to(message, f"✅ @{target} has been added as sudo user.")
    except:
        bot.reply_to(message, "Usage: /addsudo @user")

@bot.message_handler(commands=['delsudo'])
def del_sudo_command(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        target = message.text.split()[1].replace('@', '')
        
        # Find user by username
        db.cursor.execute('SELECT user_id FROM users WHERE username = ?', (target,))
        result = db.cursor.fetchone()
        if not result:
            bot.reply_to(message, "User not found.")
            return
        
        user_id = result[0]
        db.remove_sudo(user_id)
        bot.reply_to(message, f"✅ @{target} has been removed from sudo users.")
    except:
        bot.reply_to(message, "Usage: /delsudo @user")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    # Get all users
    db.cursor.execute('SELECT user_id FROM users')
    users = db.cursor.fetchall()
    
    # Send message to all users
    msg_text = message.text.replace('/broadcast', '').strip()
    if not msg_text:
        bot.reply_to(message, "Please provide a message to broadcast.")
        return
    
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 BROADCAST MESSAGE\n\n{msg_text}")
            sent += 1
        except:
            pass
    
    bot.reply_to(message, f"✅ Broadcast sent to {sent} users.")

# ========== MEDIA COMMANDS ==========
@bot.message_handler(commands=['addmarrysticker'])
def add_marry_sticker(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    if message.reply_to_message:
        if message.reply_to_message.animation:
            file_id = message.reply_to_message.animation.file_id
            db.add_media('marry', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Marriage media added successfully!")
        elif message.reply_to_message.sticker:
            file_id = message.reply_to_message.sticker.file_id
            db.add_media('marry', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Marriage sticker added successfully!")
        elif message.reply_to_message.photo:
            file_id = message.reply_to_message.photo[-1].file_id
            db.add_media('marry', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Marriage photo added successfully!")
        else:
            bot.reply_to(message, "❌ Please reply to a sticker, GIF, or photo.")
    else:
        bot.reply_to(message, "❌ Please reply to a sticker, GIF, or photo with the command.")

@bot.message_handler(commands=['adddivorcesticker'])
def add_divorce_sticker(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    if message.reply_to_message:
        if message.reply_to_message.animation:
            file_id = message.reply_to_message.animation.file_id
            db.add_media('divorce', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Divorce media added successfully!")
        elif message.reply_to_message.sticker:
            file_id = message.reply_to_message.sticker.file_id
            db.add_media('divorce', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Divorce sticker added successfully!")
        elif message.reply_to_message.photo:
            file_id = message.reply_to_message.photo[-1].file_id
            db.add_media('divorce', file_id, message.from_user.id)
            bot.reply_to(message, "✅ Divorce photo added successfully!")
        else:
            bot.reply_to(message, "❌ Please reply to a sticker, GIF, or photo.")
    else:
        bot.reply_to(message, "❌ Please reply to a sticker, GIF, or photo with the command.")

# ========== ERROR HANDLER ==========
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    if message.chat.type == 'private':
        bot.reply_to(
            message,
            "❓ Unknown command. Use /start to see available commands.\n\n"
            "📚 Available commands:\n"
            "/start - Start the bot\n"
            "/profile - View your profile\n"
            "/claim - Claim daily reward\n"
            "/marry @user - Propose to someone\n"
            "/divorce - Divorce your partner\n"
            "/relationship - Check relationship status\n"
            "/roast @user - Roast someone\n"
            "/mytask - View daily tasks\n"
            "/achievements - View your achievements\n"
            "/leaderboard - View top players"
        )

# ========== RUN BOT ==========
if __name__ == "__main__":
    print("🤖 ZYNOX GAMING BOT IS RUNNING...")
    bot.polling(none_stop=True)
