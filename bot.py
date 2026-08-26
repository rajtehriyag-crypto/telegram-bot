import telebot
import sqlite3
import random
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import json
import os

# Bot Configuration
BOT_TOKEN = "8897042969:AAFVI298X8Y9kAE0N2MhNDYBcSNfo1klyLU"  # Replace with actual token
OWNER_ID = 8727799160
OWNER_USERNAME = "@internationalpanditG"
SUPPORT_CHANNEL = "https://t.me/+CS-ZvjWSB1oxZjZl"
SUPPORT_GROUP = "https://t.me/+97rox0VQWXNiMzg1"
BOT_USERNAME = "@zynoxgamingbot"

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  coins INTEGER DEFAULT 0,
                  xp INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1,
                  rank TEXT DEFAULT 'Bronze',
                  games_played INTEGER DEFAULT 0,
                  wins INTEGER DEFAULT 0,
                  losses INTEGER DEFAULT 0,
                  daily_claim_date TEXT,
                  dice_rolls_today INTEGER DEFAULT 0,
                  dice_last_reset TEXT,
                  streak INTEGER DEFAULT 0,
                  created_at TEXT)''')
    
    # Groups table
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (group_id INTEGER PRIMARY KEY,
                  group_name TEXT,
                  added_date TEXT)''')
    
    # Transactions table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  type TEXT,
                  amount INTEGER,
                  description TEXT,
                  timestamp TEXT)''')
    
    # Bot wallet table
    c.execute('''CREATE TABLE IF NOT EXISTS bot_wallet
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  balance INTEGER DEFAULT 0,
                  last_updated TEXT)''')
    
    # Initialize wallet if empty
    c.execute("SELECT COUNT(*) FROM bot_wallet")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO bot_wallet (balance, last_updated) VALUES (0, ?)", 
                 (datetime.now().isoformat(),))
    
    # Matches table
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (match_id TEXT PRIMARY KEY,
                  game_type TEXT,
                  host_id INTEGER,
                  player2_id INTEGER,
                  bet_amount INTEGER,
                  prize_pool INTEGER,
                  status TEXT,
                  board TEXT,
                  current_player INTEGER,
                  winner_id INTEGER,
                  created_at TEXT,
                  updated_at TEXT)''')
    
    conn.commit()
    conn.close()

