"""
REALMX HELPER - Telegram group management bot

Run locally (Linux / macOS / Railway / Replit Terminal):
    pip install python-telegram-bot
    BOT_TOKEN="8980536868:AAHjaPCAcer6TCfbfpMqdcTTp_CFvhnNu7w" OWNER_ID="8727799160" python bot.py
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from telegram import (
    BotCommand,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ----------------------------- Configuration -----------------------------

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
log = logging.getLogger("realmx")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "8727799160"))
DB_PATH = os.getenv("DB_PATH", "realmx.db")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "@realmXsupport")
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/+6BXS6AfvJPQ2OTI1")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Add it in Environment Variables.")

UTC = timezone.utc
START_TIME = time.time()
recent_messages: dict[tuple[int, int], deque[float]] = defaultdict(lambda: deque(maxlen=20))
recent_text: dict[tuple[int, int], tuple[str, float]] = {}
message_cache: dict[tuple[int, int], str] = {}
captcha_storage: dict[tuple[int, int], int] = {}


# -------------------------------- Database --------------------------------

class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        parent = Path(path).expanduser().parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT '',
                is_bot INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                coins INTEGER NOT NULL DEFAULT 0,
                bank INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                messages INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT NOT NULL DEFAULT '',
                daily_streak INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                first_seen TEXT NOT NULL,
                messages INTEGER NOT NULL DEFAULT 0,
                welcome_enabled INTEGER NOT NULL DEFAULT 1,
                goodbye_enabled INTEGER NOT NULL DEFAULT 1,
                welcome_text TEXT NOT NULL DEFAULT '',
                rules TEXT NOT NULL DEFAULT '',
                antispam INTEGER NOT NULL DEFAULT 0,
                antiflood INTEGER NOT NULL DEFAULT 0,
                antiraid INTEGER NOT NULL DEFAULT 0,
                captcha INTEGER NOT NULL DEFAULT 0,
                blocklist TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS group_users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                last_seen TEXT NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS staff (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, item)
            );
            CREATE TABLE IF NOT EXISTS chat_stats (
                chat_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                messages INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, day)
            );
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                messages INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, day)
            );
            CREATE TABLE IF NOT EXISTS checkins (
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                reward INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, day)
            );
            CREATE TABLE IF NOT EXISTS weekly_rewards (
                user_id INTEGER NOT NULL,
                week TEXT NOT NULL,
                reward INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, week)
            );
            CREATE TABLE IF NOT EXISTS marriages (
                user_id INTEGER PRIMARY KEY,
                partner_id INTEGER NOT NULL,
                married_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_claims (
                user_id INTEGER PRIMARY KEY,
                last_work TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS crime_claims (
                user_id INTEGER PRIMARY KEY,
                last_crime TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS investments (
                user_id INTEGER PRIMARY KEY,
                amount INTEGER NOT NULL,
                invested_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lottery_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS afk (
                user_id INTEGER PRIMARY KEY,
                reason TEXT NOT NULL,
                since TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snipes (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                text TEXT NOT NULL,
                deleted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edit_snipes (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                old_text TEXT NOT NULL,
                new_text TEXT NOT NULL,
                edited_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS filters (
                chat_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                reply_text TEXT NOT NULL,
                PRIMARY KEY (chat_id, keyword)
            );
            """
        )
        try:
            self.conn.execute("ALTER TABLE users ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def one(self, sql: str, params: tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchone()

    def all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def close(self) -> None:
        self.conn.close()

db = Database(DB_PATH)

# --------------------------------- Helpers ---------------------------------

def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

def today() -> str:
    return datetime.now(UTC).date().isoformat()

def ensure_user(user: Any) -> None:
    if not user:
        return
    db.execute(
        """
        INSERT INTO users(user_id, name, username, is_bot, first_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,
        username=excluded.username, is_bot=excluded.is_bot
        """,
        (user.id, user.full_name or "", user.username or "", int(bool(getattr(user, "is_bot", False))), now_iso()),
    )

def ensure_group(chat: Any) -> None:
    if not chat or chat.type not in ("group", "supergroup"):
        return
    db.execute(
        """
        INSERT INTO groups(chat_id, title, first_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title
        """,
        (chat.id, chat.title or "", now_iso()),
    )

def record_message(chat_id: int, user_id: int) -> None:
    day = today()
    db.execute("UPDATE users SET messages=messages+1, xp=xp+1 WHERE user_id=?", (user_id,))
    db.execute(
        """
        INSERT INTO group_users(chat_id, user_id, last_seen) VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET last_seen=excluded.last_seen
        """,
        (chat_id, user_id, now_iso()),
    )
    db.execute("UPDATE groups SET messages=messages+1 WHERE chat_id=?", (chat_id,))
    db.execute(
        """
        INSERT INTO chat_stats(chat_id, day, messages) VALUES (?, ?, 1)
        ON CONFLICT(chat_id, day) DO UPDATE SET messages=messages+1
        """,
        (chat_id, day),
    )
    db.execute(
        """
        INSERT INTO user_stats(user_id, day, messages) VALUES (?, ?, 1)
        ON CONFLICT(user_id, day) DO UPDATE SET messages=messages+1
        """,
        (user_id, day),
    )
    row = db.one("SELECT xp FROM users WHERE user_id=?", (user_id,))
    if row:
        level = max(1, int(row["xp"]) // 100 + 1)
        db.execute("UPDATE users SET level=? WHERE user_id=?", (level, user_id))

def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(name or "User")}</a>'

def display_user(user: Any) -> str:
    return f"@{user.username}" if getattr(user, "username", None) else (user.full_name or f"User {user.id}")

def is_group(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in ("group", "supergroup"))

def is_owner(user_id: Optional[int]) -> bool:
    return user_id == OWNER_ID

async def is_user_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except TelegramError:
        return False

def rank_name(rank: int) -> str:
    return {1: "Realm Keeper", 2: "Realm Guardian", 3: "Realm Commander"}.get(rank, "Member")

def rank_permission(rank: int, permission: str) -> bool:
    permissions = {
        1: {"warn", "delete"},
        2: {"warn", "delete", "mute", "pin"},
        3: {"warn", "delete", "mute", "pin", "full"},
    }
    return permission in permissions.get(rank, set())

def staff_rank(chat_id: int, user_id: int) -> int:
    row = db.one("SELECT rank FROM staff WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return int(row["rank"]) if row else 0

async def can_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE, permission: str = "full") -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not is_group(update):
        return False
    if await is_user_admin(chat.id, user.id, context):
        return True
    return rank_permission(staff_rank(chat.id, user.id), permission)

async def require_group(update: Update) -> bool:
    if not is_group(update):
        await update.effective_message.reply_text("Yeh command sirf group mein use ki ja sakti hai.")
        return False
    return True

async def require_dm(update: Update) -> bool:
    if is_group(update):
        bot_username = (await update.get_bot().get_me()).username
        await update.effective_message.reply_text(
            f"🔒 Yeh command privacy ke liye sirf DM me chalti hai.\n👉 <a href='tg://resolve?domain={bot_username}'>Mujhe Private DM Karein</a>",
            parse_mode=ParseMode.HTML
        )
        return False
    return True

async def require_moderator(update: Update, context: ContextTypes.DEFAULT_TYPE, permission: str = "full") -> bool:
    if not await require_group(update):
        return False
    if not await can_moderate(update, context, permission):
        await update.effective_message.reply_text("Aapke paas is command ke liye permission nahi hai.")
        return False
    return True

async def target_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[Optional[int], str]:
    message = update.effective_message
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        ensure_user(target)
        return target.id, display_user(target)
    if context.args:
        value = context.args[0].strip()
        if value.startswith("@"):
            try:
                target = await context.bot.get_chat(value)
                return target.id, value
            except TelegramError:
                return None, value
        try:
            target_id = int(value)
            row = db.one("SELECT name, username FROM users WHERE user_id=?", (target_id,))
            return target_id, ("@" + row["username"] if row and row["username"] else value)
        except ValueError:
            return None, value
    return None, ""

async def safe_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, message: Optional[Any] = None) -> bool:
    try:
        await context.bot.delete_message(chat_id, message_id)
        if message and getattr(message, "from_user", None):
            text = message.text or message.caption or ""
            if text:
                db.execute(
                    """
                    INSERT INTO snipes(chat_id, user_id, name, text, deleted_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id) DO UPDATE SET user_id=excluded.user_id,
                    name=excluded.name, text=excluded.text, deleted_at=excluded.deleted_at
                    """,
                    (chat_id, message.from_user.id, message.from_user.full_name or "User", text, now_iso()),
                )
        return True
    except TelegramError:
        return False

