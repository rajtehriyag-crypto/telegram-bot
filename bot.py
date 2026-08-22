import os
import json
import random
import sqlite3
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from threading import Lock

import telebot
from telebot import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"
OWNER_ID = int(os.getenv('OWNER_ID', '8727799160'))
SUPPORT_CHANNEL = os.getenv('SUPPORT_CHANNEL', 'https://t.me/+CS-ZvjWSB1oxZjZl')
SUPPORT_GROUP = os.getenv('SUPPORT_GROUP', 'https://t.me/+97rox0VQWXNiMzg1')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DAILY_REWARD = 5000
GROUP_CLAIM_REWARD = 10000
ROB_MAX_AMOUNT = 10000
PROTECTION_DURATION = 24
PvP_EXPIRY = 120

# Game rewards
GAME_REWARDS = {
    'blackjack': 50, 'card': 20, 'dice': 25, 'coinflip': 15,
    'rps': 20, 'tictactoe': 40, 'fasttype': 35, 'quiz': 30,
    'emoji': 25, 'guess': 20
}

# XP rewards
XP_REWARDS = {'win': 25, 'play': 10, 'quiz_correct': 20, 'fasttype_win': 30, 'claim': 15}

# Ranks
RANKS = [
    {'name': '🥉 Bronze', 'threshold': 0},
    {'name': '🥈 Silver', 'threshold': 10000},
    {'name': '🥇 Gold', 'threshold': 50000},
    {'name': '💎 Platinum', 'threshold': 150000},
    {'name': '🔷 Diamond', 'threshold': 400000},
    {'name': '👑 Heroic', 'threshold': 1000000},
    {'name': '🔥 Master', 'threshold': 2500000},
    {'name': '🏆 Grandmaster', 'threshold': 5000000},
    {'name': '🌟 Elite', 'threshold': 10000000}
]

LEVEL_XP_REQUIREMENTS = [0] + [i * 100 for i in range(1, 101)]

# Quiz Questions
QUIZ_QUESTIONS = [
    {'question': 'Which planet is known as the Red Planet?', 'options': ['Venus', 'Mars', 'Jupiter', 'Saturn'], 'correct': 1},
    {'question': 'What is the capital of France?', 'options': ['London', 'Berlin', 'Paris', 'Madrid'], 'correct': 2},
    {'question': 'Which element has the chemical symbol "Au"?', 'options': ['Silver', 'Copper', 'Gold', 'Iron'], 'correct': 2},
    {'question': 'What is the largest ocean on Earth?', 'options': ['Atlantic', 'Indian', 'Arctic', 'Pacific'], 'correct': 3},
    {'question': 'Who developed the theory of relativity?', 'options': ['Newton', 'Einstein', 'Hawking', 'Galileo'], 'correct': 1},
    {'question': 'What is the hardest natural substance?', 'options': ['Gold', 'Iron', 'Diamond', 'Platinum'], 'correct': 2},
    {'question': 'Which animal is known as the King of the Jungle?', 'options': ['Tiger', 'Lion', 'Elephant', 'Bear'], 'correct': 1},
    {'question': 'What is the chemical formula for water?', 'options': ['CO2', 'H2O', 'NaCl', 'HCl'], 'correct': 1},
    {'question': 'Which country has the largest population?', 'options': ['India', 'China', 'USA', 'Indonesia'], 'correct': 0},
    {'question': 'What is the tallest mountain in the world?', 'options': ['K2', 'Everest', 'Makalu', 'Lhotse'], 'correct': 1}
]

EMOJI_QUESTIONS = [
    {'emojis': '🚢 ❤️ 💔', 'answer': 'titanic'},
    {'emojis': '👽 🔫 👨', 'answer': 'alien'},
    {'emojis': '👑 🦁 🐗', 'answer': 'lion king'},
    {'emojis': '🤖 ❤️ 👨', 'answer': 'wall-e'},
    {'emojis': '🧙 ⚡ 🎓', 'answer': 'harry potter'},
    {'emojis': '🕷️ 👨 🏙️', 'answer': 'spiderman'},
    {'emojis': '😈 👔 💼', 'answer': 'devil wears prada'},
    {'emojis': '🚀 👨 🌌', 'answer': 'interstellar'},
    {'emojis': '🧜 🧜‍♀️ 🌊', 'answer': 'aquaman'},
    {'emojis': '🐾 🦁 🎶', 'answer': 'lion king'}
]

FAST_TYPE_WORDS = ['gaming', 'python', 'coding', 'programming', 'bot', 'telegram', 'development', 'software', 'engineer', 'gamer', 'streamer', 'controller', 'keyboard', 'monitor', 'processor', 'memory', 'storage']