# Database helper functions
def get_user(user_id):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username, first_name):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users 
                 (user_id, username, first_name, created_at) 
                 VALUES (?, ?, ?, ?)""",
              (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_user_balance(user_id, amount):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()
    conn.close()
    return balance[0] if balance else 0

def add_transaction(user_id, type, amount, description):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("""INSERT INTO transactions (user_id, type, amount, description, timestamp) 
                 VALUES (?, ?, ?, ?, ?)""",
              (user_id, type, amount, description, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_bot_wallet():
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM bot_wallet ORDER BY id DESC LIMIT 1")
    balance = c.fetchone()
    conn.close()
    return balance[0] if balance else 0

def update_bot_wallet(amount):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE bot_wallet SET balance = balance + ?, last_updated = ?", 
              (amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Level and Rank calculations
def calculate_level(xp):
    levels = {
        1: 0, 2: 100, 3: 250, 4: 500, 5: 800,
        6: 1150, 7: 1550, 8: 2000, 9: 2500, 10: 3100
    }
    
    for level in sorted(levels.keys()):
        if xp < levels[level]:
            return level - 1, levels[level] if level > 1 else 0
    
    # After level 10
    level = 10
    xp_needed = 3100
    while xp >= xp_needed:
        level += 1
        xp_needed += 500 * (level - 9)
    return level - 1, xp_needed

def get_rank(level):
    if level <= 3: return "🥉 Bronze"
    elif level <= 6: return "🥈 Silver"
    elif level <= 10: return "🥇 Gold"
    elif level <= 15: return "💎 Diamond"
    elif level <= 20: return "👑 Master"
    else: return "🔥 Legend"

def update_user_xp(user_id, xp_gained):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT xp FROM users WHERE user_id = ?", (user_id,))
    current_xp = c.fetchone()[0]
    new_xp = current_xp + xp_gained
    
    level, _ = calculate_level(new_xp)
    rank = get_rank(level)
    
    c.execute("UPDATE users SET xp = ?, level = ?, rank = ? WHERE user_id = ?", 
              (new_xp, level, rank, user_id))
    conn.commit()
    conn.close()

# Main Menu
def main_menu(user_id):
    user = get_user(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Games", callback_data="games"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("🪙 Balance", callback_data="balance"),
        InlineKeyboardButton("🏆 Rank", callback_data="rank"),
        InlineKeyboardButton("📊 Leaderboard", callback_data="leaderboard"),
        InlineKeyboardButton("🎁 Daily", callback_data="daily"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    )
    return markup

# Daily reward
def check_daily_available(user_id):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT daily_claim_date FROM users WHERE user_id = ?", (user_id,))
    last_claim = c.fetchone()
    conn.close()
    
    if not last_claim or not last_claim[0]:
        return True
    
    last_date = datetime.fromisoformat(last_claim[0])
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return last_date < today

def claim_daily(user_id):
    if not check_daily_available(user_id):
        return False
    
    reward = 250
    update_user_balance(user_id, reward)
    add_transaction(user_id, "daily", reward, "Daily reward")
    
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET daily_claim_date = ? WHERE user_id = ?", 
              (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    return True

# Dice system
def get_dice_rolls(user_id):
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("SELECT dice_rolls_today, dice_last_reset FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result or not result[1]:
        return 0
    
    last_reset = datetime.fromisoformat(result[1])
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if last_reset < today:
        # Reset rolls
        conn = sqlite3.connect('zynox_bot.db')
        c = conn.cursor()
        c.execute("UPDATE users SET dice_rolls_today = 0, dice_last_reset = ? WHERE user_id = ?", 
                  (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()
        return 0
    
    return result[0] if result else 0

def roll_dice(user_id):
    rolls_left = 6 - get_dice_rolls(user_id)
    if rolls_left <= 0:
        return None, 0
    
    roll = random.randint(1, 6)
    rewards = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 100}
    reward = rewards[roll]
    
    update_user_balance(user_id, reward)
    add_transaction(user_id, "dice", reward, f"Dice roll {roll}")
    
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("""UPDATE users 
                 SET dice_rolls_today = dice_rolls_today + 1,
                     dice_last_reset = ? 
                 WHERE user_id = ?""",
              (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()
    
    new_rolls_left = 6 - get_dice_rolls(user_id)
    return roll, new_rolls_left

# Tic Tac Toe Game Logic
class TicTacToe:
    def __init__(self):
        self.board = [' '] * 9
        self.current_player = 'X'
        
    def make_move(self, position):
        if self.board[position] == ' ':
            self.board[position] = self.current_player
            if self.check_winner():
                return self.current_player
            self.current_player = 'O' if self.current_player == 'X' else 'X'
            return None
        return False
    
    def check_winner(self):
        win_patterns = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
        for pattern in win_patterns:
            if self.board[pattern[0]] == self.board[pattern[1]] == self.board[pattern[2]] != ' ':
                return self.board[pattern[0]]
        if ' ' not in self.board:
            return 'draw'
        return None
    
    def get_board_display(self):
        display = []
        for i in range(0, 9, 3):
            row = [f"{j+1}️⃣" if self.board[i+j] == ' ' else self.board[i+j] for j in range(3)]
            display.append(" ".join(row))
        return "\n".join(display)

# Game Lobby Management
active_matches = {}

def create_match(game_type, host_id, bet_amount):
    match_id = f"{game_type}_{host_id}_{int(time.time())}"
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    
    c.execute("""INSERT INTO matches 
                 (match_id, game_type, host_id, bet_amount, prize_pool, status, board, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (match_id, game_type, host_id, bet_amount, bet_amount * 2, 'waiting', 
               json.dumps({'board': [' ']*9}), datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    active_matches[match_id] = {
        'game_type': game_type,
        'host_id': host_id,
        'player2_id': None,
        'bet_amount': bet_amount,
        'prize_pool': bet_amount * 2,
        'status': 'waiting',
        'game_instance': TicTacToe() if game_type == 'ttt' else None
    }
    return match_id

def join_match(match_id, player2_id):
    if match_id not in active_matches:
        return False
    
    match = active_matches[match_id]
    if match['status'] != 'waiting' or player2_id == match['host_id']:
        return False
    
    # Check if player has enough coins
    if get_user_balance(player2_id) < match['bet_amount']:
        return False
    
    match['player2_id'] = player2_id
    match['status'] = 'active'
    
    # Deduct bets
    update_user_balance(match['host_id'], -match['bet_amount'])
    update_user_balance(player2_id, -match['bet_amount'])
    
    add_transaction(match['host_id'], 'bet', -match['bet_amount'], f"{match['game_type']} bet")
    add_transaction(player2_id, 'bet', -match['bet_amount'], f"{match['game_type']} bet")
    
    return True

def handle_move(match_id, player_id, position):
    if match_id not in active_matches:
        return None
    
    match = active_matches[match_id]
    if match['status'] != 'active':
        return None
    
    game = match['game_instance']
    if (game.current_player == 'X' and player_id != match['host_id']) or \
       (game.current_player == 'O' and player_id != match['player2_id']):
        return None
    
    result = game.make_move(position)
    if result is False:
        return None
    
    # Check game result
    if result is not None:
        match['status'] = 'completed'
        return result
    
    # Update board in database
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE matches SET board = ?, updated_at = ? WHERE match_id = ?", 
              (json.dumps({'board': game.board}), datetime.now().isoformat(), match_id))
    conn.commit()
    conn.close()
    
    return 'continue'

def settle_match(match_id, winner_id):
    if match_id not in active_matches:
        return False
    
    match = active_matches[match_id]
    if match['status'] != 'active':
        return False
    
    match['status'] = 'completed'
    
    # Calculate winnings (95% of pool)
    prize_pool = match['prize_pool']
    fee = int(prize_pool * 0.05)
    winnings = prize_pool - fee
    
    # Update winner's balance
    update_user_balance(winner_id, winnings)
    add_transaction(winner_id, 'win', winnings, f"{match['game_type']} win")
    
    # Update bot wallet
    update_bot_wallet(fee)
    
    # Update stats
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET games_played = games_played + 1 WHERE user_id = ?", (winner_id,))
    # Update XP (50 for win)
    c.execute("UPDATE users SET xp = xp + 50 WHERE user_id = ?", (winner_id,))
    # Update loser XP (10 for loss)
    loser_id = match['host_id'] if match['host_id'] != winner_id else match['player2_id']
    c.execute("UPDATE users SET xp = xp + 10, losses = losses + 1 WHERE user_id = ?", (loser_id,))
    conn.commit()
    conn.close()
    
    # Update match in database
    conn = sqlite3.connect('zynox_bot.db')
    c = conn.cursor()
    c.execute("UPDATE matches SET winner_id = ?, status = ?, updated_at = ? WHERE match_id = ?", 
              (winner_id, 'completed', datetime.now().isoformat(), match_id))
    conn.commit()
    conn.close()
    
    return True

# Bot Commands
@bot.message_handler(commands=['start'])
def handle_start(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        bot.reply_to(message, "❌ Please use /start in DM only!")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    first_name = message.from_user.first_name or "User"
    
    # Check if user exists
    user = get_user(user_id)
    if not user:
        create_user(user_id, username, first_name)
    
    welcome = f"""╔══════════════════════╗
🎮 ZYNOX GAMING
╚══════════════════════╝

👋 Welcome, {first_name}! 🎮

╔══════════════════════╗
🎯 Your Gaming Hub
╚══════════════════════╝

⚡ Play Games
🪙 Earn Coins
⭐ Level Up
🏆 Compete Globally

📢 Support: {SUPPORT_CHANNEL}
👥 Group: {SUPPORT_GROUP}

━━━━━━━━━━━━━━━━━━━━━━
🔥 Ready to Play?
━━━━━━━━━━━━━━━━━━━━━━"""
    
    bot.send_message(user_id, welcome, reply_markup=main_menu(user_id))

@bot.message_handler(commands=['daily'])
def handle_daily(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        bot.reply_to(message, "❌ Please use /daily in DM only!")
        return
    
    user_id = message.from_user.id
    
    if claim_daily(user_id):
        balance = get_user_balance(user_id)
        response = f"""╔══════════════════════╗
🎁 DAILY REWARD
╚══════════════════════╝

🎉 Daily Reward Claimed!

🪙 +250 Coins
💰 Balance : {balance}

━━━━━━━━━━━━━━━━━━━━━━
🔥 Come Back Tomorrow!
━━━━━━━━━━━━━━━━━━━━━━"""
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "❌ You've already claimed your daily reward today!\nCome back tomorrow at 12:00 AM IST.")

@bot.message_handler(commands=['dice'])
def handle_dice(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        # Check support channel/group membership here
        pass
    
    user_id = message.from_user.id
    roll, rolls_left = roll_dice(user_id)
    
    if roll is None:
        bot.reply_to(message, "❌ No rolls left today! Come back tomorrow at 12:00 AM IST.")
        return
    
    balance = get_user_balance(user_id)
    
    if roll == 6:
        response = f"""╔══════════════════════╗
⚡ STRIKE ⚡
╚══════════════════════╝

🎲 Roll Result : 6️⃣

💥 STRIKE!

🪙 Reward : +100 Coins
💰 Balance : {balance}

🎯 Rolls Left : {rolls_left}/6

━━━━━━━━━━━━━━━━━━━━━━"""
    else:
        reward = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}[roll]
        response = f"""╔══════════════════════╗
🎲 DICE ROLL
╚══════════════════════╝

🎲 Roll Result : {roll}️⃣

🪙 Reward : +{reward} Coins
💰 Balance : {balance}

🎯 Rolls Left : {rolls_left}/6

━━━━━━━━━━━━━━━━━━━━━━"""
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.reply_to(message, "❌ Please start the bot first with /start")
        return
    
    response = f"""╔══════════════════════╗
👤 PROFILE
╚══════════════════════╝

👤 Name: {user[2]}
🆔 ID: {user[0]}
⭐ XP: {user[4]}
📈 Level: {user[5]}
🪙 Coins: {user[3]}
🎮 Games: {user[7]}
🏆 Wins: {user[8]}
💔 Losses: {user[9]}
📊 Win Rate: {calculate_win_rate(user[8], user[7])}
🥇 Rank: {user[6]}

━━━━━━━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, response)

@bot.message_handler(commands=['rank'])
def handle_rank(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.reply_to(message, "❌ Please start the bot first with /start")
        return
    
    level, next_level_xp = calculate_level(user[4])
    xp_to_next = next_level_xp - user[4] if level < 100 else 0
    
    response = f"""╔══════════════════════╗
🏆 YOUR RANK
╚══════════════════════╝

👤 {user[2]}

⭐ Level : {user[5]}
📈 XP : {user[4]} / {next_level_xp}

🥇 Rank : {user[6]}

🌎 Global : #N/A
👥 This Group : #N/A

━━━━━━━━━━━━━━━━━━━━━━
🔥 {xp_to_next} XP to Level {user[5] + 1}
━━━━━━━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, response)

@bot.message_handler(commands=['ttt'])
def handle_ttt(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        handle_pvp_game(message, 'ttt')
    else:
        handle_dm_practice(message, 'ttt')

def handle_pvp_game(message, game_type):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, f"❌ Usage: /{game_type} <amount>\nMinimum bet: 50 coins")
        return
    
    bet_amount = int(args[1])
    if bet_amount < 50:
        bot.reply_to(message, "❌ Minimum bet is 50 coins!")
        return
    
    user_id = message.from_user.id
    balance = get_user_balance(user_id)
    
    if balance < bet_amount:
        bot.reply_to(message, f"❌ Insufficient balance! You have {balance} coins.")
        return
    
    # Create match
    match_id = create_match(game_type, user_id, bet_amount)
    
    # Create game lobby message
    game_names = {'ttt': 'TIC TAC TOE', 'rps': 'RPS BATTLE'}
    game_emojis = {'ttt': '🎮', 'rps': '✊'}
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎮 JOIN GAME", callback_data=f"join_{match_id}"))
    
    response = f"""╔══════════════════════╗
{game_emojis[game_type]} {game_names[game_type]}
╚══════════════════════╝

👤 Host : @{message.from_user.username or "Player"}

🪙 Entry : {bet_amount} Coins
🏆 Prize Pool : {bet_amount * 2} Coins
🏦 Fee : 5%

━━━━━━━━━━━━━━━━━━━━━━
⚡ Waiting for Player 2
━━━━━━━━━━━━━━━━━━━━━━"""
    
    bot.reply_to(message, response, reply_markup=markup)

def handle_dm_practice(message, game_type):
    # DM Practice Mode
    if game_type == 'ttt':
        game = TicTacToe()
        markup = create_ttt_board(game, None, practice=True)
        bot.reply_to(message, "🎮 Practice Mode - No Coins/XP", reply_markup=markup)
    elif game_type == 'rps':
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("🪨 ROCK", callback_data="practice_rps_rock"),
            InlineKeyboardButton("📄 PAPER", callback_data="practice_rps_paper"),
            InlineKeyboardButton("✂️ SCISSORS", callback_data="practice_rps_scissors")
        )
        bot.reply_to(message, "✊ Practice Mode - Choose your move!", reply_markup=markup)