def parse_int(value: str, default: int, minimum: int = 0, maximum: int = 1000) -> int:
    try:
        number = int(value)
        return number if minimum <= number <= maximum else default
    except (TypeError, ValueError):
        return default

def user_row(user_id: int) -> sqlite3.Row:
    row = db.one("SELECT * FROM users WHERE user_id=?", (user_id,))
    if row:
        return row
    db.execute("INSERT INTO users(user_id, first_seen) VALUES (?, ?)", (user_id, now_iso()))
    return db.one("SELECT * FROM users WHERE user_id=?", (user_id,))  # type: ignore[return-value]

def setting(chat_id: int, name: str) -> Any:
    row = db.one(f"SELECT {name} FROM groups WHERE chat_id=?", (chat_id,))
    return row[name] if row else 0

async def send_long(update: Update, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    for index in range(0, len(text), 4000):
        await update.effective_message.reply_text(
            text[index : index + 4000],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup if index == 0 else None,
        )

# ----------------------------- Owner Commands (DM ONLY) -----------------------------

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update) or not is_owner(update.effective_user.id if update.effective_user else None):
        return
    await update.effective_message.reply_text(
        "👑 REALMX CONTROL PANEL\n\n⚙️ Bot Management\n📊 Statistics\n📢 Broadcast\n🔄 Restart\n\nOwner Access Verified ✅",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📊 Statistics", callback_data="stats")],
                [InlineKeyboardButton("📚 Help", callback_data="help")],
            ]
        ),
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update) or not is_owner(update.effective_user.id if update.effective_user else None):
        return
    text = " ".join(context.args).strip()
    if not text and update.effective_message.reply_to_message:
        text = update.effective_message.reply_to_message.text or ""
    if not text:
        await update.effective_message.reply_text("Usage: /broadcast <message> ya kisi message ko reply karke /broadcast")
        return
    users = db.all("SELECT user_id FROM users")
    reached = 0
    for row in users:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {html.escape(text)}", parse_mode=ParseMode.HTML)
            reached += 1
            await asyncio.sleep(0.04)
        except TelegramError:
            continue
    await update.effective_message.reply_text(f"📢 GLOBAL BROADCAST COMPLETE ✅\n\n👥 Users Reached: {reached}")

async def gcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update) or not is_owner(update.effective_user.id if update.effective_user else None):
        return
    text = " ".join(context.args).strip()
    if not text and update.effective_message.reply_to_message:
        text = update.effective_message.reply_to_message.text or ""
    if not text:
        await update.effective_message.reply_text("Usage: /gcast <message>")
        return
    groups = db.all("SELECT chat_id FROM groups")
    sent = 0
    for row in groups:
        try:
            await context.bot.send_message(row["chat_id"], html.escape(text), parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramError:
            continue
    await update.effective_message.reply_text(f"🌍 GROUP BROADCAST COMPLETE ✅\n\nGroups Reached: {sent}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_owner(update.effective_user.id if update.effective_user else None):
        return
    users = db.one("SELECT COUNT(*) AS n FROM users")["n"]
    groups = db.one("SELECT COUNT(*) AS n FROM groups")["n"]
    messages = db.one("SELECT COALESCE(SUM(messages), 0) AS n FROM users")["n"]
    await update.effective_message.reply_text(
        f"📊 REALMX STATISTICS\n\n👥 Users: {users}\n🏘️ Groups: {groups}\n💬 Messages: {messages}\n\n⚡ Status: Online"
    )

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update) or not is_owner(update.effective_user.id if update.effective_user else None):
        return
    await update.effective_message.reply_text("🔄 REALMX CORE RESTARTING...\n\nPlease Wait...")
    await asyncio.sleep(1)
    db.close()
    os.execv(sys.executable, [sys.executable, *sys.argv])

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update) or not is_owner(update.effective_user.id if update.effective_user else None):
        return
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    destination = backup_dir / f"realmx-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.db"
    db.conn.commit()
    backup_connection = sqlite3.connect(destination)
    try:
        db.conn.backup(backup_connection)
    finally:
        backup_connection.close()
    await update.effective_message.reply_text(f"💾 BACKUP CREATED\n\nFile: {destination.name}")

# --------------------------- Moderation Commands --------------------------

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /ban @username use karein.")
        return
    if target_id == OWNER_ID:
        await update.effective_message.reply_text("Owner ko ban nahi kiya ja sakta.")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
    except TelegramError as error:
        await update.effective_message.reply_text(f"Ban nahi hua: {error.message}")
        return
    admin = display_user(update.effective_user)
    await update.effective_message.reply_text(
        f"🔨 REALMX JUDGEMENT\n\n👤 User: {html.escape(target_name)}\n\n"
        f"☠️ Group se ban kar diya gaya hai!\n\n👮 Action By: {html.escape(admin)}",
        parse_mode=ParseMode.HTML,
    )

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("Usage: /unban @username ya user id")
        return
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target_id, only_if_banned=True)
    except TelegramError as error:
        await update.effective_message.reply_text(f"Unban nahi hua: {error.message}")
        return
    await update.effective_message.reply_text(
        f"✅ BAN REMOVED\n\n👤 {html.escape(target_name)}\n\nWelcome Back To The Realm.",
        parse_mode=ParseMode.HTML,
    )

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /kick @username use karein.")
        return
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
    except TelegramError as error:
        await update.effective_message.reply_text(f"Kick nahi hua: {error.message}")
        return
    await update.effective_message.reply_text(
        f"👢 ORBIT EJECTION\n\n🚀 {html.escape(target_name)} ko group se kick kar diya gaya.",
        parse_mode=ParseMode.HTML,
    )

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "mute"):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /mute @username [minutes] use karein.")
        return
    minutes = parse_int(context.args[1] if len(context.args) > 1 else "60", 60, 1, 10080)
    until = datetime.now(UTC) + timedelta(minutes=minutes)
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
    except TelegramError as error:
        await update.effective_message.reply_text(f"Mute nahi hua: {error.message}")
        return
    await update.effective_message.reply_text(
        f"🔇 SILENCE MODE ACTIVATED\n\n🤫 {html.escape(target_name)}\n\nDuration: {minutes} minutes",
        parse_mode=ParseMode.HTML,
    )

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "mute"):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /unmute @username use karein.")
        return
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
    except TelegramError as error:
        await update.effective_message.reply_text(f"Unmute nahi hua: {error.message}")
        return
    await update.effective_message.reply_text(
        f"🔊 VOICE RESTORED\n\n🎉 {html.escape(target_name)} can speak again.",
        parse_mode=ParseMode.HTML,
    )

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "warn"):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /warn @username use karein.")
        return
    row = db.one("SELECT count FROM warnings WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target_id))
    count = int(row["count"]) + 1 if row else 1
    db.execute(
        """
        INSERT INTO warnings(chat_id, user_id, count) VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET count=excluded.count
        """,
        (update.effective_chat.id, target_id, count),
    )
    action = ""
    if count >= 3 and target_id != OWNER_ID:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target_id)
            action = "\n☠️ 3 warnings complete — user banned."
        except TelegramError:
            pass
    await update.effective_message.reply_text(
        f"⚠️ WARNING ISSUED\n\n👤 {html.escape(target_name)}\n📛 Warning: {count}/3{action}",
        parse_mode=ParseMode.HTML,
    )