# ============== DATABASE ==============
class Database:
    def __init__(self):
        self.db_path = 'database/zynox.db'
        os.makedirs('database', exist_ok=True)
        self.lock = Lock()
        self._init_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_tables(self):
        with self._get_connection() as conn:
            c = conn.cursor()
            
            # Users
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                coins INTEGER DEFAULT 0, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
                total_games INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0,
                protection_expiry INTEGER DEFAULT 0, daily_claim_timestamp INTEGER DEFAULT 0,
                first_start_timestamp INTEGER DEFAULT 0, last_activity_timestamp INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0, level_rewards TEXT DEFAULT '[]', current_rank TEXT DEFAULT '🥉 Bronze'
            )''')
            
            # Groups
            c.execute('''CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY, group_name TEXT, group_claimed INTEGER DEFAULT 0, member_count INTEGER DEFAULT 0
            )''')
            
            # Game stats
            c.execute('''CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, game_type TEXT,
                played INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0
            )''')
            
            # Game sessions
            c.execute('''CREATE TABLE IF NOT EXISTS game_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, game_type TEXT,
                player1_id INTEGER, player2_id INTEGER DEFAULT NULL, current_state TEXT, moves TEXT,
                winner_id INTEGER DEFAULT NULL, status TEXT DEFAULT 'active',
                created_at INTEGER, expires_at INTEGER
            )''')
            
            # Quiz sessions
            c.execute('''CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, question_id INTEGER,
                correct_answer INTEGER, status TEXT DEFAULT 'active', created_at INTEGER, expires_at INTEGER
            )''')
            
            # Emoji sessions
            c.execute('''CREATE TABLE IF NOT EXISTS emoji_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, question_id INTEGER,
                correct_answer TEXT, status TEXT DEFAULT 'active', created_at INTEGER, expires_at INTEGER
            )''')
            
            # Fast type sessions
            c.execute('''CREATE TABLE IF NOT EXISTS fasttype_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, word TEXT,
                status TEXT DEFAULT 'active', created_at INTEGER, expires_at INTEGER
            )''')
            
            # Number sessions
            c.execute('''CREATE TABLE IF NOT EXISTS number_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, number INTEGER,
                status TEXT DEFAULT 'active', created_at INTEGER, expires_at INTEGER
            )''')
            
            # Bans
            c.execute('''CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY, reason TEXT, banned_at INTEGER
            )''')
            
            # Settings
            c.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )''')
            
            # Init quiz
            c.execute('SELECT value FROM settings WHERE key = "quiz_initialized"')
            if not c.fetchone():
                c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("quiz_questions", ?)', (json.dumps(QUIZ_QUESTIONS),))
                c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("emoji_questions", ?)', (json.dumps(EMOJI_QUESTIONS),))
                c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("quiz_initialized", "true")')
            
            conn.commit()

    def get_user(self, user_id, username=None, first_name=None):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = c.fetchone()
            
            if not user:
                if not username: username = str(user_id)
                if not first_name: first_name = f'User_{user_id}'
                
                c.execute('INSERT INTO users (user_id, username, first_name, first_start_timestamp, last_activity_timestamp) VALUES (?, ?, ?, ?, ?)',
                         (user_id, username, first_name, int(time.time()), int(time.time())))
                conn.commit()
                
                for game in ['blackjack', 'card', 'dice', 'coinflip', 'rps', 'tictactoe', 'fasttype', 'quiz', 'emoji', 'guess']:
                    c.execute('INSERT INTO game_stats (user_id, game_type) VALUES (?, ?)', (user_id, game))
                conn.commit()
                
                self._notify_owner_new_user(user_id, username, first_name)
                
                c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = c.fetchone()
            
            return {
                'user_id': user[0], 'username': user[1], 'first_name': user[2],
                'coins': user[3], 'xp': user[4], 'level': user[5],
                'total_games': user[6], 'wins': user[7], 'losses': user[8], 'draws': user[9],
                'protection_expiry': user[10], 'daily_claim_timestamp': user[11],
                'first_start_timestamp': user[12], 'last_activity_timestamp': user[13],
                'is_banned': user[14], 'level_rewards': json.loads(user[15]) if user[15] else [],
                'current_rank': user[16] if len(user) > 16 else '🥉 Bronze'
            }

    def _notify_owner_new_user(self, user_id, username, first_name):
        try:
            total = self.get_total_users()
            bot.send_message(OWNER_ID, f"🔔 <b>NEW USER STARTED BOT</b>\n\n👤 Name: {first_name}\n📛 Username: @{username}\n🆔 User ID: <code>{user_id}</code>\n\n📅 Date: {datetime.now().strftime('%d %b %Y')}\n⏰ Time: {datetime.now().strftime('%I:%M %p')}\n\n👥 Total Users: {total:,}")
        except: pass

    def get_total_users(self):
        with self._get_connection() as conn:
            return conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]

    def update_user_coins(self, user_id, amount):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            self._update_rank(user_id)

    def update_user_xp(self, user_id, xp_amount):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET xp = xp + ? WHERE user_id = ?', (xp_amount, user_id))
            conn.commit()
            
            user = self.get_user(user_id)
            level, total_xp = user['level'], user['xp'] + xp_amount
            new_level = level
            while new_level < len(LEVEL_XP_REQUIREMENTS) and total_xp >= LEVEL_XP_REQUIREMENTS[new_level]:
                new_level += 1
            
            if new_level > level:
                rewards = user['level_rewards']
                for i in range(level, new_level):
                    if i not in rewards:
                        rewards.append(i)
                        bonus = i * 1000
                        self.update_user_coins(user_id, bonus)
                        try:
                            bot.send_message(user_id, f"🎉 <b>LEVEL UP!</b>\n\n⭐ Level {i} → {i + 1}\n💰 Reward: +{bonus:,} Coins\n✨ XP: {total_xp:,}")
                        except: pass
                
                c.execute('UPDATE users SET level = ?, level_rewards = ? WHERE user_id = ?', (new_level, json.dumps(rewards), user_id))
                conn.commit()

    def _update_rank(self, user_id):
        coins = self.get_user(user_id)['coins']
        rank = RANKS[0]['name']
        for r in RANKS:
            if coins >= r['threshold']: rank = r['name']
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE users SET current_rank = ? WHERE user_id = ?', (rank, user_id))
            conn.commit()

    def get_user_rank(self, user_id):
        coins = self.get_user(user_id)['coins']
        for r in reversed(RANKS):
            if coins >= r['threshold']: return r['name']
        return RANKS[0]['name']

    def get_global_rank(self, user_id):
        with self._get_connection() as conn:
            return conn.cursor().execute('SELECT COUNT(*) + 1 FROM users WHERE coins > (SELECT coins FROM users WHERE user_id = ?)', (user_id,)).fetchone()[0]

    def get_leaderboard(self, limit=10):
        with self._get_connection() as conn:
            return [{'user_id': r[0], 'username': r[1], 'coins': r[2], 'first_name': r[3]} 
                    for r in conn.cursor().execute('SELECT user_id, username, coins, first_name FROM users ORDER BY coins DESC LIMIT ?', (limit,)).fetchall()]

    def get_user_game_stats(self, user_id):
        with self._get_connection() as conn:
            result = {}
            for r in conn.cursor().execute('SELECT * FROM game_stats WHERE user_id = ?', (user_id,)).fetchall():
                result[r[2]] = {'played': r[3], 'wins': r[4], 'losses': r[5], 'draws': r[6]}
            return result

    def update_game_stats(self, user_id, game_type, result):
        with self._get_connection() as conn:
            c = conn.cursor()
            if result == 'win':
                c.execute('UPDATE game_stats SET played = played + 1, wins = wins + 1 WHERE user_id = ? AND game_type = ?', (user_id, game_type))
                c.execute('UPDATE users SET total_games = total_games + 1, wins = wins + 1 WHERE user_id = ?', (user_id,))
            elif result == 'loss':
                c.execute('UPDATE game_stats SET played = played + 1, losses = losses + 1 WHERE user_id = ? AND game_type = ?', (user_id, game_type))
                c.execute('UPDATE users SET total_games = total_games + 1, losses = losses + 1 WHERE user_id = ?', (user_id,))
            elif result == 'draw':
                c.execute('UPDATE game_stats SET played = played + 1, draws = draws + 1 WHERE user_id = ? AND game_type = ?', (user_id, game_type))
                c.execute('UPDATE users SET total_games = total_games + 1, draws = draws + 1 WHERE user_id = ?', (user_id,))
            conn.commit()

    def get_protection(self, user_id):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT protection_expiry FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if r and r[0] > int(time.time()): return True, r[0] - int(time.time())
            return False, 0

    def set_protection(self, user_id):
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE users SET protection_expiry = ? WHERE user_id = ?', (int(time.time()) + PROTECTION_DURATION * 3600, user_id))
            conn.commit()

    def can_claim_daily(self, user_id):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT daily_claim_timestamp FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if r and r[0] > 0:
                next_claim = r[0] + 24 * 3600
                if next_claim > int(time.time()): return False, next_claim - int(time.time())
            return True, 0

    def claim_daily(self, user_id):
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE users SET daily_claim_timestamp = ? WHERE user_id = ?', (int(time.time()), user_id))
            conn.commit()
        self.update_user_coins(user_id, DAILY_REWARD)
        self.update_user_xp(user_id, XP_REWARDS['claim'])
        return DAILY_REWARD

    def get_group_claim_status(self, group_id):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT group_claimed FROM groups WHERE group_id = ?', (group_id,)).fetchone()
            return r and r[0] == 1

    def claim_group_reward(self, group_id, user_id):
        with self._get_connection() as conn:
            c = conn.cursor()
            if c.execute('SELECT group_claimed FROM groups WHERE group_id = ?', (group_id,)).fetchone():
                return False
            c.execute('INSERT OR REPLACE INTO groups (group_id, group_claimed) VALUES (?, 1)', (group_id,))
            conn.commit()
        self.update_user_coins(user_id, GROUP_CLAIM_REWARD)
        return True

    def save_game_session(self, chat_id, game_type, player1_id, player2_id=None, moves=None, state=None):
        with self._get_connection() as conn:
            c = conn.cursor()
            created = int(time.time())
            c.execute('INSERT INTO game_sessions (chat_id, game_type, player1_id, player2_id, current_state, moves, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (chat_id, game_type, player1_id, player2_id, state or 'waiting', json.dumps(moves or {}), created, created + PvP_EXPIRY))
            conn.commit()
            return c.lastrowid

    def update_game_session(self, session_id, **kwargs):
        with self._get_connection() as conn:
            c = conn.cursor()
            updates, values = [], []
            for k, v in kwargs.items():
                if k == 'moves': v = json.dumps(v)
                updates.append(f"{k} = ?")
                values.append(v)
            if updates:
                values.append(session_id)
                c.execute(f"UPDATE game_sessions SET {', '.join(updates)} WHERE session_id = ?", values)
                conn.commit()

    def get_game_session(self, session_id):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT * FROM game_sessions WHERE session_id = ?', (session_id,)).fetchone()
            if r:
                return {'session_id': r[0], 'chat_id': r[1], 'game_type': r[2], 'player1_id': r[3], 'player2_id': r[4],
                        'current_state': r[5], 'moves': json.loads(r[6]) if r[6] else {}, 'winner_id': r[7],
                        'status': r[8], 'created_at': r[9], 'expires_at': r[10]}
            return None

    def save_quiz_session(self, chat_id, question_id, correct_answer):
        with self._get_connection() as conn:
            c = conn.cursor()
            created = int(time.time())
            c.execute('INSERT INTO quiz_sessions (chat_id, question_id, correct_answer, created_at, expires_at) VALUES (?, ?, ?, ?, ?)',
                     (chat_id, question_id, correct_answer, created, created + 60))
            conn.commit()
            return c.lastrowid

    def update_quiz_session(self, session_id, status):
        with self._get_connection() as conn:
            conn.cursor().execute('UPDATE quiz_sessions SET status = ? WHERE id = ?', (status, session_id))
            conn.commit()

    def get_quiz_session(self, session_id):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT * FROM quiz_sessions WHERE id = ?', (session_id,)).fetchone()
            if r:
                return {'id': r[0], 'chat_id': r[1], 'question_id': r[2], 'correct_answer': r[3], 'status': r[4], 'created_at': r[5], 'expires_at': r[6]}
            return None

    def save_emoji_session(self, chat_id, question_id, correct_answer):
        with self._get_connection() as conn:
            c = conn.cursor()
            created = int(time.time())
            c.execute('INSERT INTO emoji_sessions (chat_id, question_id, correct_answer, created_at, expires_at) VALUES (?, ?, ?, ?, ?)',
                     (chat_id, question_id, correct_answer, created, created + 60))
            conn.commit()
            return c.lastrowid

    def save_fasttype_session(self, chat_id, word):
        with self._get_connection() as conn:
            c = conn.cursor()
            created = int(time.time())
            c.execute('INSERT INTO fasttype_sessions (chat_id, word, created_at, expires_at) VALUES (?, ?, ?, ?)',
                     (chat_id, word, created, created + 30))
            conn.commit()
            return c.lastrowid

    def save_number_session(self, chat_id, number):
        with self._get_connection() as conn:
            c = conn.cursor()
            created = int(time.time())
            c.execute('INSERT INTO number_sessions (chat_id, number, created_at, expires_at) VALUES (?, ?, ?, ?)',
                     (chat_id, number, created, created + 120))
            conn.commit()
            return c.lastrowid

    def get_all_quiz_questions(self):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT value FROM settings WHERE key = "quiz_questions"').fetchone()
            return json.loads(r[0]) if r else QUIZ_QUESTIONS

    def get_all_emoji_questions(self):
        with self._get_connection() as conn:
            r = conn.cursor().execute('SELECT value FROM settings WHERE key = "emoji_questions"').fetchone()
            return json.loads(r[0]) if r else EMOJI_QUESTIONS

    def is_user_banned(self, user_id):
        with self._get_connection() as conn:
            return conn.cursor().execute('SELECT user_id FROM bans WHERE user_id = ?', (user_id,)).fetchone() is not None

    def ban_user(self, user_id, reason=None):
        with self._get_connection() as conn:
            conn.cursor().execute('INSERT OR REPLACE INTO bans (user_id, reason, banned_at) VALUES (?, ?, ?)',
                                 (user_id, reason or 'No reason provided', int(time.time())))
            conn.commit()

    def unban_user(self, user_id):
        with self._get_connection() as conn:
            conn.cursor().execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
            conn.commit()

    def get_all_users(self):
        with self._get_connection() as conn:
            return [{'user_id': r[0], 'username': r[1], 'first_name': r[2], 'coins': r[3], 'level': r[4]}
                    for r in conn.cursor().execute('SELECT user_id, username, first_name, coins, level FROM users').fetchall()]

    def get_all_groups(self):
        with self._get_connection() as conn:
            return [{'group_id': r[0], 'group_name': r[1], 'group_claimed': r[2] == 1, 'member_count': r[3]}
                    for r in conn.cursor().execute('SELECT group_id, group_name, group_claimed, member_count FROM groups').fetchall()]

    def update_group_info(self, group_id, group_name=None, member_count=None):
        with self._get_connection() as conn:
            c = conn.cursor()
            if group_name and member_count:
                c.execute('INSERT OR REPLACE INTO groups (group_id, group_name, member_count) VALUES (?, ?, ?)',
                         (group_id, group_name, member_count))
            elif group_name:
                c.execute('INSERT OR REPLACE INTO groups (group_id, group_name) VALUES (?, ?)', (group_id, group_name))
            elif member_count:
                c.execute('INSERT OR REPLACE INTO groups (group_id, member_count) VALUES (?, ?)', (group_id, member_count))
            conn.commit()

    def get_top_users_by_coins(self, limit=10):
        with self._get_connection() as conn:
            return [{'user_id': r[0], 'username': r[1], 'coins': r[2], 'level': r[3], 'first_name': r[4]}
                    for r in conn.cursor().execute('SELECT user_id, username, coins, level, first_name FROM users ORDER BY coins DESC LIMIT ?', (limit,)).fetchall()]

db = Database()

# ============== GAME MANAGER ==============
game_manager = {}

def create_game(chat_id, game_type, player1_id, player2_id=None):
    session_id = db.save_game_session(chat_id, game_type, player1_id, player2_id)
    game_manager[session_id] = {
        'chat_id': chat_id, 'game_type': game_type, 'player1_id': player1_id,
        'player2_id': player2_id, 'moves': {}, 'state': 'waiting',
        'created_at': time.time(), 'status': 'active'
    }
    return session_id

def get_game(session_id):
    return game_manager.get(session_id)

def update_game(session_id, **kwargs):
    if session_id in game_manager:
        for k, v in kwargs.items():
            if k == 'moves' and isinstance(v, dict):
                game_manager[session_id]['moves'].update(v)
            else:
                game_manager[session_id][k] = v
        db.update_game_session(session_id, **kwargs)

def remove_game(session_id):
    if session_id in game_manager:
        del game_manager[session_id]
        db.update_game_session(session_id, status='completed')

# ============== HELPERS ==============
def format_number(num): return f"{num:,}"
def format_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m" if h > 0 else f"{m}m"

def get_rank_from_coins(coins):
    for r in reversed(RANKS):
        if coins >= r['threshold']: return r['name']
    return RANKS[0]['name']

def is_owner(user_id): return user_id == OWNER_ID
def is_group(chat_type): return chat_type in ['group', 'supergroup']

def check_banned(user_id):
    if db.is_user_banned(user_id):
        raise ValueError("You are banned from using this bot.")

# ============== START - DM ONLY ==============
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if is_group(message.chat.type):
        bot.reply_to(message, "⚠️ Please use /start in private chat with the bot.")
        return
    
    try:
        check_banned(user_id)
        user = db.get_user(user_id, message.from_user.username or '', message.from_user.first_name or 'User')
        
        welcome = f"""🎮 <b>WELCOME TO ZYNOX GAMING</b> 🎮

👤 Welcome, {user['first_name']}!

<b>🌟 Premium Gaming Experience</b>

🎯 <b>GAMES</b>
Play exciting games and earn coins!
Blackjack, Card, Dice, RPS & more!

💰 <b>ECONOMY</b>
Earn coins through games and daily claims
Rob other players (if you dare!)
Protect your hard-earned coins

🏆 <b>RANK & LEVEL</b>
• Rank based on coin balance
• Level up through activity & XP

⚔️ <b>FEATURES</b>
• PvP & PvE game modes
• Global & Group leaderboards

📊 <b>YOUR STATS</b>
💰 Coins: {format_number(user['coins'])}
🏅 Rank: {get_rank_from_coins(user['coins'])}
⭐ Level: {user['level']}
🎮 Games: {user['total_games']}

🎮 Ready to play? Choose an option below!"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🎮 PLAY", callback_data="menu_games"))
        markup.add(types.InlineKeyboardButton("📚 HELP", callback_data="menu_help"),
                   types.InlineKeyboardButton("📢 SUPPORT", callback_data="menu_support"))
        
        bot.send_photo(user_id, "https://i.imgur.com/placeholder.png", caption=welcome, reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== HELP - DM ONLY ==============
@bot.message_handler(commands=['help'])
def handle_help(message):
    if is_group(message.chat.type):
        bot.reply_to(message, "⚠️ Please use /help in private chat with the bot.")
        return
    show_help_menu(message.from_user.id)

def show_help_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎮 GAMES", callback_data="help_games"),
               types.InlineKeyboardButton("💰 ECONOMY", callback_data="help_economy"))
    markup.add(types.InlineKeyboardButton("👤 PROFILE", callback_data="help_profile"))
    markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="menu_main"))
    bot.send_message(user_id, "📚 <b>ZYNOX HELP MENU</b>\n\nSelect a category:", reply_markup=markup)

def show_games_help(user_id):
    text = """🎮 <b>GAME COMMANDS</b>

🃏 /blackjack - Play Blackjack vs Bot (50 coins)
🃏 /card - Higher Card Challenge (20 coins)
🎲 /dice - Dice Duel (25 coins)
🪙 /coinflip - Coin Flip (15 coins)
✂️ /rps - Rock Paper Scissors (20 coins)
⭕ /tictactoe - Tic Tac Toe (40 coins)
⚡ /fasttype - Fast Type Challenge (35 coins)
❓ /quiz - Quiz Challenge (30 coins)
😀 /emoji - Emoji Guess (25 coins)
🔢 /guess - Number Guess (20 coins)

<b>📌 PvP:</b> Reply to user with /game"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="help_menu"))
    bot.send_message(user_id, text, reply_markup=markup)

def show_economy_help(user_id):
    text = """💰 <b>ECONOMY COMMANDS</b>

<b>/bal</b> - Check balance
<b>/claim</b> - Daily or group claim
<b>/rob</b> - Rob other users (max 10,000)
<b>/protect</b> - 24-hour protection
<b>/leaderboard</b> - Global ranking
<b>/grouprank</b> - Group ranking"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="help_menu"))
    bot.send_message(user_id, text, reply_markup=markup)

def show_profile_help(user_id):
    text = """👤 <b>PROFILE COMMANDS</b>

<b>/profile</b> - View your gaming profile
<b>/stats</b> - Detailed game statistics"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="help_menu"))
    bot.send_message(user_id, text, reply_markup=markup)

# ============== PROFILE ==============
@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.from_user.id
    try:
        check_banned(user_id)
        user = db.get_user(user_id, message.from_user.username or '', message.from_user.first_name or 'User')
        stats = db.get_user_game_stats(user_id)
        
        total_played = sum(s.get('played', 0) for s in stats.values())
        total_wins = sum(s.get('wins', 0) for s in stats.values())
        total_losses = sum(s.get('losses', 0) for s in stats.values())
        win_rate = (total_wins / total_played * 100) if total_played > 0 else 0
        
        rank = get_rank_from_coins(user['coins'])
        global_rank = db.get_global_rank(user_id)
        protection = db.get_protection(user_id)
        
        text = f"""<b>{rank} PROFILE</b>

👤 Name: {user['first_name']}
📛 Username: @{user['username'] or 'N/A'}

━━━━━━━━━━━━━━━━━
💰 Coins: {format_number(user['coins'])}
🏅 Rank: {rank}
⭐ Level: {user['level']}
✨ XP: {format_number(user['xp'])}
━━━━━━━━━━━━━━━━━

📊 GAME STATISTICS
🎮 Games: {total_played}
✅ Wins: {total_wins}
❌ Losses: {total_losses}
📈 Win Rate: {win_rate:.1f}%

🌍 Global Rank: #{global_rank}"""
        
        if protection[0]:
            text += f"\n🛡️ Protected: ✅ ({format_time(protection[1])} remaining)"
        else:
            text += "\n🛡️ Protected: ❌"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 STATS", callback_data=f"view_stats_{user_id}"),
                   types.InlineKeyboardButton("🎮 PLAY", callback_data="menu_games"))
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== STATS ==============
@bot.message_handler(commands=['stats'])
def handle_stats(message):
    user_id = message.from_user.id
    try:
        check_banned(user_id)
        user = db.get_user(user_id, message.from_user.username or '', message.from_user.first_name or 'User')
        stats = db.get_user_game_stats(user_id)
        
        total_played = sum(s.get('played', 0) for s in stats.values())
        total_wins = sum(s.get('wins', 0) for s in stats.values())
        total_losses = sum(s.get('losses', 0) for s in stats.values())
        win_rate = (total_wins / total_played * 100) if total_played > 0 else 0
        
        text = f"""📊 <b>GAME STATISTICS</b>

👤 Player: {user['first_name']}

━━━━━━━━━━━━━━━━━
🎮 Total Games: {total_played}
✅ Wins: {total_wins}
❌ Losses: {total_losses}
📈 Win Rate: {win_rate:.1f}%
━━━━━━━━━━━━━━━━━

<b>📋 PER-GAME STATS</b>"""
        
        games = {'blackjack': '🃏 Blackjack', 'card': '🃏 Card', 'dice': '🎲 Dice',
                'coinflip': '🪙 Coin Flip', 'rps': '✂️ RPS', 'tictactoe': '⭕ Tic Tac Toe',
                'fasttype': '⚡ Fast Type', 'quiz': '❓ Quiz', 'emoji': '😀 Emoji', 'guess': '🔢 Guess'}
        
        for key, name in games.items():
            s = stats.get(key, {})
            played = s.get('played', 0)
            wins = s.get('wins', 0)
            if played > 0:
                text += f"\n{name}: {played} played, {wins} wins ({wins/played*100:.0f}%)"
            else:
                text += f"\n{name}: Not played yet"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 PROFILE", callback_data=f"view_profile_{user_id}"),
                   types.InlineKeyboardButton("🎮 PLAY", callback_data="menu_games"))
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== BALANCE ==============
@bot.message_handler(commands=['bal'])
def handle_balance(message):
    user_id = message.from_user.id
    target_id = user_id
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    
    try:
        check_banned(user_id)
        user = db.get_user(target_id)
        rank = get_rank_from_coins(user['coins'])
        protection = db.get_protection(target_id)
        global_rank = db.get_global_rank(target_id)
        
        text = f"""💰 <b>BALANCE</b>

👤 User: {user['first_name']} (@{user['username'] or 'N/A'})
💵 Coins: {format_number(user['coins'])}
🏅 Rank: {rank}
⭐ Level: {user['level']}
🌍 Global Rank: #{global_rank}"""
        
        if protection[0]:
            text += f"\n🛡️ Protected: ✅ ({format_time(protection[1])} remaining)"
        else:
            text += "\n🛡️ Protected: ❌"
        
        bot.reply_to(message, text)
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== LEADERBOARD ==============
@bot.message_handler(commands=['leaderboard'])
def handle_leaderboard(message):
    user_id = message.from_user.id
    try:
        check_banned(user_id)
        top = db.get_top_users_by_coins(10)
        user = db.get_user(user_id)
        
        text = "🌍 <b>GLOBAL LEADERBOARD</b>\n\n"
        medals = ['🥇', '🥈', '🥉']
        for i, u in enumerate(top):
            medal = medals[i] if i < 3 else f"#{i+1}"
            text += f"{medal} @{u['username'] or 'User'} — {format_number(u['coins'])} coins\n"
        
        text += f"\n📊 Your Rank: #{db.get_global_rank(user_id)} (Coins: {format_number(user['coins'])})"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎮 PLAY", callback_data="menu_games"))
        bot.reply_to(message, text, reply_markup=markup)
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== GROUP RANK ==============
@bot.message_handler(commands=['grouprank'])
def handle_group_rank(message):
    if not is_group(message.chat.type):
        bot.reply_to(message, "⚠️ This command can only be used in groups.")
        return
    bot.reply_to(message, "📊 Group ranking feature coming soon!")