def create_ttt_board(game, match_id=None, practice=False):
    markup = InlineKeyboardMarkup(row_width=3)
    board = game.board
    
    for i in range(0, 9, 3):
        buttons = []
        for j in range(3):
            pos = i + j
            if board[pos] == ' ':
                if practice:
                    callback = f"practice_ttt_{pos}"
                else:
                    callback = f"ttt_move_{match_id}_{pos}"
                text = f"{pos + 1}️⃣"
            else:
                text = board[pos]
                callback = "none"
            buttons.append(InlineKeyboardButton(text, callback_data=callback))
        markup.row(*buttons)
    
    if not practice:
        markup.add(InlineKeyboardButton("❌ Cancel Game", callback_data=f"cancel_{match_id}"))
    
    return markup

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    
    if data == "games":
        show_games_menu(call.message)
    elif data == "profile":
        show_profile(call.message)
    elif data == "balance":
        show_balance(call.message)
    elif data == "rank":
        show_rank(call.message)
    elif data == "leaderboard":
        show_leaderboard(call.message)
    elif data == "daily":
        show_daily(call.message)
    elif data == "help":
        show_help(call.message)
    elif data.startswith("join_"):
        handle_join_match(call)
    elif data.startswith("ttt_move_"):
        handle_ttt_move(call)
    elif data.startswith("practice_ttt_"):
        handle_practice_ttt(call)
    elif data.startswith("practice_rps_"):
        handle_practice_rps(call)
    elif data.startswith("cancel_"):
        handle_cancel_match(call)