async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "warn"):
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("User ko reply karein ya /unwarn @username use karein.")
        return
    db.execute("UPDATE warnings SET count=MAX(0, count-1) WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target_id))
    await update.effective_message.reply_text(
        f"✅ WARNING REMOVED\n\n👤 {html.escape(target_name)}\n\nRecord updated.",
        parse_mode=ParseMode.HTML,
    )

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "delete"):
        return
    message = update.effective_message
    count = parse_int(context.args[0] if context.args else "10", 10, 1, 100)
    if not message.reply_to_message:
        await message.reply_text("Jis message se purge shuru karna hai usko reply karke /purge [count] use karein.")
        return
    start_id = message.reply_to_message.message_id
    deleted = 0
    for message_id in range(start_id, start_id + count):
        if await safe_delete(context, update.effective_chat.id, message_id):
            deleted += 1
            await asyncio.sleep(0.02)
    await context.bot.send_message(update.effective_chat.id, f"🧹 PURGE COMPLETE\n\nMessages Removed: {deleted}")

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "pin"):
        return
    reply = update.effective_message.reply_to_message
    if not reply:
        await update.effective_message.reply_text("Pinned message ko reply karke /pin use karein.")
        return
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, reply.message_id, disable_notification=True)
        await update.effective_message.reply_text("📌 MESSAGE PINNED")
    except TelegramError as error:
        await update.effective_message.reply_text(f"Pin nahi hua: {error.message}")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context, "pin"):
        return
    reply = update.effective_message.reply_to_message
    try:
        if reply:
            await context.bot.unpin_chat_message(update.effective_chat.id, reply.message_id)
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.effective_message.reply_text("📍 MESSAGE UNPINNED")
    except TelegramError as error:
        await update.effective_message.reply_text(f"Unpin nahi hua: {error.message}")

# -------------------------------- Staff -----------------------------------

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE, fixed_rank: Optional[int] = None) -> None:
    if not await require_moderator(update, context):
        return
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.effective_message.reply_text("Sirf owner ya Telegram admin staff promote kar sakta hai.")
        return
    target_id, target_name = await target_user(update, context)
    rank = fixed_rank or parse_int(context.args[1] if len(context.args) > 1 else "1", 1, 1, 3)
    if not target_id:
        await update.effective_message.reply_text("Reply karke /promote1, /promote2 ya /promote3 use karein.")
        return
    db.execute(
        """
        INSERT INTO staff(chat_id, user_id, rank) VALUES (?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET rank=excluded.rank
        """,
        (update.effective_chat.id, target_id, rank),
    )
    descriptions = {
        1: "🥉 Realm Keeper\n• Delete Messages\n• Warn Users",
        2: "🥈 Realm Guardian\n• Delete, Warn, Mute, Pin",
        3: "🥇 Realm Commander\n• Full Admin Access",
    }
    await update.effective_message.reply_text(
        f"👑 STAFF PROMOTED\n\n👤 {html.escape(target_name)}\n{descriptions[rank]}",
        parse_mode=ParseMode.HTML,
    )