# ============== CLAIM ==============
@bot.message_handler(commands=['claim'])
def handle_claim(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        check_banned(user_id)
        
        if is_group(message.chat.type):
            if db.get_group_claim_status(chat_id):
                bot.reply_to(message, "❌ <b>GROUP REWARD ALREADY CLAIMED</b>\n\nThis group has already received its one-time 10,000 coin reward.", parse_mode='HTML')
                return
            
            try:
                chat = bot.get_chat(chat_id)
                member_count = chat.get_member_count() if hasattr(chat, 'get_member_count') else 0
                if member_count < 500:
                    bot.reply_to(message, f"❌ <b>GROUP REWARD LOCKED</b>\n\nThis group has {member_count} members.\nNeed at least 500 members.\n\n👥 Members: {member_count}/500", parse_mode='HTML')
                    return
            except: pass
            
            if db.claim_group_reward(chat_id, user_id):
                try:
                    chat = bot.get_chat(chat_id)
                    db.update_group_info(chat_id, chat.title, chat.get_member_count() if hasattr(chat, 'get_member_count') else 0)
                except: pass
                
                bot.reply_to(message, f"🎉 <b>GROUP REWARD CLAIMED!</b>\n\n👥 Group: {message.chat.title or 'This Group'}\n👤 Claimed By: @{message.from_user.username or 'N/A'}\n\n💰 +{format_number(GROUP_CLAIM_REWARD)} Coins", parse_mode='HTML')
            else:
                bot.reply_to(message, "❌ Failed to claim group reward.")
        else:
            can_claim, remaining = db.can_claim_daily(user_id)
            
            if not can_claim:
                bot.reply_to(message, f"⏳ <b>DAILY CLAIM COOLDOWN</b>\n\nNext claim available in: {format_time(remaining)}", parse_mode='HTML')
                return
            
            reward = db.claim_daily(user_id)
            user = db.get_user(user_id)
            bot.reply_to(message, f"🎉 <b>DAILY REWARD CLAIMED!</b>\n\n💰 +{format_number(reward)} Coins\n⭐ +{XP_REWARDS['claim']} XP\n\n📊 New Balance: {format_number(user['coins'])} coins\n🏅 Rank: {get_rank_from_coins(user['coins'])}\n⭐ Level: {user['level']}", parse_mode='HTML')
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== PROTECT ==============
@bot.message_handler(commands=['protect'])
def handle_protect(message):
    user_id = message.from_user.id
    try:
        check_banned(user_id)
        protected, remaining = db.get_protection(user_id)
        
        if protected:
            bot.reply_to(message, f"🛡️ <b>ALREADY PROTECTED</b>\n\n⏳ Remaining: {format_time(remaining)}\n\nYour coins are currently safe.", parse_mode='HTML')
        else:
            db.set_protection(user_id)
            bot.reply_to(message, "🛡️ <b>PROTECTION ACTIVATED</b>\n\n⏰ Duration: 24 Hours\n\nYour coins are now protected from robbery.", parse_mode='HTML')
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== ROB ==============
@bot.message_handler(commands=['rob'])
def handle_rob(message):
    user_id = message.from_user.id
    
    if not is_group(message.chat.type):
        bot.reply_to(message, "⚠️ Rob command can only be used in groups.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Reply to the user you want to rob with /rob")
        return
    
    target_id = message.reply_to_message.from_user.id
    
    if target_id == user_id:
        bot.reply_to(message, "❌ You cannot rob yourself!")
        return
    
    if target_id == OWNER_ID:
        bot.reply_to(message, "❌ You cannot rob the bot owner!")
        return
    
    try:
        check_banned(user_id)
        
        protected, remaining = db.get_protection(target_id)
        if protected:
            bot.reply_to(message, f"❌ <b>ROB FAILED</b>\n\n🛡️ @{message.reply_to_message.from_user.username or 'User'} is protected.\n\n⏳ Protection remaining: {format_time(remaining)}", parse_mode='HTML')
            return
        
        target = db.get_user(target_id)
        if target['coins'] <= 0:
            bot.reply_to(message, "❌ This user has no coins to rob!")
            return
        
        rob_amount = random.randint(100, min(ROB_MAX_AMOUNT, target['coins']))
        
        db.update_user_coins(target_id, -rob_amount)
        db.update_user_coins(user_id, rob_amount)
        
        robber = db.get_user(user_id)
        bot.reply_to(message, f"✅ <b>ROB SUCCESSFUL!</b>\n\n👤 Robber: @{message.from_user.username or 'N/A'}\n🎯 Target: @{message.reply_to_message.from_user.username or 'N/A'}\n\n💰 Stolen: {format_number(rob_amount)} coins\n\n📊 Robber's Balance: {format_number(robber['coins'])} coins\n📊 Target's Balance: {format_number(target['coins'] - rob_amount)} coins", parse_mode='HTML')
    except Exception as e:
        bot.send_message(user_id, f"❌ Error: {e}")

# ============== GAMES ==============

# Blackjack
@bot.message_handler(commands=['blackjack'])
def handle_blackjack(message):
    user_id = message.from_user.id
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id == user_id:
            bot.reply_to(message, "❌ You cannot play against yourself!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"bj_accept_{user_id}_{target_id}"),
                   types.InlineKeyboardButton("❌ Decline", callback_data=f"bj_decline_{user_id}_{target_id}"))
        bot.reply_to(message, f"🎯 <b>BLACKJACK CHALLENGE</b>\n\n👤 @{message.from_user.username or 'User'} challenged @{message.reply_to_message.from_user.username or 'User'}!\n\n💰 Winner: {GAME_REWARDS['blackjack']} coins", reply_markup=markup)
    else:
        # Bot mode
        suits = ['♠', '♥', '♦', '♣']
        values = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
        
        def get_card(): return random.choice(values) + random.choice(suits)
        def card_value(c):
            v = c[:-1]
            if v.isdigit(): return int(v)
            if v in ['J','Q','K']: return 10
            return 11
        def hand_total(hand):
            total = sum(card_value(c) for c in hand)
            aces = sum(1 for c in hand if c.startswith('A'))
            while total > 21 and aces > 0:
                total -= 10
                aces -= 1
            return total
        
        player_cards = [get_card(), get_card()]
        bot_cards = [get_card(), get_card()]
        
        session_id = create_game(message.chat.id, 'blackjack', user_id)
        update_game(session_id, state='playing', moves={'player_cards': player_cards, 'bot_cards': bot_cards, 'player_total': hand_total(player_cards), 'bot_total': hand_total(bot_cards)})
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("➕ HIT", callback_data=f"bj_hit_{session_id}"),
                   types.InlineKeyboardButton("✋ STAND", callback_data=f"bj_stand_{session_id}"))
        
        bot.reply_to(message, f"🃏 <b>BLACKJACK</b>\n\n👤 Your Hand: {' '.join(player_cards)} = {hand_total(player_cards)}\n🤖 Bot Hand: {bot_cards[0]} ?\n\nChoose your action:", reply_markup=markup)