def show_games_menu(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Tic Tac Toe", callback_data="game_ttt"),
        InlineKeyboardButton("✊ RPS", callback_data="game_rps"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
    )
    bot.edit_message_text("🎮 Select a game:", message.chat.id, message.message_id, reply_markup=markup)

def show_profile(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.reply_to(message, "❌ Please start the bot first with /start")
        return
    
    response = f"""╔══════════════════════╗
👤 PROFILE
╚══════════════════════╝

👤 Name: {user[2]}
🆔 ID: {user[0]}
⭐ XP: {user[4]}
📈 Level: {user[5]}
🪙 Coins: {user[3]}
🎮 Games: {user[7]}
🏆 Wins: {user[8]}
💔 Losses: {user[9]}
📊 Win Rate: {calculate_win_rate(user[8], user[7])}
🥇 Rank: {user[6]}

━━━━━━━━━━━━━━━━━━━━━━"""
    bot.edit_message_text(response, message.chat.id, message.message_id, 
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
                         ))

def show_balance(message):
    user_id = message.from_user.id
    balance = get_user_balance(user_id)
    
    response = f"""╔══════════════════════╗
🪙 BALANCE
╚══════════════════════╝

💰 Your Balance: {balance} Coins

━━━━━━━━━━━━━━━━━━━━━━
🎮 Play games to earn more!
━━━━━━━━━━━━━━━━━━━━━━"""
    bot.edit_message_text(response, message.chat.id, message.message_id,
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
                         ))