async def promote_fixed_rank(update: Update, context: ContextTypes.DEFAULT_TYPE, rank: int) -> None:
    await promote(update, context, fixed_rank=rank)

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    if not await is_user_admin(update.effective_chat.id, update.effective_user.id, context):
        await update.effective_message.reply_text("Sirf owner ya Telegram admin staff demote kar sakta hai.")
        return
    target_id, target_name = await target_user(update, context)
    if not target_id:
        await update.effective_message.reply_text("Reply karke /demote use karein.")
        return
    db.execute("DELETE FROM staff WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target_id))
    await update.effective_message.reply_text(
        f"⬇️ STAFF DEMOTION\n\n👤 {html.escape(target_name)}\n\nRank Removed Successfully.",
        parse_mode=ParseMode.HTML,
    )

# ------------------------------ User Commands ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    await update.effective_message.reply_text(
        "🌌 Welcome To REALMX HELPER\n\n🛡️ Group Management\n💰 Economy\n🎮 Games\n📈 Analytics\n\nChoose Your Destiny Below...",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📚 Help Center", callback_data="help")],
                [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
            ]
        ),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "📚 REALMX HELP CENTER\n\n"
        "🛡️ Moderation: /ban /unban /kick /mute /warn /purge /pin\n"
        "👑 Staff: /promote1 /promote2 /promote3 /demote\n"
        "💰 DM Economy: /bal /daily /checkin /weeklyreward /bank /deposit /withdraw /shop /inventory\n"
        "💸 Group Economy: /give /work /crime /rob /invest /spin /lottery /giveaway\n"
        "🤖 AI & Media: /ai <prompt> /download <link>\n"
        "📈 Analytics: /activity /today /weekly /topusers /groupstats /mystats\n"
        "🎮 Games: /dice /coin /rps /guess /quiz /truth /dare /8ball /tictac\n"
        "⚙️ Settings: /welcome /goodbye /setwelcome /setrules /antispam /antiflood /filter /stopfilter",
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.effective_message.reply_text(f"🆔 USER INFORMATION\n\nUser ID: {user.id}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user(user)
    row = user_row(user.id)
    await update.effective_message.reply_text(
        f"👤 USER INFO\n\nName: {html.escape(user.full_name)}\n"
        f"Username: @{html.escape(user.username) if user.username else 'none'}\n"
        f"User ID: {user.id}\nJoin Date: {row['first_seen'][:10]}",
        parse_mode=ParseMode.HTML,
    )

def profile_text(user_id: int, label: str, chat_id: Optional[int] = None) -> str:
    row = user_row(user_id)
    current_rank = staff_rank(chat_id, user_id) if chat_id is not None else 0
    return (
        f"👑 REALMX PROFILE\n\n👤 {html.escape(label)}\n⭐ Level: {row['level']}\n"
        f"🎖️ Rank: {rank_name(current_rank)}\n\n💰 Coins: {row['coins']}\n"
        f"🏦 Bank: {row['bank']}\n\n💬 Messages: {row['messages']}\n🔥 Streak: {row['streak']}\n\n❤️ Reputation: {row['reputation']}"
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    user = update.effective_user
    await update.effective_message.reply_text(
        profile_text(user.id, display_user(user), update.effective_chat.id),
        parse_mode=ParseMode.HTML,
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🤖 REALMX HELPER\n\n👑 Owner:\n@internationalpanditG\n\n🆔 ID:\n8727799160\n\n📢 Support:\n@realmXsupport"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"🆘 SUPPORT CENTER\n\n📢 Channel:\n{SUPPORT_CHANNEL}\n\n💬 Group:\n{SUPPORT_GROUP}"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    started = time.time()
    message = await update.effective_message.reply_text("🏓 Pinging...")
    elapsed = round((time.time() - started) * 1000)
    await message.edit_text(f"🏓 PONG!\n\n⚡ Speed: {elapsed} ms\n✅ REALMX Online")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    group = db.one("SELECT rules FROM groups WHERE chat_id=?", (update.effective_chat.id,))
    if not group or not group["rules"]:
        await update.effective_message.reply_text("📜 No rules configured.")
        return
    await update.effective_message.reply_text(f"📜 GROUP RULES\n\n{html.escape(group['rules'])}", parse_mode=ParseMode.HTML)

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    reply = update.effective_message.reply_to_message
    if not reply or not reply.from_user:
        await update.effective_message.reply_text("Reply kisi user ke message par karo.")
        return
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    except TelegramError:
        await update.effective_message.reply_text("⚠️ Admin list access nahi ho paaya.")
        return
    reporter = update.effective_user.full_name
    target = reply.from_user.full_name
    for admin in admins:
        try:
            await context.bot.send_message(
                admin.user.id,
                f"🚨 REPORT ALERT\n\nReporter: {reporter}\nTarget: {target}\nGroup: {update.effective_chat.title or update.effective_chat.id}",
            )
        except TelegramError:
            continue
    await update.effective_message.reply_text("✅ Report sent to admins.")

# ------------------------------- AI & Media Features -----------------------

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args).strip()
    if not query:
        await update.effective_message.reply_text("Usage: /ai <aapka sawaal>")
        return
    responses = [
        f"🤖 REALMX AI: Main aapki queries solve kar sakta hoon. Aapne poocha: '{query}'",
        f"🧠 REALMX BRAIN: According to my intelligence, '{query}' ka response tayyar ho raha hai!",
    ]
    await update.effective_message.reply_text(random.choice(responses))

async def downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    link = context.args[0] if context.args else ""
    if not link or ("instagram.com" not in link and "youtube.com" not in link and "youtu.be" not in link):
        await update.effective_message.reply_text("Usage: /download <valid link>")
        return
    await update.effective_message.reply_text("📥 Downloading media... Please wait.")

# ------------------------------- Tag System --------------------------------

async def known_mentions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    admins: bool = False,
    staff: bool = False,
    bots: bool = False,
) -> str:
    chat_id = update.effective_chat.id
    rows = db.all("SELECT u.user_id, u.name, u.username FROM group_users gu JOIN users u ON u.user_id=gu.user_id WHERE gu.chat_id=? LIMIT 500", (chat_id,))
    if admins:
        try:
            members = await context.bot.get_chat_administrators(chat_id)
            allowed = {member.user.id for member in members}
            rows = [row for row in rows if row["user_id"] in allowed]
        except TelegramError:
            rows = []
    if staff:
        rows = db.all("SELECT u.user_id, u.name, u.username FROM staff s JOIN users u ON u.user_id=s.user_id WHERE s.chat_id=?", (chat_id,))
    if bots:
        rows = db.all("SELECT u.user_id, u.name, u.username FROM group_users gu JOIN users u ON u.user_id=gu.user_id WHERE gu.chat_id=? AND u.is_bot=1", (chat_id,))
    if not rows:
        return "Abhi koi known member nahi mila."
    return " ".join(mention(row["user_id"], row["name"]) for row in rows)

async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    text = await known_mentions(update, context)
    await send_long(update, f"📢 TAG SYSTEM\n\n{text}")

async def hidetag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    text = await known_mentions(update, context)
    hidden = text.replace("User", "‌‌")
    await send_long(update, f"📢 Hidden tag sent.\n\n{hidden}")

async def admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    await send_long(update, f"👮 ADMINS\n\n{await known_mentions(update, context, admins=True)}")

async def staff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    await send_long(update, f"👑 STAFF\n\n{await known_mentions(update, context, staff=True)}")

async def tagbots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    await send_long(update, f"🤖 BOTS\n\n{await known_mentions(update, context, bots=True)}")

# ------------------------------- Economy (DM ONLY RESTRUCTURING) -----------------------------------

async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    row = user_row(update.effective_user.id)
    await update.effective_message.reply_text(f"💰 Wallet Balance: {row['coins']}")

async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    row = user_row(update.effective_user.id)
    await update.effective_message.reply_text(f"🏦 BANK ACCOUNT\n\nBalance: {row['bank']}")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    amount = parse_int(context.args[0] if context.args else "", 0, 1, 1_000_000_000)
    row = user_row(update.effective_user.id)
    if not amount or row["coins"] < amount:
        await update.effective_message.reply_text("Valid amount dein aur wallet balance check karein.")
        return
    db.execute("UPDATE users SET coins=coins-?, bank=bank+? WHERE user_id=?", (amount, amount, update.effective_user.id))
    await update.effective_message.reply_text(f"🏦 MONEY DEPOSITED\n\nAmount: {amount}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    amount = parse_int(context.args[0] if context.args else "", 0, 1, 1_000_000_000)
    row = user_row(update.effective_user.id)
    if not amount or row["bank"] < amount:
        await update.effective_message.reply_text("Valid amount dein aur bank balance check karein.")
        return
    db.execute("UPDATE users SET bank=bank-?, coins=coins+? WHERE user_id=?", (amount, amount, update.effective_user.id))
    await update.effective_message.reply_text(f"💸 MONEY WITHDRAWN\n\nAmount: {amount}")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    await update.effective_message.reply_text(
        "🛒 REALMX SHOP\n\n🎁 Items Available\n\n"
        "• Shield — 500 coins\n• Lucky Charm — 750 coins\n• VIP Badge — 1500 coins\n\nPurchase: /buy <item>"
    )

async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    rows = db.all("SELECT item, quantity FROM inventory WHERE user_id=?", (update.effective_user.id,))
    items = "\n".join(f"• {row['item']} x{row['quantity']}" for row in rows) or "No items yet."
    await update.effective_message.reply_text(f"🎒 INVENTORY\n\nItems Owned:\n{items}")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    prices = {"shield": 500, "lucky": 750, "lucky charm": 750, "vip": 1500, "vip badge": 1500}
    item = " ".join(context.args).lower().strip()
    price = prices.get(item)
    if not price:
        await update.effective_message.reply_text("Usage: /buy shield | /buy lucky | /buy vip")
        return
    row = user_row(update.effective_user.id)
    if row["coins"] < price:
        await update.effective_message.reply_text("Aapke paas enough coins nahi hain.")
        return
    canonical = {"lucky charm": "lucky", "vip badge": "vip"}.get(item, item)
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (price, update.effective_user.id))
    db.execute(
        """
        INSERT INTO inventory(user_id, item, quantity) VALUES (?, ?, 1)
        ON CONFLICT(user_id, item) DO UPDATE SET quantity=quantity+1
        """,
        (update.effective_user.id, canonical),
    )
    await update.effective_message.reply_text(f"🛒 PURCHASE COMPLETE\n\nItem: {canonical}\nCost: {price} coins")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    user = update.effective_user
    row = user_row(user.id)
    if row["last_daily"] == today():
        await update.effective_message.reply_text("Aaj ka reward already claim kar chuke ho. Kal phir aana.")
        return
    previous = datetime.now(UTC).date() - timedelta(days=1)
    streak = int(row["daily_streak"]) + 1 if row["last_daily"] == previous.isoformat() else 1
    db.execute(
        "UPDATE users SET coins=coins+500, xp=xp+100, last_daily=?, daily_streak=?, streak=? WHERE user_id=?",
        (today(), streak, streak, user.id),
    )
    await update.effective_message.reply_text(f"🎁 DAILY REWARD\n\n💰 Coins: 500\n⭐ XP: 100\n\n🔥 Streak Updated: {streak}")

async def checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    user_id = update.effective_user.id
    user_row(user_id)
    try:
        db.execute("INSERT INTO checkins(user_id, day, reward) VALUES (?, ?, ?)", (user_id, today(), 250))
    except sqlite3.IntegrityError:
        await update.effective_message.reply_text("✅ Aaj ka check-in already complete hai.")
        return
    db.execute("UPDATE users SET coins=coins+250, xp=xp+25 WHERE user_id=?", (user_id,))
    await update.effective_message.reply_text("✅ CHECK-IN COMPLETE\n\n💰 Reward: 250 coins\n⭐ XP: 25")

async def weeklyreward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    user_id = update.effective_user.id
    user_row(user_id)
    iso = datetime.now(UTC).isocalendar()
    week_key = f"{iso.year}-{iso.week}"
    try:
        db.execute("INSERT INTO weekly_rewards(user_id, week, reward) VALUES (?, ?, ?)", (user_id, week_key, 1500))
    except sqlite3.IntegrityError:
        await update.effective_message.reply_text("✅ Is week ka reward already claim ho chuka hai.")
        return
    db.execute("UPDATE users SET coins=coins+1500, xp=xp+250 WHERE user_id=?", (user_id,))
    await update.effective_message.reply_text("🎁 WEEKLY REWARD\n\n💰 Coins: 1500\n⭐ XP: 250")

# Group Economy Commands
async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not context.args:
        await update.effective_message.reply_text("Usage: /give @username amount ya reply karke /give amount")
        return

    if update.effective_message.reply_to_message:
        target_id, target_name = await target_user(update, context)
        amount_arg = context.args[0]
    else:
        target_id, target_name = await target_user(update, context)
        amount_arg = context.args[1] if len(context.args) > 1 else ""

    amount = parse_int(amount_arg, 0, 1, 1_000_000_000)
    if not target_id or not amount or target_id == user.id:
        await update.effective_message.reply_text("Valid receiver aur amount dein.")
        return

    sender = user_row(user.id)
    if sender["coins"] < amount:
        await update.effective_message.reply_text("Aapke paas itne coins nahi hain.")
        return

    user_row(target_id)
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user.id))
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, target_id))
    await update.effective_message.reply_text(
        f"💸 TRANSFER COMPLETE\n\n👤 Sender: {html.escape(display_user(user))}\n"
        f"👤 Receiver: {html.escape(target_name)}\n\n💰 Amount: {amount}",
        parse_mode=ParseMode.HTML,
    )

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("🎯 DAILY CHALLENGE\n\n💬 Send 100 Messages\n\nReward:\n💰 500 Coins")

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row = user_row(update.effective_user.id)
    await update.effective_message.reply_text(f"🏆 CURRENT RANK\n\n🎖️ Level {row['level']} — {row['xp']} XP")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.all("SELECT name, username, coins FROM users ORDER BY coins DESC LIMIT 10")
    lines = ["🏆 REALMX LEADERBOARD", ""]
    medals = ["🥇", "🥈", "🥉"]
    for index, row in enumerate(rows):
        lines.append(f"{medals[index] if index < 3 else f'{index + 1}.'} {html.escape(row['name'])} — {row['coins']} coins")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ------------------------------- Analytics ---------------------------------