# Card
@bot.message_handler(commands=['card'])
def handle_card(message):
    user_id = message.from_user.id
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id == user_id:
            bot.reply_to(message, "❌ You cannot play against yourself!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"card_accept_{user_id}_{target_id}"),
                   types.InlineKeyboardButton("❌ Decline", callback_data=f"card_decline_{user_id}_{target_id}"))
        bot.reply_to(message, f"🎯 <b>CARD CHALLENGE</b>\n\n👤 @{message.from_user.username or 'User'} challenged @{message.reply_to_message.from_user.username or 'User'}!\n\n💰 Winner: {GAME_REWARDS['card']} coins", reply_markup=markup)
    else:
        suits = ['♠', '♥', '♦', '♣']
        values = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
        def get_card(): return random.choice(values) + random.choice(suits)
        def card_value(c):
            v = c[:-1]
            if v.isdigit(): return int(v)
            if v in ['J','Q','K']: return 10
            return 11
        
        player = get_card()
        bot_card = get_card()
        p_val, b_val = card_value(player), card_value(bot_card)
        
        if p_val > b_val:
            db.update_user_coins(user_id, GAME_REWARDS['card'])
            db.update_user_xp(user_id, XP_REWARDS['win'])
            db.update_game_stats(user_id, 'card', 'win')
            result = f"🏆 <b>YOU WIN!</b> 🎉\n💰 +{GAME_REWARDS['card']} coins"
        elif p_val < b_val:
            db.update_game_stats(user_id, 'card', 'loss')
            result = "❌ <b>YOU LOSE!</b>\nBetter luck next time!"
        else:
            db.update_game_stats(user_id, 'card', 'draw')
            result = "🤝 <b>IT'S A TIE!</b>"
        
        bot.reply_to(message, f"🃏 <b>HIGHER CARD</b>\n\n👤 Your Card: {player} = {p_val}\n🤖 Bot Card: {bot_card} = {b_val}\n\n{result}")

