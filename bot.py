# Complete fixed code with all working systems

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
        self.create_group_management_tables()
    
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
        
        # Add default quiz questions if none exist
        self.cursor.execute('SELECT COUNT(*) FROM quiz_questions')
        if self.cursor.fetchone()[0] == 0:
            default_questions = [
                ('GK', 'Which planet is known as the Red Planet?', '["Earth","Mars","Venus","Jupiter"]', 1),
                ('GK', 'What is the largest ocean on Earth?', '["Atlantic","Pacific","Indian","Arctic"]', 1),
                ('GK', 'Who wrote "Hamlet"?', '["Shakespeare","Dickens","Hemingway","Tolkien"]', 0),
                ('Gaming', 'What is the most popular game in 2024?', '["PUBG","Fortnite","Minecraft","GTA V"]', 2),
                ('Gaming', 'Which company created GTA?', '["EA","Ubisoft","Rockstar","Activision"]', 2),
                ('Sports', 'Which sport is known as the "king of sports"?', '["Cricket","Football","Basketball","Tennis"]', 1),
                ('Sports', 'How many players are in a cricket team?', '["11","10","9","12"]', 0),
                ('Movies', 'Who played Iron Man?', '["Chris Evans","Robert Downey Jr.","Chris Hemsworth","Mark Ruffalo"]', 1),
                ('Movies', 'What is the highest grossing movie of all time?', '["Avatar","Titanic","Avengers","Star Wars"]', 0),
                ('Riddles', 'I have cities, but no houses. I have mountains, but no trees. I have water, but no fish. What am I?', '["Map","Globe","Book","Painting"]', 0),
            ]
            
            for q in default_questions:
                self.cursor.execute('''
                    INSERT INTO quiz_questions (category, question, options, answer)
                    VALUES (?, ?, ?, ?)
                ''', (q[0], q[1], q[2], q[3]))
            
            self.conn.commit()
    
    def create_group_management_tables(self):
        """Create group management tables"""
        # Group settings table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                group_id INTEGER PRIMARY KEY,
                welcome_enabled INTEGER DEFAULT 1,
                goodbye_enabled INTEGER DEFAULT 1,
                anti_spam INTEGER DEFAULT 1,
                anti_links INTEGER DEFAULT 0,
                anti_media INTEGER DEFAULT 0,
                language TEXT DEFAULT 'en',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Group admins table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_admins (
                group_id INTEGER,
                user_id INTEGER,
                promoted_by INTEGER,
                promotion_level INTEGER DEFAULT 1,
                promotion_title TEXT DEFAULT 'Member',
                promoted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )
        ''')
        
        # Muted users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS muted_users (
                group_id INTEGER,
                user_id INTEGER,
                muted_by INTEGER,
                mute_duration INTEGER,
                mute_reason TEXT,
                muted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                unmuted_at DATETIME,
                PRIMARY KEY (group_id, user_id)
            )
        ''')
        
        # Warnings table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_warnings (
                group_id INTEGER,
                user_id INTEGER,
                warned_by INTEGER,
                warning_reason TEXT,
                warning_level INTEGER DEFAULT 1,
                warned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id, warned_at)
            )
        ''')
        
        # Banned users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                group_id INTEGER,
                user_id INTEGER,
                banned_by INTEGER,
                ban_reason TEXT,
                banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )
        ''')
        
        self.conn.commit()
    
    def get_group_setting(self, group_id, setting_key):
        self.cursor.execute(
            f'SELECT {setting_key} FROM group_settings WHERE group_id = ?',
            (group_id,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 1
    
    def update_group_setting(self, group_id, setting_key, value):
        self.cursor.execute(
            f'UPDATE group_settings SET {setting_key} = ? WHERE group_id = ?',
            (value, group_id)
        )
        self.conn.commit()
    
    def add_group_admin(self, group_id, user_id, promoted_by, level=1):
        titles = {1: 'Member', 2: 'Senior Member', 3: 'VIP Member', 4: 'Elite Member', 5: 'Legendary Member'}
        title = titles.get(level, 'Member')
        self.cursor.execute('''
            INSERT OR REPLACE INTO group_admins 
            (group_id, user_id, promoted_by, promotion_level, promotion_title)
            VALUES (?, ?, ?, ?, ?)
        ''', (group_id, user_id, promoted_by, level, title))
        self.conn.commit()
    
    def remove_group_admin(self, group_id, user_id):
        self.cursor.execute('''
            DELETE FROM group_admins WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        self.conn.commit()
    
    def get_group_admins(self, group_id):
        self.cursor.execute('''
            SELECT * FROM group_admins WHERE group_id = ? ORDER BY promotion_level DESC
        ''', (group_id,))
        return self.cursor.fetchall()
    
    def is_group_admin(self, group_id, user_id):
        self.cursor.execute('''
            SELECT * FROM group_admins WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        return self.cursor.fetchone() is not None
    
    def add_muted_user(self, group_id, user_id, muted_by, duration, reason=''):
        unmuted_at = datetime.now() + timedelta(seconds=duration)
        self.cursor.execute('''
            INSERT OR REPLACE INTO muted_users 
            (group_id, user_id, muted_by, mute_duration, mute_reason, unmuted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (group_id, user_id, muted_by, duration, reason, unmuted_at))
        self.conn.commit()
    
    def remove_muted_user(self, group_id, user_id):
        self.cursor.execute('''
            DELETE FROM muted_users WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        self.conn.commit()
    
    def is_muted(self, group_id, user_id):
        self.cursor.execute('''
            SELECT * FROM muted_users 
            WHERE group_id = ? AND user_id = ? AND unmuted_at > datetime('now')
        ''', (group_id, user_id))
        return self.cursor.fetchone() is not None
    
    def get_muted_users(self, group_id):
        self.cursor.execute('''
            SELECT * FROM muted_users 
            WHERE group_id = ? AND unmuted_at > datetime('now')
        ''', (group_id,))
        return self.cursor.fetchall()
    
    def add_warning(self, group_id, user_id, warned_by, reason, level=1):
        self.cursor.execute('''
            INSERT INTO user_warnings 
            (group_id, user_id, warned_by, warning_reason, warning_level)
            VALUES (?, ?, ?, ?, ?)
        ''', (group_id, user_id, warned_by, reason, level))
        self.conn.commit()
        
        # Check if user has too many warnings (3 = mute, 5 = ban)
        self.cursor.execute('''
            SELECT COUNT(*) FROM user_warnings 
            WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        count = self.cursor.fetchone()[0]
        return count
    
    def clear_warnings(self, group_id, user_id):
        self.cursor.execute('''
            DELETE FROM user_warnings WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        self.conn.commit()
    
    def add_banned_user(self, group_id, user_id, banned_by, reason=''):
        self.cursor.execute('''
            INSERT OR REPLACE INTO banned_users 
            (group_id, user_id, banned_by, ban_reason)
            VALUES (?, ?, ?, ?)
        ''', (group_id, user_id, banned_by, reason))
        self.conn.commit()
    
    def remove_banned_user(self, group_id, user_id):
        self.cursor.execute('''
            DELETE FROM banned_users WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        self.conn.commit()
    
    def is_banned(self, group_id, user_id):
        self.cursor.execute('''
            SELECT * FROM banned_users WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        return self.cursor.fetchone() is not None
    
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

def is_admin_in_group(message):
    """Check if user is admin in the group"""
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_bot_admin_in_group(chat_id):
    """Check if bot is admin in the group"""
    try:
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        return bot_member.status in ['administrator', 'creator']
    except:
        return False

def is_user_in_group(user_id, group_id):
    try:
        member = bot.get_chat_member(group_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def check_support_membership(user_id):
    try:
        # Extract group and channel IDs from links
        group_id = SUPPORT_GROUP.split('/')[-1]
        channel_id = SUPPORT_CHANNEL.split('/')[-1]
        
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
        try:
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
        except:
            bot.answer_callback_query(call.id, "Please use /start to see the menu.")
    
    elif data == "groups":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👥 Support Group", url=SUPPORT_GROUP),
            types.InlineKeyboardButton("📢 Support Channel", url=SUPPORT_CHANNEL),
            types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start")
        )
        try:
            bot.edit_message_text(
                "👥 ZYNOX COMMUNITY\n\n"
                "Join our official communities:\n\n"
                "👥 Support Group - Get help and connect with others\n"
                "📢 Support Channel - Latest updates and announcements",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except:
            bot.answer_callback_query(call.id, "Please use /start to see the menu.")
    
    elif data == "profile":
        try:
            profile_command(call.message)
            bot.answer_callback_query(call.id)
        except:
            bot.answer_callback_query(call.id, "Please use /profile command.")
    
    elif data == "updates":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
        try:
            bot.edit_message_text(
                "📢 ZYNOX UPDATES\n\n"
                "Stay tuned for the latest updates!\n"
                "Join our Support Channel for announcements.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except:
            bot.answer_callback_query(call.id, "Please use /start to see the menu.")
    
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
        try:
            bot.edit_message_text(
                "🎮 ZYNOX GAMES\n\n"
                "Choose a game to play and earn Aura!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except:
            bot.answer_callback_query(call.id, "Please use /start to see the menu.")
    
    elif data == "add_bot":
        bot.answer_callback_query(call.id, "Add Zynox Gaming to your group from the bot's profile!")
    
    elif data == "back_to_start":
        try:
            start_command(call.message)
        except:
            bot.send_message(call.message.chat.id, "Please use /start to see the menu.")
    
    elif data.startswith("game_"):
        game_name = data.replace("game_", "")
        if game_name == "dice":
            game_dice(call.message)
        elif game_name == "rps":
            game_rps(call.message)
        elif game_name == "quiz":
            game_quiz(call.message)
        elif game_name == "guess":
            game_guess(call.message)
        elif game_name == "math":
            game_math(call.message)
        elif game_name == "slots":
            game_slots(call.message)
        else:
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
    
    elif data.startswith("set_"):
        settings_callback_handler(call)

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
        try:
            bot.edit_message_text("User not found.", call.message.chat.id, call.message.message_id)
        except:
            pass
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
    try:
        bot.edit_message_text(
            content,
            call.message.chat.id,
            call.message.message_id
        )
    except:
        pass

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
    
    # Parse target - works in both DM and Group
    target_user = None
    target_id = None
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_user = message.reply_to_message.from_user
    elif message.text and len(message.text.split()) > 1:
        # Try to get user from mention
        try:
            target_username = message.text.split()[1].replace('@', '')
            # Find user in chat
            if message.chat.type == 'group' or message.chat.type == 'supergroup':
                for member in bot.get_chat_members(message.chat.id):
                    if member.user.username == target_username:
                        target_id = member.user.id
                        target_user = member.user
                        break
        except:
            pass
    
    if not target_id:
        bot.reply_to(message, "💍 Reply to the person you want to marry with /marry\nOr use: /marry @username")
        return
    
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
            f"👀 Proposal Attempt: You → @{target_user.username or 'Unknown' if target_user else 'Unknown'}\n\n"
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
    target_name = target_user.first_name if target_user else "User"
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
    
    # Send in DM to target if in group, or in chat if in DM
    try:
        bot.send_message(
            target_id,
            f"💍 MARRIAGE PROPOSAL\n\n"
            f"💌 @{message.from_user.username or 'User'} has proposed to you.\n\n"
            f"Will you accept?\n\n"
            f"⏳ Proposal expires in 5 minutes.",
            reply_markup=markup
        )
    except:
        bot.reply_to(message, "❌ Could not send proposal. Make sure the user has started the bot.")
        return
    
    # Send confirmation to proposer
    bot.reply_to(message, f"💌 Marriage proposal sent to @{target_user.username or 'Unknown'}!\n\n⏳ Waiting for response...")

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
        try:
            bot.edit_message_text(
                "⏳ Proposal expired.",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
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
        proposer = db.get_user(proposer_id)
        target = db.get_user(user_id)
        proposer_name = proposer[2] if proposer else "User"
        target_name = target[2] if target else "User"
        
        success_msg = f"💍 MARRIAGE SUCCESS\n\n🎉 Congratulations!\n\n💖 {proposer_name} × {target_name}\n\n✨ Both received +100 Aura\n\n🌹 A new relationship has begun."
        
        # Add aura to both
        db.update_aura(user_id, 100)
        db.update_aura(proposer_id, 100)
        
        try:
            bot.edit_message_text(
                success_msg,
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        
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
        
        try:
            bot.edit_message_text(
                f"💔 MARRIAGE REJECTED\n\n{roast}\n\n💔 {db.get_user(proposer_id)[2] or 'User'} lost -100 Aura",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        
        # Notify proposer
        proposer = db.get_user(proposer_id)
        bot.send_message(proposer_id, f"💔 Your proposal was rejected.\n\n{roast}")
        
        bot.answer_callback_query(call.id, "💔 Marriage rejected.")

# ========== DIVORCE SYSTEM ==========
@bot.message_handler(commands=['divorce'])
def divorce_command(message):
    user_id = message.from_user.id
    
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
    
    partner_name = partner[2] or "Partner"
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
        try:
            bot.edit_message_text(
                "⏳ Divorce request expired.",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        return
    
    if action == 'accept':
        # Divorce them
        db.divorce_users(user_id, proposer_id)
        db.update_divorce_status(proposer_id, user_id, 'accepted')
        
        proposer = db.get_user(proposer_id)
        target = db.get_user(user_id)
        proposer_name = proposer[2] if proposer else "User"
        target_name = target[2] if target else "User"
        
        try:
            bot.edit_message_text(
                f"💔 DIVORCE COMPLETE\n\n"
                f"{proposer_name} × {target_name}\n\n"
                "The relationship has ended.\n\n"
                "💫 Both users are now Single.",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        
        # Notify proposer
        bot.send_message(proposer_id, f"💔 Your divorce request has been accepted.\n\nYou are now single.")
        
        bot.answer_callback_query(call.id, "💔 Divorce complete.")
    
    elif action == 'stay':
        db.update_divorce_status(proposer_id, user_id, 'rejected')
        
        try:
            bot.edit_message_text(
                "💍 DIVORCE REJECTED\n\n"
                "The marriage continues.\n\n"
                "❤️ Still Married.",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        
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
    if not message.reply_to_message:
        bot.reply_to(message, "🫂 Reply to someone with /friendship")
        return
    
    target = message.reply_to_message.from_user
    content = f"""
🫂 FRIENDSHIP

👤 {message.from_user.first_name}
👤 {target.first_name}

💙 Friendship: {random.randint(50, 95)}%
💬 Interactions: {random.randint(100, 500)}
📅 First Seen: {datetime.now().strftime('%Y-%m-%d')}
🏷️ Level: 💙 Close Friends
"""
    
    bot.reply_to(message, content)

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
    
    # Random Aura change
    winner_aura = random.randint(5, 15)
    loser_aura = random.randint(5, 15)
    
    db.update_aura(message.from_user.id, winner_aura)
    db.update_aura(target_id, -loser_aura)
    
    bot.reply_to(
        message,
        f"😂 ROAST BATTLE\n\n{roast}\n\n🏆 Winner: {message.from_user.first_name} (+{winner_aura} Aura)\n💀 Loser: {target_name} (-{loser_aura} Aura)"
    )

# ========== GAMES ==========

# Dice Game
@bot.message_handler(commands=['dice'])
def game_dice(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    # Check cooldown (30 seconds)
    if hasattr(game_dice, 'cooldown') and user_id in game_dice.cooldown:
        if (datetime.now() - game_dice.cooldown[user_id]).seconds < 30:
            bot.reply_to(message, "⏳ Please wait 30 seconds before rolling again.")
            return
    
    # Roll dice
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    if user_roll > bot_roll:
        reward = random.randint(10, 30)
        db.update_aura(user_id, reward)
        result = f"🎉 You win! +{reward} Aura"
    elif user_roll < bot_roll:
        loss = random.randint(5, 15)
        db.update_aura(user_id, -loss)
        result = f"😔 You lose! -{loss} Aura"
    else:
        result = "🤝 It's a tie! No Aura lost or gained."
    
    # Save cooldown
    if not hasattr(game_dice, 'cooldown'):
        game_dice.cooldown = {}
    game_dice.cooldown[user_id] = datetime.now()
    
    content = f"""
🎲 DICE GAME

You rolled: 🎲 {user_roll}
Bot rolled: 🎲 {bot_roll}

{result}

━━━━━━━━━━━━━━━━━━
⚡ Aura: {format_aura(db.get_user(user_id)[3])}
"""
    bot.reply_to(message, content)

# Rock Paper Scissors Game
@bot.message_handler(commands=['rps'])
def game_rps(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🗿 Rock", callback_data="rps_rock"),
        types.InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
        types.InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")
    )
    bot.reply_to(message, "✊ Choose your move:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rps_'))
def rps_callback(call):
    user_id = call.from_user.id
    user_choice = call.data.split('_')[1]
    
    choices = ['rock', 'paper', 'scissors']
    bot_choice = random.choice(choices)
    
    emojis = {'rock': '🗿', 'paper': '📄', 'scissors': '✂️'}
    
    # Determine winner
    if user_choice == bot_choice:
        result = "🤝 It's a tie!"
        aura_change = 0
    elif (user_choice == 'rock' and bot_choice == 'scissors') or \
         (user_choice == 'paper' and bot_choice == 'rock') or \
         (user_choice == 'scissors' and bot_choice == 'paper'):
        reward = random.randint(10, 25)
        db.update_aura(user_id, reward)
        result = f"🎉 You win! +{reward} Aura"
        aura_change = reward
    else:
        loss = random.randint(5, 10)
        db.update_aura(user_id, -loss)
        result = f"😔 You lose! -{loss} Aura"
        aura_change = -loss
    
    content = f"""
✊ ROCK PAPER SCISSORS

You: {emojis[user_choice]} {user_choice.title()}
Bot: {emojis[bot_choice]} {bot_choice.title()}

{result}

━━━━━━━━━━━━━━━━━━
⚡ Aura: {format_aura(db.get_user(user_id)[3])}
"""
    try:
        bot.edit_message_text(content, call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.message.chat.id, content)
    bot.answer_callback_query(call.id)

# Quiz Game
@bot.message_handler(commands=['quiz'])
def game_quiz(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    # Get random quiz
    quiz = db.get_random_quiz()
    if not quiz:
        bot.reply_to(message, "No quiz questions available.")
        return
    
    # Store quiz in message for callback
    options_text = ""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for i, option in enumerate(quiz['options']):
        options_text += f"{chr(65+i)}. {option}\n"
        markup.add(types.InlineKeyboardButton(
            f"{chr(65+i)}. {option[:20]}",
            callback_data=f"quiz_{quiz['id']}_{i}"
        ))
    
    content = f"""
🧠 ZYNOX QUIZ

❓ {quiz['question']}

{options_text}

⚡ First correct answer wins!
"""
    bot.reply_to(message, content, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('quiz_'))
def quiz_callback(call):
    user_id = call.from_user.id
    data = call.data.split('_')
    quiz_id = int(data[1])
    selected = int(data[2])
    
    # Get quiz
    db.cursor.execute('SELECT * FROM quiz_questions WHERE id = ?', (quiz_id,))
    result = db.cursor.fetchone()
    
    if not result:
        bot.answer_callback_query(call.id, "Quiz expired.")
        return
    
    quiz = {
        'id': result[0],
        'category': result[1],
        'question': result[2],
        'options': json.loads(result[3]),
        'answer': result[4]
    }
    
    if selected == quiz['answer']:
        reward = random.randint(20, 50)
        db.update_aura(user_id, reward)
        db.cursor.execute('UPDATE users SET quiz_wins = quiz_wins + 1 WHERE user_id = ?', (user_id,))
        db.conn.commit()
        
        content = f"""
🏆 CORRECT!

🎉 @{call.from_user.username or 'User'} answered first.

⚡ +{reward} Aura

✅ Answer: {quiz['options'][quiz['answer']]}
"""
        try:
            bot.edit_message_text(content, call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(call.message.chat.id, content)
        bot.answer_callback_query(call.id, "✅ Correct! +{reward} Aura")
    else:
        # Check if someone else answered correctly
        if hasattr(quiz_callback, 'answered') and quiz_callback.answered.get(quiz_id, False):
            bot.answer_callback_query(call.id, "❌ Already answered!")
            return
        
        bot.answer_callback_query(call.id, "❌ Wrong answer! Try again.")

# Guess Number Game
@bot.message_handler(commands=['guess'])
def game_guess(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    # Generate random number
    number = random.randint(1, 10)
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(1, 11):
        buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"guess_{number}_{i}"))
    markup.add(*buttons)
    
    bot.reply_to(message, "🎯 Guess a number between 1 and 10:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('guess_'))
def guess_callback(call):
    user_id = call.from_user.id
    data = call.data.split('_')
    number = int(data[1])
    guessed = int(data[2])
    
    if guessed == number:
        reward = random.randint(15, 35)
        db.update_aura(user_id, reward)
        content = f"🎯 CORRECT! The number was {number}\n\n⚡ +{reward} Aura"
        try:
            bot.edit_message_text(content, call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(call.message.chat.id, content)
        bot.answer_callback_query(call.id, f"✅ Correct! +{reward} Aura")
    else:
        bot.answer_callback_query(call.id, f"❌ Wrong! Try again.")

# Math Battle Game
@bot.message_handler(commands=['math'])
def game_math(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    # Generate math problem
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operator = random.choice(['+', '-', '*'])
    
    if operator == '+':
        answer = num1 + num2
    elif operator == '-':
        answer = num1 - num2
    else:
        answer = num1 * num2
    
    # Store answer
    if not hasattr(game_math, 'answers'):
        game_math.answers = {}
    game_math.answers[user_id] = answer
    
    content = f"""
🔢 MATH BATTLE

Solve: {num1} {operator} {num2} = ?

Reply with: /mathanswer [number]

⚡ First correct answer wins 20-50 Aura!
"""
    bot.reply_to(message, content)

@bot.message_handler(commands=['mathanswer'])
def math_answer(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    if not hasattr(game_math, 'answers') or user_id not in game_math.answers:
        bot.reply_to(message, "No math question active. Use /math to start one.")
        return
    
    try:
        user_answer = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ Please provide a number.\nExample: /mathanswer 15")
        return
    
    correct_answer = game_math.answers[user_id]
    
    if user_answer == correct_answer:
        reward = random.randint(20, 50)
        db.update_aura(user_id, reward)
        bot.reply_to(message, f"✅ CORRECT! +{reward} Aura")
        del game_math.answers[user_id]
    else:
        bot.reply_to(message, f"❌ Wrong! The correct answer was {correct_answer}")

# Slots Game
@bot.message_handler(commands=['slots'])
def game_slots(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    # Check cooldown (10 seconds)
    if hasattr(game_slots, 'cooldown') and user_id in game_slots.cooldown:
        if (datetime.now() - game_slots.cooldown[user_id]).seconds < 10:
            bot.reply_to(message, "⏳ Please wait 10 seconds before playing again.")
            return
    
    emojis = ['🍒', '🍋', '🍊', '🍇', '💎', '7️⃣']
    
    slot1 = random.choice(emojis)
    slot2 = random.choice(emojis)
    slot3 = random.choice(emojis)
    
    # Check win
    if slot1 == slot2 == slot3:
        if slot1 == '7️⃣':
            reward = random.randint(50, 100)
        elif slot1 == '💎':
            reward = random.randint(30, 60)
        else:
            reward = random.randint(15, 35)
        db.update_aura(user_id, reward)
        result = f"🎉 JACKPOT! +{reward} Aura"
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        reward = random.randint(5, 15)
        db.update_aura(user_id, reward)
        result = f"🎊 Two of a kind! +{reward} Aura"
    else:
        loss = random.randint(5, 10)
        db.update_aura(user_id, -loss)
        result = f"😔 No match! -{loss} Aura"
    
    # Save cooldown
    if not hasattr(game_slots, 'cooldown'):
        game_slots.cooldown = {}
    game_slots.cooldown[user_id] = datetime.now()
    
    content = f"""
🎰 SLOTS

[{slot1}] [{slot2}] [{slot3}]

{result}

━━━━━━━━━━━━━━━━━━
⚡ Aura: {format_aura(db.get_user(user_id)[3])}
"""
    bot.reply_to(message, content)

# ========== GROUP MANAGEMENT COMMANDS ==========

# WELCOME SYSTEM
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    """Welcome new members to the group"""
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            # Bot added to group
            # Setup default group settings
            db.cursor.execute('''
                INSERT OR IGNORE INTO group_settings (group_id)
                VALUES (?)
            ''', (message.chat.id,))
            db.conn.commit()
            
            # Add group to database
            db.add_group(message.chat.id, message.chat.title or "Unknown Group", message.from_user.id)
            
            # Give bonus to user who added bot
            if not db.get_group_bonus(message.from_user.id, message.chat.id):
                db.add_group_bonus(message.from_user.id, message.chat.id)
                db.update_aura(message.from_user.id, 1000)
                
                # Get updated rank
                user = db.get_user(message.from_user.id)
                rank = user[4] if user else 'Bronze I'
                
                bot.send_message(
                    message.chat.id,
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
                f"📛 Group: {message.chat.title or 'Unknown'}\n"
                f"🆔 ID: {message.chat.id}\n"
                f"👤 Added By: @{message.from_user.username or 'User'}\n"
                f"🆔 User ID: {message.from_user.id}\n\n"
                f"✅ Group Registered"
            )
            return
        
        # Check if welcome enabled
        if db.get_group_setting(message.chat.id, 'welcome_enabled'):
            welcome_media = db.get_media('welcome')
            welcome_text = f"""
╔════════════════════╗
👋 WELCOME TO THE GROUP
╚════════════════════╝

🎮 Welcome {member.first_name}!

━━━━━━━━━━━━━━━━━━
🌟 Enjoy your stay and earn Aura!
💡 Type /help for commands
"""

            if welcome_media:
                try:
                    bot.send_animation(message.chat.id, welcome_media, caption=welcome_text)
                except:
                    bot.send_message(message.chat.id, welcome_text)
            else:
                bot.send_message(message.chat.id, welcome_text)

# MUTE SYSTEM
@bot.message_handler(commands=['mute'])
def mute_command(message):
    """Mute a user in the group"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to mute users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /mute [duration] [reason]\n\nDurations: 1m, 5m, 10m, 30m, 1h, 2h, 6h, 12h, 1d, 7d")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    # Parse duration and reason
    parts = message.text.split(' ', 2)
    duration_text = parts[1] if len(parts) > 1 else '1h'
    reason = parts[2] if len(parts) > 2 else 'No reason provided'
    
    # Get duration in seconds
    durations = {
        '1m': 60, '5m': 300, '10m': 600, '30m': 1800,
        '1h': 3600, '2h': 7200, '6h': 21600, '12h': 43200,
        '1d': 86400, '7d': 604800
    }
    
    duration = durations.get(duration_text)
    if not duration:
        bot.reply_to(message, f"❌ Invalid duration. Available: 1m, 5m, 10m, 30m, 1h, 2h, 6h, 12h, 1d, 7d")
        return
    
    # Check if target is admin
    if is_admin_in_group(message) and target_id != message.from_user.id:
        bot.reply_to(message, "❌ Cannot mute an admin.")
        return
    
    # Mute the user
    try:
        until_date = time.time() + duration
        bot.restrict_chat_member(
            message.chat.id,
            target_id,
            can_send_messages=False,
            can_send_media=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            until_date=until_date
        )
        
        db.add_muted_user(
            message.chat.id,
            target_id,
            message.from_user.id,
            duration,
            reason
        )
        
        # Format duration
        if duration >= 86400:
            duration_text = f"{duration // 86400} days"
        elif duration >= 3600:
            duration_text = f"{duration // 3600} hours"
        elif duration >= 60:
            duration_text = f"{duration // 60} minutes"
        else:
            duration_text = f"{duration} seconds"
        
        bot.reply_to(
            message,
            f"🔇 MUTED USER\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"⏳ Duration: {duration_text}\n"
            f"📝 Reason: {reason}\n\n"
            f"🔓 Unmute at: {datetime.fromtimestamp(until_date).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to mute user: {str(e)}")

@bot.message_handler(commands=['unmute'])
def unmute_command(message):
    """Unmute a user in the group"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to unmute users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /unmute")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        bot.restrict_chat_member(
            message.chat.id,
            target_id,
            can_send_messages=True,
            can_send_media=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            until_date=None
        )
        
        db.remove_muted_user(message.chat.id, target_id)
        
        bot.reply_to(
            message,
            f"🔓 UNMUTED USER\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"✅ User can now send messages."
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to unmute user: {str(e)}")

@bot.message_handler(commands=['muted'])
def muted_list_command(message):
    """Show all muted users in the group"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    muted_users = db.get_muted_users(message.chat.id)
    
    if not muted_users:
        bot.reply_to(message, "✅ No muted users in this group.")
        return
    
    content = "🔇 MUTED USERS\n\n"
    for user in muted_users:
        try:
            user_info = bot.get_chat_member(message.chat.id, user[1])
            name = user_info.user.first_name
        except:
            name = f"User {user[1]}"
        
        unmuted_time = datetime.strptime(user[5], '%Y-%m-%d %H:%M:%S')
        remaining = (unmuted_time - datetime.now()).seconds
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        
        content += f"👤 {name}\n"
        content += f"⏳ Remaining: {hours}h {minutes}m\n"
        content += f"📝 Reason: {user[4] or 'No reason'}\n\n"
    
    bot.reply_to(message, content)

# PROMOTE SYSTEM
@bot.message_handler(commands=['promote1', 'promote2', 'promote3', 'promote4', 'promote5'])
def promote_command(message):
    """Promote a user to different levels"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to promote users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, f"❌ Reply to a user with /{message.text.split()[0]}")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    # Get promotion level
    level = int(message.text.replace('promote', ''))
    titles = {1: 'Member', 2: 'Senior Member', 3: 'VIP Member', 4: 'Elite Member', 5: 'Legendary Member'}
    title = titles.get(level, 'Member')
    
    try:
        bot.promote_chat_member(
            message.chat.id,
            target_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=level >= 5
        )
        
        db.add_group_admin(
            message.chat.id,
            target_id,
            message.from_user.id,
            level
        )
        
        bot.reply_to(
            message,
            f"⭐ PROMOTED\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"📊 Level: {title} (Level {level})\n"
            f"🎖️ {title} privileges granted!\n"
            f"💪 Promoted by: {message.from_user.first_name}"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to promote user: {str(e)}")

@bot.message_handler(commands=['demote'])
def demote_command(message):
    """Demote a user"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to demote users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /demote")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        bot.promote_chat_member(
            message.chat.id,
            target_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )
        
        db.remove_group_admin(message.chat.id, target_id)
        
        bot.reply_to(
            message,
            f"⬇️ DEMOTED\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"✅ User has been demoted from admin."
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to demote user: {str(e)}")

@bot.message_handler(commands=['admins'])
def admins_list_command(message):
    """List all admins in the group"""
    admins = db.get_group_admins(message.chat.id)
    
    if not admins:
        bot.reply_to(message, "📋 No promoted admins in this group.")
        return
    
    content = "⭐ GROUP ADMINS\n\n"
    for admin in admins:
        try:
            user_info = bot.get_chat_member(message.chat.id, admin[1])
            name = user_info.user.first_name
        except:
            name = f"User {admin[1]}"
        
        level = admin[3]
        title = admin[4]
        promoted_at = datetime.strptime(admin[5], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        
        content += f"👤 {name}\n"
        content += f"📊 Level: {title} (Level {level})\n"
        content += f"📅 Promoted: {promoted_at}\n\n"
    
    bot.reply_to(message, content)

# WARNING SYSTEM
@bot.message_handler(commands=['warn'])
def warn_command(message):
    """Warn a user"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /warn [reason]")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    reason = message.text.replace('/warn', '').strip()
    if not reason:
        reason = "No reason provided"
    
    warnings_count = db.add_warning(
        message.chat.id,
        target_id,
        message.from_user.id,
        reason
    )
    
    if warnings_count >= 5:
        try:
            bot.ban_chat_member(message.chat.id, target_id)
            db.add_banned_user(
                message.chat.id,
                target_id,
                message.from_user.id,
                f"5 warnings: {reason}"
            )
            bot.reply_to(
                message,
                f"🚫 USER BANNED\n\n"
                f"👤 User: {target_user.first_name}\n"
                f"⚠️ Received 5 warnings\n"
                f"📝 Last Reason: {reason}\n\n"
                f"🔨 Banned from the group."
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Failed to ban user: {str(e)}")
            
    elif warnings_count >= 3:
        try:
            until_date = time.time() + 3600
            bot.restrict_chat_member(
                message.chat.id,
                target_id,
                can_send_messages=False,
                can_send_media=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                until_date=until_date
            )
            
            db.add_muted_user(
                message.chat.id,
                target_id,
                message.from_user.id,
                3600,
                f"3 warnings: {reason}"
            )
            
            bot.reply_to(
                message,
                f"🔇 USER MUTED\n\n"
                f"👤 User: {target_user.first_name}\n"
                f"⚠️ Received 3 warnings\n"
                f"📝 Reason: {reason}\n"
                f"⏳ Muted for 1 hour."
            )
        except Exception as e:
            bot.reply_to(message, f"❌ Failed to mute user: {str(e)}")
    else:
        bot.reply_to(
            message,
            f"⚠️ WARNING\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"📝 Reason: {reason}\n"
            f"📊 Warning {warnings_count}/5\n\n"
            f"💡 3 warnings = 1 hour mute\n"
            f"💡 5 warnings = permanent ban"
        )

@bot.message_handler(commands=['clearwarn'])
def clear_warn_command(message):
    """Clear warnings for a user"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /clearwarn")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    db.clear_warnings(message.chat.id, target_id)
    
    bot.reply_to(
        message,
        f"✅ WARNINGS CLEARED\n\n"
        f"👤 User: {target_user.first_name}\n"
        f"📊 All warnings have been cleared."
    )

# BAN SYSTEM
@bot.message_handler(commands=['ban'])
def ban_command(message):
    """Ban a user"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to ban users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /ban [reason]")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    reason = message.text.replace('/ban', '').strip()
    if not reason:
        reason = "No reason provided"
    
    if is_admin_in_group(message) and target_id != message.from_user.id:
        bot.reply_to(message, "❌ Cannot ban an admin.")
        return
    
    try:
        bot.ban_chat_member(message.chat.id, target_id)
        db.add_banned_user(
            message.chat.id,
            target_id,
            message.from_user.id,
            reason
        )
        
        bot.reply_to(
            message,
            f"🚫 USER BANNED\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"📝 Reason: {reason}\n"
            f"🔨 Banned by: {message.from_user.first_name}"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to ban user: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    """Unban a user"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    if not is_bot_admin_in_group(message.chat.id):
        bot.reply_to(message, "❌ I need to be admin to unban users.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a user with /unban")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        bot.unban_chat_member(message.chat.id, target_id)
        db.remove_banned_user(message.chat.id, target_id)
        
        bot.reply_to(
            message,
            f"✅ USER UNBANNED\n\n"
            f"👤 User: {target_user.first_name}\n"
            f"🔓 User can now join the group again."
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to unban user: {str(e)}")

@bot.message_handler(commands=['banned'])
def banned_list_command(message):
    """List all banned users"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    db.cursor.execute('''
        SELECT * FROM banned_users WHERE group_id = ?
    ''', (message.chat.id,))
    banned_users = db.cursor.fetchall()
    
    if not banned_users:
        bot.reply_to(message, "✅ No banned users in this group.")
        return
    
    content = "🚫 BANNED USERS\n\n"
    for user in banned_users:
        try:
            user_info = bot.get_chat_member(message.chat.id, user[1])
            name = user_info.user.first_name
        except:
            name = f"User {user[1]}"
        
        banned_at = datetime.strptime(user[4], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        content += f"👤 {name}\n"
        content += f"📅 Banned: {banned_at}\n"
        content += f"📝 Reason: {user[3] or 'No reason'}\n\n"
    
    bot.reply_to(message, content)

# GROUP SETTINGS
@bot.message_handler(commands=['settings'])
def settings_command(message):
    """View and manage group settings"""
    if not is_admin_in_group(message) and message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Only admins can use this command.")
        return
    
    welcome = db.get_group_setting(message.chat.id, 'welcome_enabled')
    goodbye = db.get_group_setting(message.chat.id, 'goodbye_enabled')
    antispam = db.get_group_setting(message.chat.id, 'anti_spam')
    antilinks = db.get_group_setting(message.chat.id, 'anti_links')
    antimedia = db.get_group_setting(message.chat.id, 'anti_media')
    
    content = f"""
⚙️ GROUP SETTINGS

━━━━━━━━━━━━━━━━━━

👋 Welcome: {'✅' if welcome else '❌'}
👋 Goodbye: {'✅' if goodbye else '❌'}
🛡️ Anti-Spam: {'✅' if antispam else '❌'}
🔗 Anti-Links: {'✅' if antilinks else '❌'}
🖼️ Anti-Media: {'✅' if antimedia else '❌'}

━━━━━━━━━━━━━━━━━━

Click below to toggle settings.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"👋 Welcome {'ON' if welcome else 'OFF'}", callback_data=f"set_welcome_{message.chat.id}"),
        types.InlineKeyboardButton(f"👋 Goodbye {'ON' if goodbye else 'OFF'}", callback_data=f"set_goodbye_{message.chat.id}"),
        types.InlineKeyboardButton(f"🛡️ Anti-Spam {'ON' if antispam else 'OFF'}", callback_data=f"set_antispam_{message.chat.id}"),
        types.InlineKeyboardButton(f"🔗 Anti-Links {'ON' if antilinks else 'OFF'}", callback_data=f"set_antilinks_{message.chat.id}"),
        types.InlineKeyboardButton(f"🖼️ Anti-Media {'ON' if antimedia else 'OFF'}", callback_data=f"set_antimedia_{message.chat.id}")
    )
    
    bot.reply_to(message, content, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def settings_callback_handler(call):
    """Handle settings toggles"""
    if call.from_user.id != OWNER_ID and not is_admin_in_group(call.message):
        bot.answer_callback_query(call.id, "❌ Only admins can change settings.")
        return
    
    parts = call.data.split('_')
    setting = parts[1]
    group_id = int(parts[2]) if len(parts) > 2 else call.message.chat.id
    
    # Toggle setting
    setting_key = f'{setting}_enabled' if setting not in ['antilinks', 'antimedia'] else setting
    current_value = db.get_group_setting(group_id, setting_key)
    new_value = 0 if current_value else 1
    db.update_group_setting(group_id, setting_key, new_value)
    
    # Update message
    settings_command(call.message)
    bot.answer_callback_query(call.id, f"✅ Setting updated!")

# ANTI-SPAM HANDLER
@bot.message_handler(func=lambda message: True)
def anti_spam_handler(message):
    """Handle anti-spam and anti-link features"""
    if message.chat.type in ['group', 'supergroup']:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Check if user is admin
        if is_admin_in_group(message):
            return
        
        # Check if user is muted
        if db.is_muted(chat_id, user_id):
            try:
                bot.delete_message(chat_id, message.message_id)
                bot.send_message(
                    chat_id,
                    f"🔇 {message.from_user.first_name}, you are muted!",
                    reply_to_message_id=message.message_id
                )
            except:
                pass
            return
        
        # Check anti-links
        if db.get_group_setting(chat_id, 'anti_links'):
            if 'http' in message.text or 't.me' in message.text or 'telegram' in message.text:
                try:
                    bot.delete_message(chat_id, message.message_id)
                    bot.send_message(
                        chat_id,
                        f"🔗 {message.from_user.first_name}, links are not allowed!",
                        reply_to_message_id=message.message_id
                    )
                except:
                    pass
                return
        
        # Check anti-media
        if db.get_group_setting(chat_id, 'anti_media'):
            if message.photo or message.video or message.sticker or message.animation or message.document:
                try:
                    bot.delete_message(chat_id, message.message_id)
                    bot.send_message(
                        chat_id,
                        f"🖼️ {message.from_user.first_name}, media files are not allowed!",
                        reply_to_message_id=message.message_id
                    )
                except:
                    pass
                return

# ========== LEADERBOARD COMMAND ==========
@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
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
    
    bot.reply_to(message, content)

# ========== ACHIEVEMENTS COMMAND ==========
@bot.message_handler(commands=['achievements'])
def achievements_command(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        bot.reply_to(message, "Please use /start first to register.")
        return
    
    achievements = json.loads(user[11]) if user[11] else []
    
    if not achievements:
        content = "🏅 ACHIEVEMENTS\n\nNo achievements unlocked yet.\nKeep playing to unlock achievements!"
    else:
        content = "🏅 ACHIEVEMENTS\n\n" + "\n".join([f"✅ {ach}" for ach in achievements])
    
    bot.reply_to(message, content)

# ========== MYTASK COMMAND ==========
@bot.message_handler(commands=['mytask'])
def mytask_command(message):
    user_id = message.from_user.id
    today = datetime.now().date()
    
    db.cursor.execute('''
        SELECT * FROM daily_tasks 
        WHERE user_id = ? AND task_date = ?
    ''', (user_id, today))
    tasks = db.cursor.fetchone()
    
    if not tasks:
        task_list = [
            "☐ Send 50 messages",
            "☐ Win 1 Quiz",
            "☐ Use Dice",
            "☐ Win 1 Game",
            "☐ Give Appreciation"
        ]
        random.shuffle(task_list)
        tasks_json = json.dumps(task_list[:3])
        
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

# ========== HELP COMMAND ==========
@bot.message_handler(commands=['help'])
def help_command(message):
    content = """
📚 ZYNOX GAMING HELP

━━━━━━━━━━━━━━━━━━

🎮 GAME COMMANDS:
/dice - Roll a dice
/rps - Rock Paper Scissors  
/quiz - Answer a quiz
/guess - Guess the number
/math - Math battle
/slots - Slot machine

━━━━━━━━━━━━━━━━━━

💍 SOCIAL COMMANDS:
/marry - Propose to someone
/divorce - Divorce your partner
/relationship - Check relationship status
/friendship - Check friendship level

━━━━━━━━━━━━━━━━━━

👤 USER COMMANDS:
/start - Start the bot
/profile - View your profile
/claim - Claim daily reward
/roast - Roast someone
/mytask - View daily tasks
/achievements - View achievements
/leaderboard - View top players

━━━━━━━━━━━━━━━━━━

👑 ADMIN COMMANDS:
/mute - Mute a user
/unmute - Unmute a user
/muted - View muted users
/promote1-5 - Promote a user
/demote - Demote a user
/warn - Warn a user
/clearwarn - Clear warnings
/ban - Ban a user
/unban - Unban a user
/banned - View banned users
/settings - Group settings

━━━━━━━━━━━━━━━━━━

🌌 Support: @internationalpanditG
"""
    bot.reply_to(message, content)

# ========== RUN BOT ==========
if __name__ == "__main__":
    print("🤖 ZYNOX GAMING BOT IS RUNNING...")
    print("✅ All systems loaded successfully!")
    print("📊 Bot ready to serve!")
    bot.polling(none_stop=True)