def period_sum(table: str, column: str, where: str, params: tuple[Any, ...]) -> int:
    row = db.one(f"SELECT COALESCE(SUM({column}), 0) AS n FROM {table} WHERE {where}", params)
    return int(row["n"]) if row else 0

async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    count = period_sum("chat_stats", "messages", "chat_id=? AND day=?", (chat_id, today()))
    users = db.one("SELECT COUNT(*) AS n FROM group_users WHERE chat_id=?", (chat_id,))["n"]
    await update.effective_message.reply_text(f"📈 REALMX ANALYTICS\n\n💬 Messages Today: {count}\n👥 Active Users: {users}")

async def today_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    count = period_sum("chat_stats", "messages", "chat_id=? AND day=?", (chat_id, today()))
    await update.effective_message.reply_text(f"📅 TODAY REPORT\n\nMessages Sent Today:\n{count}")

async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    start = (datetime.now(UTC).date() - timedelta(days=6)).isoformat()
    end = today()
    count = period_sum("chat_stats", "messages", "chat_id=? AND day BETWEEN ? AND ?", (update.effective_chat.id, start, end))
    await update.effective_message.reply_text(f"📆 WEEKLY REPORT\n\nMessages This Week:\n{count}")

async def topusers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.all(
        """
        SELECT u.name, SUM(us.messages) AS messages FROM user_stats us
        JOIN users u ON u.user_id=us.user_id
        WHERE us.day >= ? GROUP BY us.user_id ORDER BY messages DESC LIMIT 3
        """,
        ((datetime.now(UTC).date() - timedelta(days=6)).isoformat(),),
    )
    lines = ["🥇 TOP CHATTERS", ""]
    for index, row in enumerate(rows, 1):
        lines.append(f"{index}️⃣ {html.escape(row['name'])} — {row['messages']}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def groupstats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    group = db.one("SELECT * FROM groups WHERE chat_id=?", (update.effective_chat.id,))
    members = db.one("SELECT COUNT(*) AS n FROM group_users WHERE chat_id=?", (update.effective_chat.id,))["n"]
    await update.effective_message.reply_text(
        f"📊 GROUP STATISTICS\n\nMembers: {members}\nMessages: {group['messages'] if group else 0}"
    )

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    row = user_row(update.effective_user.id)
    await update.effective_message.reply_text(f"📈 PERSONAL STATS\n\nMessages: {row['messages']}\nLevel: {row['level']}\nXP: {row['xp']}")

# ------------------------- Realm Expansion Commands ------------------------

async def marry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_id, target_name = await target_user(update, context)
    user_id = update.effective_user.id
    if not target_id or target_id == user_id:
        await update.effective_message.reply_text("Jis user se marry karna hai uske message ko reply karke /marry use karo.")
        return
    if db.one("SELECT user_id FROM marriages WHERE user_id IN (?, ?)", (user_id, target_id)):
        await update.effective_message.reply_text("In dono me se koi already married hai.")
        return
    db.execute("INSERT INTO marriages(user_id, partner_id, married_at) VALUES (?, ?, ?)", (user_id, target_id, now_iso()))
    db.execute("INSERT INTO marriages(user_id, partner_id, married_at) VALUES (?, ?, ?)", (target_id, user_id, now_iso()))
    await update.effective_message.reply_text(f"💍 CONGRATULATIONS\n\n{html.escape(display_user(update.effective_user))} and {html.escape(target_name)} are now married!")

async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    marriage = db.one("SELECT partner_id FROM marriages WHERE user_id=?", (user_id,))
    if not marriage:
        await update.effective_message.reply_text("Aap married nahi ho.")
        return
    db.execute("DELETE FROM marriages WHERE user_id IN (?, ?)", (user_id, marriage["partner_id"]))
    await update.effective_message.reply_text("💔 DIVORCE COMPLETE\n\nMarriage record removed.")

async def rep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_id, target_name = await target_user(update, context)
    if not target_id or target_id == update.effective_user.id:
        await update.effective_message.reply_text("Reputation dene ke liye kisi user ke message ko reply karo.")
        return
    user_row(target_id)
    db.execute("UPDATE users SET reputation=reputation+1 WHERE user_id=?", (target_id,))
    await update.effective_message.reply_text(f"❤️ Reputation +1\n\n{html.escape(target_name)} ko reputation di gayi.")

async def toprep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = db.all("SELECT name, username, reputation FROM users ORDER BY reputation DESC LIMIT 10")
    lines = ["❤️ TOP REPUTATION", ""]
    for index, row in enumerate(rows, 1):
        lines.append(f"{index}. {html.escape(row['name'])} — {row['reputation']}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_row(user_id)
    last = db.one("SELECT last_work FROM work_claims WHERE user_id=?", (user_id,))
    if last and time.time() - datetime.fromisoformat(last["last_work"]).timestamp() < 3600:
        await update.effective_message.reply_text("⏳ Work cooldown active hai. Ek ghante baad phir try karo.")
        return
    reward = random.randint(100, 350)
    db.execute(
        """
        INSERT INTO work_claims(user_id, last_work) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_work=excluded.last_work
        """,
        (user_id, now_iso()),
    )
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (reward, user_id))
    await update.effective_message.reply_text(f"💼 WORK COMPLETE\n\n💰 You earned {reward} coins.")

async def crime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    row = user_row(user_id)
    last = db.one("SELECT last_crime FROM crime_claims WHERE user_id=?", (user_id,))
    if last and time.time() - datetime.fromisoformat(last["last_crime"]).timestamp() < 1800:
        await update.effective_message.reply_text("⏳ Crime cooldown 30 minutes ka hai.")
        return
    db.execute(
        """
        INSERT INTO crime_claims(user_id, last_crime) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET last_crime=excluded.last_crime
        """,
        (user_id, now_iso()),
    )
    if random.random() < 0.6:
        reward = random.randint(150, 600)
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (reward, user_id))
        await update.effective_message.reply_text(f"🕶️ CRIME SUCCESSFUL\n\n💰 Loot: {reward} coins")
    else:
        fine = min(row["coins"], random.randint(50, 200))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (fine, user_id))
        await update.effective_message.reply_text(f"🚔 CAUGHT BY THE REALM\n\n💸 Fine: {fine} coins")

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_id, target_name = await target_user(update, context)
    user_id = update.effective_user.id
    if not target_id or target_id == user_id:
        await update.effective_message.reply_text("Target ke message ko reply karke /rob use karo.")
        return
    target = user_row(target_id)
    if random.random() < 0.45 and target["coins"] > 0:
        amount = min(target["coins"], random.randint(50, 300))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, target_id))
        result = f"💰 Loot: {amount} coins"
    else:
        fine = min(user_row(user_id)["coins"], random.randint(25, 150))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (fine, user_id))
        result = f"💸 Failed. Fine: {fine} coins"
    await update.effective_message.reply_text(f"🥷 ROB ATTEMPT\n\nTarget: {html.escape(target_name)}\n\n{result}", parse_mode=ParseMode.HTML)