# Dice
@bot.message_handler(commands=['dice'])
def handle_dice(message):
    user_id = message.from_user.id
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id == user_id:
            bot.reply_to(message, "❌ You cannot play against yourself!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"dice_accept_{user_id}_{target_id}"),
                   types.InlineKeyboardButton("❌ Decline", callback_data=f"dice_decline_{user_id}_{target_id}"))
        bot.reply_to(message, f"🎯 <b>DICE CHALLENGE</b>\n\n👤 @{message.from_user.username or 'User'} challenged @{message.reply_to_message.from_user.username or 'User'}!\n\n💰 Winner: {GAME_REWARDS['dice']} coins", reply_markup=markup)
    else:
        player = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        if player > bot_roll:
            db.update_user_coins(user_id, GAME_REWARDS['dice'])
            db.update_user_xp(user_id, XP_REWARDS['win'])
            db.update_game_stats(user_id, 'dice', 'win')
            result = f"🏆 <b>YOU WIN!</b> 🎉\n💰 +{GAME_REWARDS['dice']} coins"
        elif player < bot_roll:
            db.update_game_stats(user_id, 'dice', 'loss')
            result = "❌ <b>YOU LOSE!</b>\nBetter luck next time!"
        else:
            db.update_game_stats(user_id, 'dice', 'draw')
            result = "🤝 <b>IT'S A TIE!</b>"
        
        bot.reply_to(message, f"🎲 <b>DICE DUEL</b>\n\n👤 Your Roll: 🎲 {player}\n🤖 Bot Roll: 🎲 {bot_roll}\n\n{result}")