def show_rank(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.reply_to(message, "❌ Please start the bot first with /start")
        return
    
    level, next_level_xp = calculate_level(user[4])
    xp_to_next = next_level_xp - user[4] if level < 100 else 0
    
    response = f"""╔══════════════════════╗
🏆 YOUR RANK
╚══════════════════════╝

👤 {user[2]}

⭐ Level : {user[5]}
📈 XP : {user[4]} / {next_level_xp}

🥇 Rank : {user[6]}

🌎 Global : #N/A
👥 This Group : #N/A

━━━━━━━━━━━━━━━━━━━━━━
🔥 {xp_to_next} XP to Level {user[5] + 1}
━━━━━━━━━━━━━━━━━━━━━━"""
    bot.edit_message_text(response, message.chat.id, message.message_id,
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
                         ))

def show_leaderboard(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🌎 GLOBAL", callback_data="lb_global"),
        InlineKeyboardButton("👥 GROUP", callback_data="lb_group"),
        InlineKeyboardButton("⭐ XP", callback_data="lb_xp"),
        InlineKeyboardButton("🪙 COINS", callback_data="lb_coins"),
        InlineKeyboardButton("🏆 WINS", callback_data="lb_wins"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
    )
    bot.edit_message_text("📊 Select Leaderboard Type:", message.chat.id, message.message_id, reply_markup=markup)

def show_daily(message):
    user_id = message.from_user.id
    
    if claim_daily(user_id):
        balance = get_user_balance(user_id)
        response = f"""╔══════════════════════╗
🎁 DAILY REWARD
╚══════════════════════╝

🎉 Daily Reward Claimed!

🪙 +250 Coins
💰 Balance : {balance}

━━━━━━━━━━━━━━━━━━━━━━
🔥 Come Back Tomorrow!
━━━━━━━━━━━━━━━━━━━━━━"""
    else:
        response = f"""╔══════════════════════╗
🎁 DAILY REWARD
╚══════════════════════╝

❌ Already Claimed Today!

⏰ Next Claim: Tomorrow 12:00 AM IST

━━━━━━━━━━━━━━━━━━━━━━
🔥 Come Back Tomorrow!
━━━━━━━━━━━━━━━━━━━━━━"""
    
    bot.edit_message_text(response, message.chat.id, message.message_id,
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
                         ))