async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    row = user_row(user_id)
    if context.args and context.args[0].lower() == "collect":
        old = db.one("SELECT amount, invested_at FROM investments WHERE user_id=?", (user_id,))
        if not old:
            await update.effective_message.reply_text("Koi active investment nahi hai.")
            return
        invested_at = datetime.fromisoformat(old["invested_at"])
        if datetime.now(UTC) - invested_at < timedelta(hours=24):
            await update.effective_message.reply_text("Investment 24 hours baad mature hoga.")
            return
        amount = int(old["amount"])
        profit = round(amount * 0.25)
        db.execute("DELETE FROM investments WHERE user_id=?", (user_id,))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount + profit, user_id))
        await update.effective_message.reply_text(f"📈 INVESTMENT COLLECTED\n\n💰 Principal: {amount}\n📊 Profit: {profit}\nTotal returned: {amount + profit}")
        return
    amount = parse_int(context.args[0] if context.args else "", 0, 100, 1_000_000_000)
    if not amount or row["coins"] < amount:
        await update.effective_message.reply_text("Usage: /invest <amount> — minimum 100 coins.")
        return
    old = db.one("SELECT amount FROM investments WHERE user_id=?", (user_id,))
    if old:
        await update.effective_message.reply_text("Pehle existing investment withdraw karo ya mature hone do.")
        return
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
    db.execute("INSERT INTO investments(user_id, amount, invested_at) VALUES (?, ?, ?)", (user_id, amount, now_iso()))
    await update.effective_message.reply_text(f"📈 INVESTMENT CREATED\n\n💰 Invested: {amount} coins\nReturn: /invest collect (24 hours ke baad)")

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    row = user_row(user_id)
    cost = 50
    if row["coins"] < cost:
        await update.effective_message.reply_text("🎰 Spin ke liye 50 coins chahiye.")
        return
    reward = random.choice([0, 25, 50, 100, 250, 500])
    db.execute("UPDATE users SET coins=coins-?+? WHERE user_id=?", (cost, reward, user_id))
    await update.effective_message.reply_text(f"🎰 SPIN RESULT\n\n💸 Cost: {cost}\n💰 Prize: {reward} coins")

async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    amount = parse_int(context.args[0] if context.args else "100", 100, 100, 100)
    row = user_row(user_id)
    if row["coins"] < amount:
        await update.effective_message.reply_text("🎟️ Lottery ticket ke liye 100 coins chahiye.")
        return
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
    db.execute("INSERT INTO lottery_entries(user_id, amount, created_at) VALUES (?, ?, ?)", (user_id, amount, now_iso()))
    entries = db.all("SELECT id, user_id, amount FROM lottery_entries")
    if len(entries) < 5:
        await update.effective_message.reply_text(f"🎟️ LOTTERY ENTRY ADDED\n\nPlayers: {len(entries)}/5\nPrize draw 5 entries par hoga.")
        return
    winner = random.choice(entries)
    prize = sum(int(entry["amount"]) for entry in entries)
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (prize, winner["user_id"]))
    db.execute("DELETE FROM lottery_entries")
    await update.effective_message.reply_text(f"🎉 LOTTERY WINNER\n\nWinner ID: {winner['user_id']}\n💰 Prize: {prize} coins")

async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    amount = parse_int(context.args[0] if context.args else "100", 100, 1, 1_000_000)
    members = db.all("SELECT u.user_id, u.name FROM group_users gu JOIN users u ON u.user_id=gu.user_id WHERE gu.chat_id=? AND u.is_bot=0", (update.effective_chat.id,))
    if not members:
        await update.effective_message.reply_text("Giveaway ke liye known members nahi mile.")
        return
    winner = random.choice(members)
    user_row(winner["user_id"])
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, winner["user_id"]))
    await update.effective_message.reply_text(f"🎁 GIVEAWAY WINNER\n\n{mention(winner['user_id'], winner['name'])}\n💰 Prize: {amount} coins", parse_mode=ParseMode.HTML)

async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reason = " ".join(context.args).strip() or "AFK"
    db.execute(
        """
        INSERT INTO afk(user_id, reason, since) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason, since=excluded.since
        """,
        (update.effective_user.id, reason, now_iso()),
    )
    await update.effective_message.reply_text(f"💤 AFK enabled: {reason}")

async def snipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    row = db.one("SELECT * FROM snipes WHERE chat_id=?", (update.effective_chat.id,))
    if not row:
        await update.effective_message.reply_text("👀 No deleted message recorded.")
        return
    await update.effective_message.reply_text(f"👀 SNIPE\n\n{html.escape(row['name'])}: {html.escape(row['text'])}", parse_mode=ParseMode.HTML)

async def editsnipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    row = db.one("SELECT * FROM edit_snipes WHERE chat_id=?", (update.effective_chat.id,))
    if not row:
        await update.effective_message.reply_text("✏️ No edited message recorded.")
        return
    await update.effective_message.reply_text(
        f"✏️ EDIT SNIPE\n\nBefore: {html.escape(row['old_text'])}\nAfter: {html.escape(row['new_text'])}",
        parse_mode=ParseMode.HTML,
    )