# Coin Flip
@bot.message_handler(commands=['coinflip'])
def handle_coinflip(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🪙 HEADS", callback_data=f"cf_heads_{user_id}"),
               types.InlineKeyboardButton("🪙 TAILS", callback_data=f"cf_tails_{user_id}"))
    bot.reply_to(message, "🪙 <b>COIN FLIP</b>\n\nChoose heads or tails:", reply_markup=markup)

# RPS
@bot.message_handler(commands=['rps'])
def handle_rps(message):
    user_id = message.from_user.id
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        if target_id == user_id:
            bot.reply_to(message, "❌ You cannot play against yourself!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"rps_accept_{user_id}_{target_id}"),
                   types.InlineKeyboardButton("❌ Decline", callback_data=f"rps_decline_{user_id}_{target_id}"))
        bot.reply_to(message, f"🎯 <b>RPS CHALLENGE</b>\n\n👤 @{message.from_user.username or 'User'} challenged @{message.reply_to_message.from_user.username or 'User'}!\n\n💰 Winner: {GAME_REWARDS['rps']} coins", reply_markup=markup)
    else:
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(types.InlineKeyboardButton("🪨 ROCK", callback_data=f"rps_bot_rock_{user_id}"),
                   types.InlineKeyboardButton("📄 PAPER", callback_data=f"rps_bot_paper_{user_id}"),
                   types.InlineKeyboardButton("✂️ SCISSORS", callback_data=f"rps_bot_scissors_{user_id}"))
        bot.reply_to(message, "✂️ <b>ROCK PAPER SCISSORS</b>\n\nChoose your move:", reply_markup=markup)

# Tic Tac Toe
@bot.message_handler(commands=['tictactoe'])
def handle_tictactoe(message):
    user_id = message.from_user.id
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Reply to the user you want to challenge with /tictactoe")
        return
    
    target_id = message.reply_to_message.from_user.id
    if target_id == user_id:
        bot.reply_to(message, "❌ You cannot play against yourself!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"ttt_accept_{user_id}_{target_id}"),
               types.InlineKeyboardButton("❌ Decline", callback_data=f"ttt_decline_{user_id}_{target_id}"))
    bot.reply_to(message, f"🎯 <b>TIC TAC TOE CHALLENGE</b>\n\n👤 @{message.from_user.username or 'User'} challenged @{message.reply_to_message.from_user.username or 'User'}!\n\n💰 Winner: {GAME_REWARDS['tictactoe']} coins", reply_markup=markup)

# Fast Type
@bot.message_handler(commands=['fasttype'])
def handle_fasttype(message):
    word = random.choice(FAST_TYPE_WORDS)
    db.save_fasttype_session(message.chat.id, word)
    bot.reply_to(message, f"⚡ <b>FAST TYPE CHALLENGE</b>\n\nType this word first to win:\n\n📝 <code>{word}</code>\n\n💰 Winner: {GAME_REWARDS['fasttype']} coins", parse_mode='HTML')

# Quiz
@bot.message_handler(commands=['quiz'])
def handle_quiz(message):
    questions = db.get_all_quiz_questions()
    if not questions: questions = QUIZ_QUESTIONS
    
    q = random.choice(questions)
    q_id = questions.index(q)
    session_id = db.save_quiz_session(message.chat.id, q_id, q['correct'])
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for i, opt in enumerate(q['options']):
        markup.add(types.InlineKeyboardButton(opt, callback_data=f"quiz_answer_{session_id}_{i}"))
    
    bot.reply_to(message, f"❓ <b>QUIZ CHALLENGE</b>\n\n{q['question']}\n\n💰 Winner: {GAME_REWARDS['quiz']} coins", reply_markup=markup)

# Emoji Guess
@bot.message_handler(commands=['emoji'])
def handle_emoji(message):
    questions = db.get_all_emoji_questions()
    if not questions: questions = EMOJI_QUESTIONS
    
    q = random.choice(questions)
    q_id = questions.index(q)
    db.save_emoji_session(message.chat.id, q_id, q['answer'])
    
    bot.reply_to(message, f"😀 <b>EMOJI GUESS</b>\n\n{q['emojis']}\n\nGuess what this represents!\n\n💰 Winner: {GAME_REWARDS['emoji']} coins")

# Number Guess
@bot.message_handler(commands=['guess'])
def handle_guess(message):
    number = random.randint(1, 100)
    db.save_number_session(message.chat.id, number)
    bot.reply_to(message, f"🔢 <b>NUMBER GUESS</b>\n\nI'm thinking of a number between 1 and 100.\n\n💰 Winner: {GAME_REWARDS['guess']} coins")