def show_help(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 GAMES", callback_data="help_games"),
        InlineKeyboardButton("🪙 ECONOMY", callback_data="help_economy"),
        InlineKeyboardButton("👤 PROFILE", callback_data="help_profile"),
        InlineKeyboardButton("🎁 REWARDS", callback_data="help_rewards"),
        InlineKeyboardButton("📖 GUIDE", callback_data="help_guide"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")
    )
    bot.edit_message_text("📖 Help Menu:", message.chat.id, message.message_id, reply_markup=markup)

def calculate_win_rate(wins, games_played):
    if games_played == 0:
        return "0%"
    return f"{(wins / games_played * 100):.1f}%"

def handle_join_match(call):
    match_id = call.data.split("_")[1]
    user_id = call.from_user.id
    
    if match_id not in active_matches:
        bot.answer_callback_query(call.id, "❌ Game expired!")
        return
    
    if join_match(match_id, user_id):
        match = active_matches[match_id]
        # Start the game
        game = match['game_instance']
        markup = create_ttt_board(game, match_id)
        
        bot.edit_message_text(
            f"🎮 Game Started!\n\n" + game.get_board_display(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id, "✅ Joined successfully!")
    else:
        bot.answer_callback_query(call.id, "❌ Cannot join game!")

def handle_ttt_move(call):
    data = call.data.split("_")
    match_id = data[2]
    position = int(data[3])
    user_id = call.from_user.id
    
    result = handle_move(match_id, user_id, position)
    if result is None:
        bot.answer_callback_query(call.id, "❌ Invalid move!")
        return
    
    match = active_matches[match_id]
    game = match['game_instance']
    
    if result == 'continue':
        markup = create_ttt_board(game, match_id)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, "✅ Move made!")
    elif result == 'draw':
        # Return bets
        update_user_balance(match['host_id'], match['bet_amount'])
        update_user_balance(match['player2_id'], match['bet_amount'])
        add_transaction(match['host_id'], 'refund', match['bet_amount'], "Draw refund")
        add_transaction(match['player2_id'], 'refund', match['bet_amount'], "Draw refund")
        
        # Update match status
        match['status'] = 'completed'
        
        bot.edit_message_text(
            f"🤝 Game Draw!\n\n" + game.get_board_display() + "\n\nBoth players get their bets back!",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, "🤝 Draw!")
    elif result in ['X', 'O']:
        winner_id = match['host_id'] if result == 'X' else match['player2_id']
        settle_match(match_id, winner_id)
        
        winner_name = call.from_user.first_name if winner_id == user_id else "Player"
        bot.edit_message_text(
            f"🏆 Game Over!\n\n{game.get_board_display()}\n\n🎉 Winner: {winner_name}!",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, "🏆 Game Over!")

def handle_practice_ttt(call):
    position = int(call.data.split("_")[2])
    # Simple practice mode - bot responds randomly
    # For now, just show message
    bot.answer_callback_query(call.id, "🎮 Practice mode - AI coming soon!")

def handle_practice_rps(call):
    choice = call.data.split("_")[2]
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
    beats = {'rock': 'scissors', 'paper': 'rock', 'scissors': 'paper'}
    
    if choice == bot_choice:
        result = "🤝 Draw!"
    elif beats[choice] == bot_choice:
        result = "🎉 You Win!"
    else:
        result = "😔 You Lose!"
    
    response = f"""✊ RPS Practice

You: {emojis[choice]}
Bot: {emojis[bot_choice]}

{result}

🔁 Play again with /rps in DM"""
    
    bot.edit_message_text(response, call.message.chat.id, call.message.message_id,
                         reply_markup=InlineKeyboardMarkup().add(
                             InlineKeyboardButton("🔄 Play Again", callback_data="practice_rps_again")
                         ))
    bot.answer_callback_query(call.id, "✅ Move made!")

def handle_cancel_match(call):
    match_id = call.data.split("_")[1]
    if match_id in active_matches:
        match = active_matches[match_id]
        if match['status'] == 'waiting':
            del active_matches[match_id]
            # Delete from database
            conn = sqlite3.connect('zynox_bot.db')
            c = conn.cursor()
            c.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
            conn.commit()
            conn.close()
            bot.edit_message_text("❌ Game cancelled!", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "✅ Game cancelled!")
        else:
            bot.answer_callback_query(call.id, "❌ Game already started!")
    else:
        bot.answer_callback_query(call.id, "❌ Game not found!")

# Owner commands
@bot.message_handler(commands=['wallet'])
def handle_wallet(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    balance = get_bot_wallet()
    response = f"""╔══════════════════════╗
🏦 BOT WALLET
╚══════════════════════╝

💰 Balance: {balance} Coins

━━━━━━━━━━━━━━━━━━━━━━
📊 Total Fees Collected
━━━━━━━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, response)

@bot.message_handler(commands=['give'])
def handle_give(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Usage: /give @username 5000 or /give user_id 5000")
        return
    
    target = args[1]
    amount = int(args[2])
    
    if amount <= 0:
        bot.reply_to(message, "❌ Amount must be positive!")
        return
    
    # Get user_id
    if target.startswith('@'):
        # Get user by username
        conn = sqlite3.connect('zynox_bot.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (target[1:],))
        result = c.fetchone()
        conn.close()
        if not result:
            bot.reply_to(message, "❌ User not found!")
            return
        user_id = result[0]
    else:
        user_id = int(target)
    
    update_user_balance(user_id, amount)
    add_transaction(user_id, 'give', amount, f"Admin give {amount} coins")
    update_bot_wallet(-amount)
    
    bot.reply_to(message, f"✅ Successfully gave {amount} coins to user {target}!")

@bot.message_handler(commands=['take'])
def handle_take(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "❌ Usage: /take @username 500 or /take user_id 500")
        return
    
    target = args[1]
    amount = int(args[2])
    
    if amount <= 0:
        bot.reply_to(message, "❌ Amount must be positive!")
        return
    
    # Get user_id
    if target.startswith('@'):
        conn = sqlite3.connect('zynox_bot.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (target[1:],))
        result = c.fetchone()
        conn.close()
        if not result:
            bot.reply_to(message, "❌ User not found!")
            return
        user_id = result[0]
    else:
        user_id = int(target)
    
    # Check if user has enough balance
    balance = get_user_balance(user_id)
    if balance < amount:
        bot.reply_to(message, f"❌ User only has {balance} coins!")
        return
    
    update_user_balance(user_id, -amount)
    add_transaction(user_id, 'take', -amount, f"Admin take {amount} coins")
    update_bot_wallet(amount)
    
    bot.reply_to(message, f"✅ Successfully took {amount} coins from user {target}!")

# Group welcome message
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            # Bot added to group
            conn = sqlite3.connect('zynox_bot.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO groups (group_id, group_name, added_date) VALUES (?, ?, ?)",
                     (message.chat.id, message.chat.title, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            continue
        
        # Welcome new member
        welcome = f"""╔═ 🎉✨ WELCOME ✨🎉 ═╗

👋 Welcome, {member.first_name} 💎

🆔 User ID : "{member.id}"
👤 Username : @{member.username or 'No username'}

🎮 Welcome To 🎮
✅ 𝐙𝐘𝐍𝐎𝐗 𝐆𝐀𝐌𝐈𝐍𝐆 ✅

╚══ 🚀💓 ENJOY 💓🚀 ══╝"""
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎮 START BOT", url=f"https://t.me/{BOT_USERNAME}?start"))
        
        bot.send_message(message.chat.id, welcome, reply_markup=markup)

# Start the bot
if __name__ == "__main__":
    init_db()
    print("🤖 ZYNOX GAMING BOT started!")
    print(f"👑 Owner: {OWNER_USERNAME} (ID: {OWNER_ID})")
    print(f"📢 Support Channel: {SUPPORT_CHANNEL}")
    print(f"👥 Support Group: {SUPPORT_GROUP}")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