async def inactive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    days = parse_int(context.args[0] if context.args else "7", 7, 1, 365)
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")
    rows = db.all(
        """
        SELECT u.name FROM group_users gu JOIN users u ON u.user_id=gu.user_id
        WHERE gu.chat_id=? AND gu.last_seen < ? AND u.is_bot=0 LIMIT 50
        """,
        (update.effective_chat.id, cutoff),
    )
    names = "\n".join(f"• {html.escape(row['name'])}" for row in rows) or "No inactive members found."
    await update.effective_message.reply_text(f"💤 INACTIVE MEMBERS ({days}+ days)\n\n{names}", parse_mode=ParseMode.HTML)

async def topactive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_group(update):
        return
    start = (datetime.now(UTC).date() - timedelta(days=6)).isoformat()
    rows = db.all(
        """
        SELECT u.name, SUM(us.messages) AS messages FROM user_stats us
        JOIN users u ON u.user_id=us.user_id
        JOIN group_users gu ON gu.user_id=us.user_id
        WHERE gu.chat_id=? AND us.day>=? GROUP BY us.user_id
        ORDER BY messages DESC LIMIT 10
        """,
        (update.effective_chat.id, start),
    )
    lines = ["🔥 TOP ACTIVE", ""]
    lines.extend(f"{index}. {html.escape(row['name'])} — {row['messages']} messages" for index, row in enumerate(rows, 1))
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def chatstats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await groupstats(update, context)

async def profilecard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    user = update.effective_user
    await update.effective_message.reply_text(
        "╔════ REALMX PROFILE CARD ════╗\n\n"
        + profile_text(user.id, display_user(user), update.effective_chat.id)
        + "\n\n╚══════════════════════════════╝",
        parse_mode=ParseMode.HTML,
    )

async def rankcard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_dm(update):
        return
    row = user_row(update.effective_user.id)
    await update.effective_message.reply_text(
        f"🏆 REALMX RANK CARD\n\n👤 {html.escape(display_user(update.effective_user))}\n"
        f"🎖️ Level: {row['level']}\n⭐ XP: {row['xp']}\n📊 Messages: {row['messages']}",
        parse_mode=ParseMode.HTML,
    )

# --------------------------------- Games -----------------------------------

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"🎲 Dice Rolled:\n{random.randint(1, 6)}")

async def coin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"🪙 Coin Toss\n\nResult:\n{random.choice(['Heads', 'Tails'])}")

async def rps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    choice = context.args[0].lower() if context.args else ""
    choices = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    if choice not in choices:
        await update.effective_message.reply_text("Usage: /rps rock, /rps paper ya /rps scissors")
        return
    bot_choice = random.choice(list(choices))
    winner = "Tie!" if choice == bot_choice else (
        "You win!" if (choice, bot_choice) in {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")} else "Bot wins!"
    )
    await update.effective_message.reply_text(f"🎮 ROCK PAPER SCISSORS\n\n👤 You: {choice}\n🤖 Bot: {bot_choice}\n\n🏆 {winner}")

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    secret = context.user_data.get("guess_number")
    if secret is None or not context.args:
        context.user_data["guess_number"] = random.randint(1, 10)
        await update.effective_message.reply_text("🎯 Guess The Number\n\n1 se 10 ke beech number guess karo. /guess <number>")
        return
    guess_value = parse_int(context.args[0], 0, 1, 10)
    if guess_value == secret:
        context.user_data.pop("guess_number", None)
        await update.effective_message.reply_text("🎯 Correct guess! Realm reward: 100 coins.")
        db.execute("UPDATE users SET coins=coins+100 WHERE user_id=?", (update.effective_user.id,))
    else:
        await update.effective_message.reply_text("Too high." if guess_value > secret else "Too low.")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("🧠 Quiz Started\n\nQuestion: Telegram bot ka brain kis cheez se chalta hai?\nA) Code  B) Magic\nAnswer reply mein bhejo.")

async def truth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"😳 Truth Question Generated\n\n{random.choice(['Aapka sabse bada goal kya hai?', 'Aapne recently kya seekha?', 'Aapka hidden talent kya hai?'])}")

async def dare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"🔥 Dare Generated\n\n{random.choice(['Group mein ek positive message bhejo.', 'Apni profile photo 10 minutes ke liye change karo.', 'Kisi member ko genuine compliment do.'])}")

async def eight_ball(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"🎱 Magic Answer:\n{random.choice(['Absolutely yes.', 'Ask again later.', 'Definitely not.', 'The realm says yes.', 'It is uncertain.'])}")

async def tictac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("❌⭕ TIC TAC TOE\n\nPlayer 1: ❌\nPlayer 2: ⭕\n\nGame Started.\nBoard moves ko reply mein bhejein.")

# -------------------------- Settings & Automod -----------------------------

async def toggle_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    command = update.effective_message.text.split()[0].lstrip("/").split("@")[0]
    value = 0 if setting(update.effective_chat.id, command) else 1
    db.execute(f"UPDATE groups SET {command}=? WHERE chat_id=?", (value, update.effective_chat.id))
    labels = {
        "antispam": "spam protection",
        "antiflood": "flood protection",
        "antiraid": "raid protection",
        "captcha": "captcha verification",
    }
    await update.effective_message.reply_text(f"✅ {labels.get(command, command)} {'enabled' if value else 'disabled'}.")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    db.execute("UPDATE groups SET welcome_enabled=1 WHERE chat_id=?", (update.effective_chat.id,))
    await update.effective_message.reply_text("🌌 Welcome Messages Enabled")

async def goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    db.execute("UPDATE groups SET goodbye_enabled=1 WHERE chat_id=?", (update.effective_chat.id,))
    await update.effective_message.reply_text("👋 Goodbye Messages Enabled")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Usage: /setwelcome Welcome {user} to {group}")
        return
    db.execute("UPDATE groups SET welcome_text=? WHERE chat_id=?", (text, update.effective_chat.id))
    await update.effective_message.reply_text("Custom welcome configured.")

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Usage: /setrules <rules>")
        return
    db.execute("UPDATE groups SET rules=? WHERE chat_id=?", (text, update.effective_chat.id))
    await update.effective_message.reply_text("📜 Group Rules Updated")

async def blocklist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    group = db.one("SELECT blocklist FROM groups WHERE chat_id=?", (update.effective_chat.id,))
    words = json.loads(group["blocklist"] if group else "[]")
    if not context.args:
        await update.effective_message.reply_text("Blocked words: " + (", ".join(words) or "none"))
        return
    action = context.args[0].lower()
    if action == "remove" and len(context.args) > 1:
        words = [word for word in words if word != context.args[1].lower()]
    else:
        for word in context.args:
            if word.lower() not in words:
                words.append(word.lower())
    db.execute("UPDATE groups SET blocklist=? WHERE chat_id=?", (json.dumps(words), update.effective_chat.id))
    await update.effective_message.reply_text("✅ Blocklist updated: " + (", ".join(words) or "empty"))

async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /filter <keyword> <reply message>")
        return
    keyword = context.args[0].lower()
    reply = " ".join(context.args[1:])
    db.execute(
        """
        INSERT INTO filters(chat_id, keyword, reply_text) VALUES (?, ?, ?)
        ON CONFLICT(chat_id, keyword) DO UPDATE SET reply_text=excluded.reply_text
        """,
        (update.effective_chat.id, keyword, reply)
    )
    await update.effective_message.reply_text(f"✅ Filter created for keyword: '{keyword}'")

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_moderator(update, context):
        return
    if not context.args:
        await update.effective_message.reply_text("Usage: /stopfilter <keyword>")
        return
    keyword = context.args[0].lower()
    db.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (update.effective_chat.id, keyword))
    await update.effective_message.reply_text(f"✅ Filter removed for keyword: '{keyword}'")