# ============== CALLBACKS ==============
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        check_banned(user_id)
        
        # Menu
        if data == "menu_games":
            markup = types.InlineKeyboardMarkup(row_width=2)
            games = [("🃏 Blackjack", "game_blackjack"), ("🃏 Card", "game_card"), ("🎲 Dice", "game_dice"),
                    ("🪙 Coin Flip", "game_coinflip"), ("✂️ RPS", "game_rps"), ("⭕ Tic Tac Toe", "game_tictactoe"),
                    ("⚡ Fast Type", "game_fasttype"), ("❓ Quiz", "game_quiz"), ("😀 Emoji", "game_emoji"),
                    ("🔢 Guess", "game_guess")]
            for name, cb in games:
                markup.add(types.InlineKeyboardButton(name, callback_data=cb))
            markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="menu_main"))
            bot.edit_message_text("🎮 <b>ZYNOX GAMES</b>\n\nSelect a game:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        elif data == "menu_help":
            show_help_menu(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data == "menu_support":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("📢 Channel", url=SUPPORT_CHANNEL),
                       types.InlineKeyboardButton("👥 Group", url=SUPPORT_GROUP))
            markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data="menu_main"))
            bot.edit_message_text(f"📢 <b>ZYNOX SUPPORT</b>\n\nJoin our communities:\n\n📢 Channel: {SUPPORT_CHANNEL}\n👥 Group: {SUPPORT_GROUP}", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        elif data == "menu_main":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            handle_start(call.message)
        
        elif data == "help_menu":
            show_help_menu(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data == "help_games":
            show_games_help(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data == "help_economy":
            show_economy_help(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data == "help_profile":
            show_profile_help(user_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Game shortcuts
        elif data.startswith("game_"):
            game = data.split("_")[1]
            commands = {'blackjack':'/blackjack','card':'/card','dice':'/dice','coinflip':'/coinflip','rps':'/rps',
                       'tictactoe':'/tictactoe','fasttype':'/fasttype','quiz':'/quiz','emoji':'/emoji','guess':'/guess'}
            if game in commands:
                dummy = call.message
                dummy.text = commands[game]
                dummy.from_user = call.from_user
                dummy.chat = call.message.chat
                if game == 'blackjack': handle_blackjack(dummy)
                elif game == 'card': handle_card(dummy)
                elif game == 'dice': handle_dice(dummy)
                elif game == 'coinflip': handle_coinflip(dummy)
                elif game == 'rps': handle_rps(dummy)
                elif game == 'tictactoe': handle_tictactoe(dummy)
                elif game == 'fasttype': handle_fasttype(dummy)
                elif game == 'quiz': handle_quiz(dummy)
                elif game == 'emoji': handle_emoji(dummy)
                elif game == 'guess': handle_guess(dummy)
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Coin Flip
        elif data.startswith("cf_"):
            _, choice, player_id = data.split("_")
            if int(player_id) != user_id:
                bot.answer_callback_query(call.id, "❌ This isn't your game!", show_alert=True)
                return
            
            result = random.choice(['heads', 'tails'])
            if choice == result:
                db.update_user_coins(user_id, GAME_REWARDS['coinflip'])
                db.update_user_xp(user_id, XP_REWARDS['win'])
                db.update_game_stats(user_id, 'coinflip', 'win')
                text = f"🪙 <b>COIN FLIP</b>\n\nYou chose: {choice.upper()}\nResult: {result.upper()}\n\n🏆 <b>YOU WIN!</b> 🎉\n💰 +{GAME_REWARDS['coinflip']} coins"
            else:
                db.update_game_stats(user_id, 'coinflip', 'loss')
                text = f"🪙 <b>COIN FLIP</b>\n\nYou chose: {choice.upper()}\nResult: {result.upper()}\n\n❌ <b>YOU LOSE!</b>"
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        
        # RPS Bot
        elif data.startswith("rps_bot_"):
            _, _, move, player_id = data.split("_")
            if int(player_id) != user_id:
                bot.answer_callback_query(call.id, "❌ This isn't your game!", show_alert=True)
                return
            
            bot_move = random.choice(['rock', 'paper', 'scissors'])
            moves = {'rock': '🪨 Rock', 'paper': '📄 Paper', 'scissors': '✂️ Scissors'}
            
            if move == bot_move:
                db.update_game_stats(user_id, 'rps', 'draw')
                text = f"✂️ <b>RPS</b>\n\n👤 You: {moves[move]}\n🤖 Bot: {moves[bot_move]}\n\n🤝 <b>IT'S A TIE!</b>"
            elif (move == 'rock' and bot_move == 'scissors') or (move == 'paper' and bot_move == 'rock') or (move == 'scissors' and bot_move == 'paper'):
                db.update_user_coins(user_id, GAME_REWARDS['rps'])
                db.update_user_xp(user_id, XP_REWARDS['win'])
                db.update_game_stats(user_id, 'rps', 'win')
                text = f"✂️ <b>RPS</b>\n\n👤 You: {moves[move]}\n🤖 Bot: {moves[bot_move]}\n\n🏆 <b>YOU WIN!</b> 🎉\n💰 +{GAME_REWARDS['rps']} coins"
            else:
                db.update_game_stats(user_id, 'rps', 'loss')
                text = f"✂️ <b>RPS</b>\n\n👤 You: {moves[move]}\n🤖 Bot: {moves[bot_move]}\n\n❌ <b>YOU LOSE!</b>"
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        
        # Quiz
        elif data.startswith("quiz_answer_"):
            _, _, session_id, selected = data.split("_")
            session_id = int(session_id)
            selected = int(selected)
            
            session = db.get_quiz_session(session_id)
            if not session or session['status'] != 'active':
                bot.answer_callback_query(call.id, "❌ This quiz has expired!", show_alert=True)
                return
            
            if session['expires_at'] < int(time.time()):
                bot.answer_callback_query(call.id, "❌ This quiz has expired!", show_alert=True)
                db.update_quiz_session(session_id, 'expired')
                return
            
            correct = session['correct_answer']
            questions = db.get_all_quiz_questions()
            q = questions[session['question_id']] if session['question_id'] < len(questions) else None
            
            if selected == correct:
                db.update_user_coins(user_id, GAME_REWARDS['quiz'])
                db.update_user_xp(user_id, XP_REWARDS['quiz_correct'])
                db.update_game_stats(user_id, 'quiz', 'win')
                text = f"❓ <b>QUIZ</b>\n\n✅ <b>CORRECT!</b>\n\n🏆 Winner: @{call.from_user.username or 'User'}\n💰 +{GAME_REWARDS['quiz']} coins\n⭐ +{XP_REWARDS['quiz_correct']} XP"
                if q: text += f"\n\nAnswer: {q['options'][correct]}"
            else:
                db.update_game_stats(user_id, 'quiz', 'loss')
                text = f"❓ <b>QUIZ</b>\n\n❌ <b>WRONG!</b>\n\nCorrect answer: {q['options'][correct] if q else 'N/A'}"
            
            db.update_quiz_session(session_id, 'completed')
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        
        # RPS Accept/Decline
        elif data.startswith("rps_accept_"):
            _, _, p1, p2 = data.split("_")
            if int(p2) != user_id:
                bot.answer_callback_query(call.id, "❌ This challenge isn't for you!", show_alert=True)
                return
            
            p1_name = db.get_user(int(p1))['username'] or 'Player1'
            p2_name = db.get_user(int(p2))['username'] or 'Player2'
            
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(types.InlineKeyboardButton("🪨 ROCK", callback_data=f"rps_pvp_move_{p1}_rock"),
                       types.InlineKeyboardButton("📄 PAPER", callback_data=f"rps_pvp_move_{p1}_paper"),
                       types.InlineKeyboardButton("✂️ SCISSORS", callback_data=f"rps_pvp_move_{p1}_scissors"))
            
            bot.edit_message_text(f"✂️ <b>RPS BATTLE</b>\n\n👤 @{p1_name}\n🔴 ❌ Not Played\n\n👤 @{p2_name}\n🔴 ❌ Not Played\n\n<b>@{p1_name}'s turn</b>", 
                                 call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        elif data.startswith("rps_decline_"):
            _, _, p1, p2 = data.split("_")
            if int(p2) != user_id:
                bot.answer_callback_query(call.id, "❌ This challenge isn't for you!", show_alert=True)
                return
            bot.edit_message_text("❌ Challenge declined.", call.message.chat.id, call.message.message_id)
        
        # RPS PvP Move
        elif data.startswith("rps_pvp_move_"):
            _, _, _, player, move = data.split("_")
            player = int(player)
            
            if player != user_id:
                bot.answer_callback_query(call.id, "❌ Not your turn!", show_alert=True)
                return
            
            # Get game session
            session_id = None
            for sid, game in game_manager.items():
                if game['chat_id'] == call.message.chat.id and game['game_type'] == 'rps' and game['status'] == 'active':
                    if player in [game['player1_id'], game['player2_id']]:
                        session_id = sid
                        break
            
            if not session_id:
                bot.answer_callback_query(call.id, "❌ Game not found!", show_alert=True)
                return
            
            game = get_game(session_id)
            p1 = game['player1_id']
            p2 = game['player2_id']
            
            # Record move
            moves = game.get('moves', {})
            moves[str(player)] = move
            update_game(session_id, moves=moves)
            
            p1_name = db.get_user(p1)['username'] or 'Player1'
            p2_name = db.get_user(p2)['username'] or 'Player2'
            
            # Check if both have moved
            if str(p1) in moves and str(p2) in moves:
                # Reveal results
                p1_move = moves[str(p1)]
                p2_move = moves[str(p2)]
                move_names = {'rock': '🪨 Rock', 'paper': '📄 Paper', 'scissors': '✂️ Scissors'}
                
                # Determine winner
                if p1_move == p2_move:
                    winner_text = "🤝 <b>IT'S A TIE!</b>"
                    winner_id = None
                elif (p1_move == 'rock' and p2_move == 'scissors') or (p1_move == 'paper' and p2_move == 'rock') or (p1_move == 'scissors' and p2_move == 'paper'):
                    winner_text = f"🏆 <b>WINNER: @{p1_name}</b>"
                    winner_id = p1
                else:
                    winner_text = f"🏆 <b>WINNER: @{p2_name}</b>"
                    winner_id = p2
                
                if winner_id:
                    db.update_user_coins(winner_id, GAME_REWARDS['rps'])
                    db.update_user_xp(winner_id, XP_REWARDS['win'])
                    db.update_game_stats(winner_id, 'rps', 'win')
                    loser_id = p2 if winner_id == p1 else p1
                    db.update_game_stats(loser_id, 'rps', 'loss')
                    reward_text = f"\n💰 +{GAME_REWARDS['rps']} coins\n⭐ +{XP_REWARDS['win']} XP"
                else:
                    db.update_game_stats(p1, 'rps', 'draw')
                    db.update_game_stats(p2, 'rps', 'draw')
                    reward_text = ""
                
                bot.edit_message_text(f"✂️ <b>RPS RESULT</b>\n\n👤 @{p1_name}\n{move_names[p1_move]}\n\n👤 @{p2_name}\n{move_names[p2_move]}\n\n{winner_text}{reward_text}", 
                                     call.message.chat.id, call.message.message_id)
                remove_game(session_id)
            else:
                # Update status
                p1_done = str(p1) in moves
                p2_done = str(p2) in moves
                
                p1_status = "🟢 ✅ Played" if p1_done else "🔴 ❌ Not Played"
                p2_status = "🟢 ✅ Played" if p2_done else "🔴 ❌ Not Played"
                
                next_player = p1 if not p1_done else p2
                next_name = db.get_user(next_player)['username'] or 'Player'
                
                markup = types.InlineKeyboardMarkup(row_width=3)
                if not p1_done:
                    markup.add(types.InlineKeyboardButton("🪨 ROCK", callback_data=f"rps_pvp_move_{p1}_rock"),
                               types.InlineKeyboardButton("📄 PAPER", callback_data=f"rps_pvp_move_{p1}_paper"),
                               types.InlineKeyboardButton("✂️ SCISSORS", callback_data=f"rps_pvp_move_{p1}_scissors"))
                else:
                    markup.add(types.InlineKeyboardButton("🪨 ROCK", callback_data=f"rps_pvp_move_{p2}_rock"),
                               types.InlineKeyboardButton("📄 PAPER", callback_data=f"rps_pvp_move_{p2}_paper"),
                               types.InlineKeyboardButton("✂️ SCISSORS", callback_data=f"rps_pvp_move_{p2}_scissors"))
                
                bot.edit_message_text(f"✂️ <b>RPS BATTLE</b>\n\n👤 @{p1_name}\n{p1_status}\n\n👤 @{p2_name}\n{p2_status}\n\n<b>@{next_name}'s turn</b>",
                                     call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        else:
            bot.answer_callback_query(call.id, "Feature coming soon!")
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

# ============== GROUP WELCOME ==============
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.is_bot: continue
        
        text = f"""👑 <b>WELCOME TO ZYNOX GAMING</b> 👑

👋 Welcome, @{member.username or member.first_name}!

🎮 Play exciting games
💰 Earn coins
🏆 Increase your rank
⭐ Level up through activity
⚔️ Rob other players
🛡️ Protect your coins

🎁 Start the bot in DM and claim rewards!"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 START BOT", url=f"https://t.me/{bot.get_me().username}?start=welcome"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup)
        break

# ============== OWNER COMMANDS ==============
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Reply to a message to broadcast.")
        return
    
    msg = message.reply_to_message.text or "Broadcast"
    users = db.get_all_users()
    sent = sum(1 for u in users if bot.send_message(u['user_id'], f"📢 <b>BROADCAST</b>\n\n{msg}", parse_mode='HTML'))
    
    bot.reply_to(message, f"✅ Broadcast sent to {sent} users.")

@bot.message_handler(commands=['gcast'])
def handle_gcast(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Reply to a message to broadcast.")
        return
    
    msg = message.reply_to_message.text or "Broadcast"
    groups = db.get_all_groups()
    sent = sum(1 for g in groups if bot.send_message(g['group_id'], f"📢 <b>BROADCAST</b>\n\n{msg}", parse_mode='HTML'))
    
    bot.reply_to(message, f"✅ Broadcast sent to {sent} groups.")

@bot.message_handler(commands=['addcoins'])
def handle_addcoins(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ Usage: /addcoins @username amount")
        return
    
    username = parts[1].replace('@', '')
    amount = int(parts[2])
    
    users = db.get_all_users()
    target = next((u for u in users if u['username'] == username), None)
    
    if not target:
        bot.reply_to(message, f"❌ User @{username} not found.")
        return
    
    db.update_user_coins(target['user_id'], amount)
    user = db.get_user(target['user_id'])
    bot.reply_to(message, f"✅ Added {format_number(amount)} coins to @{username}\n\n📊 New Balance: {format_number(user['coins'])}")

@bot.message_handler(commands=['removecoins'])
def handle_removecoins(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ Usage: /removecoins @username amount")
        return
    
    username = parts[1].replace('@', '')
    amount = int(parts[2])
    
    users = db.get_all_users()
    target = next((u for u in users if u['username'] == username), None)
    
    if not target:
        bot.reply_to(message, f"❌ User @{username} not found.")
        return
    
    db.update_user_coins(target['user_id'], -amount)
    user = db.get_user(target['user_id'])
    bot.reply_to(message, f"✅ Removed {format_number(amount)} coins from @{username}\n\n📊 New Balance: {format_number(user['coins'])}")

@bot.message_handler(commands=['banuser'])
def handle_banuser(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: /banuser @username")
        return
    
    username = parts[1].replace('@', '')
    users = db.get_all_users()
    target = next((u for u in users if u['username'] == username), None)
    
    if not target:
        bot.reply_to(message, f"❌ User @{username} not found.")
        return
    
    db.ban_user(target['user_id'], ' '.join(parts[2:]) if len(parts) > 2 else 'No reason')
    bot.reply_to(message, f"✅ User @{username} banned.")
    bot.send_message(target['user_id'], "🚫 <b>You have been banned</b>\n\nContact support for more information.", parse_mode='HTML')

@bot.message_handler(commands=['unbanuser'])
def handle_unbanuser(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: /unbanuser @username")
        return
    
    username = parts[1].replace('@', '')
    users = db.get_all_users()
    target = next((u for u in users if u['username'] == username), None)
    
    if not target:
        bot.reply_to(message, f"❌ User @{username} not found.")
        return
    
    db.unban_user(target['user_id'])
    bot.reply_to(message, f"✅ User @{username} unbanned.")
    bot.send_message(target['user_id'], "✅ <b>You have been unbanned</b>\n\nYou can now use the bot again.", parse_mode='HTML')

@bot.message_handler(commands=['users'])
def handle_users(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    users = db.get_all_users()
    total_coins = sum(u['coins'] for u in users)
    bot.reply_to(message, f"📊 <b>User Statistics</b>\n\n👥 Total Users: {len(users)}\n💰 Total Coins: {format_number(total_coins)}\n🏅 Avg Coins: {format_number(total_coins // len(users)) if users else 0}", parse_mode='HTML')

@bot.message_handler(commands=['groups'])
def handle_groups(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    groups = db.get_all_groups()
    text = "📊 <b>Group Statistics</b>\n\n"
    for g in groups[:20]:
        text += f"👥 {g['group_name'] or 'Unknown'}: {g['member_count']} members\n"
    if len(groups) > 20:
        text += f"\n... and {len(groups) - 20} more groups"
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=['stats_owner'])
def handle_stats_owner(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    
    users = db.get_all_users()
    groups = db.get_all_groups()
    total_coins = sum(u['coins'] for u in users)
    bot.reply_to(message, f"📊 <b>Bot Statistics</b>\n\n👥 Users: {len(users)}\n👥 Groups: {len(groups)}\n💰 Total Coins: {format_number(total_coins)}\n🏆 Top: {format_number(max([u['coins'] for u in users]) if users else 0)}", parse_mode='HTML')

@bot.message_handler(commands=['restart'])
def handle_restart(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    bot.reply_to(message, "🔄 Bot restarting... (Manual restart required)")

@bot.message_handler(commands=['backup'])
def handle_backup(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ You don't have permission!")
        return
    bot.reply_to(message, "✅ Backup command received. (Manual backup required)")

# ============== TEXT HANDLER ==============
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    # Handle fast type responses
    if message.text and message.text.lower() in FAST_TYPE_WORDS:
        # Check for active fast type session
        pass

# ============== RUN ==============
if __name__ == "__main__":
    logger.info("🚀 Starting Zynox Gaming Bot...")
    bot.infinity_polling()