# ------------------------------- Events ------------------------------------

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not message or not user or not chat:
        return
    ensure_user(user)
    if chat.type in ("group", "supergroup"):
        ensure_group(chat)
        record_message(chat.id, user.id)
        text = (message.text or message.caption or "").lower()
        message_cache[(chat.id, message.message_id)] = text

        # Captcha verification handling
        if (chat.id, user.id) in captcha_storage:
            try:
                ans = int(text)
                if ans == captcha_storage[(chat.id, user.id)]:
                    del captcha_storage[(chat.id, user.id)]
                    await message.reply_text("✅ Captcha verified! Welcome.")
                    return
            except ValueError:
                pass

        # Filter handling
        saved_filter = db.one("SELECT reply_text FROM filters WHERE chat_id=? AND keyword=?", (chat.id, text))
        if saved_filter:
            await message.reply_text(saved_filter["reply_text"])
            return

        old_afk = db.one("SELECT reason FROM afk WHERE user_id=?", (user.id,))
        if old_afk:
            db.execute("DELETE FROM afk WHERE user_id=?", (user.id,))
            await message.reply_text("👋 Welcome back! AFK status removed.")
        group = db.one("SELECT * FROM groups WHERE chat_id=?", (chat.id,))
        if group:
            blocked = json.loads(group["blocklist"] or "[]")
            if blocked and any(word in text.split() for word in blocked):
                if await safe_delete(context, chat.id, message.message_id, message):
                    await context.bot.send_message(chat.id, "🚫 Message removed: blocked word.")
                return
            key = (chat.id, user.id)
            current = time.time()
            recent_messages[key].append(current)
            if group["antiflood"] and len([t for t in recent_messages[key] if current - t < 8]) >= 8:
                try:
                    await context.bot.restrict_chat_member(
                        chat.id, user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=datetime.now(UTC) + timedelta(minutes=1),
                    )
                    await message.reply_text("🛡️ Flood protection: user muted for 1 minute.")
                except TelegramError:
                    pass
            previous_text, previous_time = recent_text.get(key, ("", 0))
            if group["antispam"] and text and text == previous_text and current - previous_time < 20:
                await safe_delete(context, chat.id, message.message_id, message)
            recent_text[key] = (text, current)

async def on_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user or chat.type not in ("group", "supergroup"):
        return
    new_text = message.text or message.caption or ""
    old_text = message_cache.get((chat.id, message.message_id), "")
    if old_text and old_text != new_text.lower():
        db.execute(
            """
            INSERT INTO edit_snipes(chat_id, user_id, name, old_text, new_text, edited_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET user_id=excluded.user_id,
            name=excluded.name, old_text=excluded.old_text, new_text=excluded.new_text,
            edited_at=excluded.edited_at
            """,
            (chat.id, user.id, user.full_name or "User", old_text, new_text, now_iso()),
        )
    message_cache[(chat.id, message.message_id)] = new_text.lower()

async def on_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not update.effective_chat:
        return
    ensure_group(update.effective_chat)
    for user in message.new_chat_members or []:
        ensure_user(user)
        db.execute(
            "INSERT OR IGNORE INTO group_users(chat_id, user_id, last_seen) VALUES (?, ?, ?)",
            (update.effective_chat.id, user.id, now_iso()),
        )
        if setting(update.effective_chat.id, "captcha"):
            num1, num2 = random.randint(1, 9), random.randint(1, 9)
            captcha_storage[(update.effective_chat.id, user.id)] = num1 + num2
            await message.reply_text(f"🛡️ CAPTCHA: {mention(user.id, user.full_name)} Solve: {num1} + {num2} = ?", parse_mode=ParseMode.HTML)
            continue

        if setting(update.effective_chat.id, "welcome_enabled"):
            group = db.one("SELECT * FROM groups WHERE chat_id=?", (update.effective_chat.id,))
            custom = group["welcome_text"] if group else ""
            text = custom or "🌌 Welcome {user} to {group}!"
            text = text.replace("{user}", mention(user.id, display_user(user))).replace(
                "{group}", html.escape(update.effective_chat.title or "the realm")
            )
            await message.reply_text(text, parse_mode=ParseMode.HTML)

async def on_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.left_chat_member or not is_group(update):
        return
    if setting(update.effective_chat.id, "goodbye_enabled"):
        await message.reply_text(
            f"👋 Goodbye {html.escape(display_user(message.left_chat_member))}",
            parse_mode=ParseMode.HTML,
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await query.message.reply_text("📚 REALMX HELP CENTER\n\nUse /help for complete command list.")
    elif query.data == "stats":
        await stats(update, context)
    elif query.data == "profile":
        await query.message.reply_text(
            profile_text(query.from_user.id, display_user(query.from_user), query.message.chat_id),
            parse_mode=ParseMode.HTML,
        )

# ---------------------------- Command Registry ----------------------------

def register_commands(application: Application) -> None:
    command_map: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {
        "panel": panel, "broadcast": broadcast, "gcast": gcast, "stats": stats,
        "restart": restart, "backup": backup,
        "ban": ban, "unban": unban, "kick": kick, "mute": mute, "unmute": unmute,
        "warn": warn, "unwarn": unwarn, "purge": purge, "pin": pin, "unpin": unpin,
        "promote1": lambda u, c: promote_fixed_rank(u, c, 1),
        "promote2": lambda u, c: promote_fixed_rank(u, c, 2),
        "promote3": lambda u, c: promote_fixed_rank(u, c, 3),
        "demote": demote,
        "start": start, "help": help_command, "id": id_command, "info": info,
        "profile": profile, "about": about, "support": support, "ping": ping,
        "rules": rules, "report": report,
        "all": tag_command, "tagall": tag_command, "hidetag": hidetag,
        "admins": admins, "staff": staff, "tagadmins": tagadmins,
        "tagstaff": tagstaff, "tagbots": tagbots,
        "bal": bal, "daily": daily, "give": transfer, "pay": transfer,
        "bank": bank, "deposit": deposit, "withdraw": withdraw, "shop": shop,
        "inventory": inventory, "buy": buy, "challenge": challenge, "rank": rank,
        "leaderboard": leaderboard, "activity": activity, "today": today_report,
        "weekly": weekly, "topusers": topusers, "groupstats": groupstats,
        "mystats": mystats, "dice": dice, "coin": coin, "rps": rps, "guess": guess,
        "quiz": quiz, "truth": truth, "dare": dare, "8ball": eight_ball,
        "tictac": tictac, "antispam": toggle_setting, "antiflood": toggle_setting,
        "antiraid": toggle_setting, "captcha": toggle_setting, "blocklist": blocklist,
        "welcome": welcome, "goodbye": goodbye, "setwelcome": setwelcome,
        "setrules": setrules, "checkin": checkin, "weeklyreward": weeklyreward,
        "marry": marry, "divorce": divorce, "rep": rep, "toprep": toprep,
        "work": work, "crime": crime, "rob": rob, "invest": invest, "spin": spin,
        "lottery": lottery, "giveaway": giveaway, "afk": afk, "snipe": snipe,
        "editsnipe": editsnipe, "inactive": inactive, "topactive": topactive,
        "chatstats": chatstats, "profilecard": profilecard, "rankcard": rankcard,
        "ai": ai_chat, "download": downloader, "filter": set_filter, "stopfilter": stop_filter,
    }
    for command, handler in command_map.items():
        application.add_handler(CommandHandler(command, handler))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_left_member))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, on_edited_message))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_message))

async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Start Bot"),
            BotCommand("help", "Help Menu"),
            BotCommand("profile", "Profile (DM Only)"),
            BotCommand("bal", "Balance (DM Only)"),
            BotCommand("daily", "Daily Reward (DM Only)"),
            BotCommand("ai", "Ask AI"),
        ]
    )
    log.info("REALMX HELPER is online")

def main() -> None:
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    register_commands(application)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()

