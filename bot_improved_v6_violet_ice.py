import os
import json
import time
import hmac
import html
import sqlite3
import hashlib
import logging
import mimetypes
import secrets
import threading
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse

import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MINIAPP_DIR = BASE_DIR / "miniapp"

LOCAL_CONFIG = {
    "BOT_TOKEN": "PASTE_YOUR_BOT_TOKEN_HERE",
    "PUBLIC_BASE_URL": "",
    "MINI_APP_URL": "",
    "ADMIN_MINI_APP_URL": "",
    "WEB_HOST": "0.0.0.0",
    "WEB_PORT": 8080,
    "PORT": "",
    "DB_PATH": str(BASE_DIR / "shokerefund.db"),
    "CHANNEL_USERNAME": "@shokerefund",
    "CHANNEL_URL": "",
    "REVIEWS_URL": "https://t.me/shokerefund_reviews",
    "AGREEMENT_URL": "https://telegra.ph/Polzovatelskoe-soglashenie-ShokeRefund-Servisa-pomoshchi-v-oformlenii-vozvratov-za-nekachestvennuyu-dostavku-edy-04-05",
    "ADMIN_CHAT_ID": 0,
    "MAIN_ADMIN_ID": 0,
    "ADMIN_IDS": {"123456789": "Главный админ"},
    "MAX_TICKETS_PER_DAY": 3,
    "COMMISSION": 0.25,
    "PROMO_BUFF_PERCENT": 0.05,
    "PROMO_BUFF_MAX_USES": 100,
    "SEND_STARTUP_MESSAGE": False,
    "DEV_ALLOW_UNSAFE_INITDATA": False,
    "INITDATA_MAX_AGE": 86400,
    "SESSION_TTL_DAYS": 30,
    "PASSWORD_RESET_ALLOWED": True,
    "TEST_MODE": False,
    "SKIP_SUBSCRIPTION_CHECK": False,
}

PAYMENT_METHODS = {
    "lolz": "LOLZ",
    "stars": "Telegram Stars",
    "cryptobot": "CryptoBot",
}
PROMO_CODE = "BUFF"
USER_ACTIVE_STATUSES = {"new", "in_progress", "waiting_user", "awaiting_payment", "payment_review"}


def _raw_cfg(name: str, default=None):
    env_val = os.getenv(name)
    if env_val is not None and env_val != "":
        return env_val
    return LOCAL_CONFIG.get(name, default)


def _cfg_text(name: str, default: str = "") -> str:
    raw = _raw_cfg(name, default)
    return "" if raw is None else str(raw)


def _cfg_int(name: str, default: int = 0) -> int:
    try:
        return int(_raw_cfg(name, default))
    except Exception:
        return default


def _cfg_float(name: str, default: float = 0.0) -> float:
    try:
        return float(_raw_cfg(name, default))
    except Exception:
        return default


def _cfg_bool(name: str, default: bool = False) -> bool:
    raw = _raw_cfg(name, default)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "y", "да"}


BOT_TOKEN = _cfg_text("BOT_TOKEN", "")
if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
    raise RuntimeError('Не задан BOT_TOKEN. Впиши токен в LOCAL_CONFIG["BOT_TOKEN"] или передай переменную окружения BOT_TOKEN.')

PUBLIC_BASE_URL = _cfg_text("PUBLIC_BASE_URL", "").rstrip("/")
WEB_HOST = _cfg_text("WEB_HOST", "0.0.0.0")
WEB_PORT = _cfg_int("PORT", _cfg_int("WEB_PORT", 8080))
DB_PATH = _cfg_text("DB_PATH", str(BASE_DIR / "shokerefund.db"))
UPLOAD_ROOT = Path(DB_PATH).expanduser().resolve().parent / "uploads"
CHANNEL_USERNAME = _cfg_text("CHANNEL_USERNAME", "@shokerefund")
CHANNEL_URL = _cfg_text("CHANNEL_URL", "") or f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
REVIEWS_URL = _cfg_text("REVIEWS_URL", "https://t.me/shokerefund_reviews")
AGREEMENT_URL = _cfg_text("AGREEMENT_URL", "https://telegra.ph/Polzovatelskoe-soglashenie-ShokeRefund-Servisa-pomoshchi-v-oformlenii-vozvratov-za-nekachestvennuyu-dostavku-edy-04-05")
ADMIN_CHAT_ID = _cfg_int("ADMIN_CHAT_ID", 0)
MAIN_ADMIN_ID = _cfg_int("MAIN_ADMIN_ID", 0)
MAX_TICKETS_PER_DAY = _cfg_int("MAX_TICKETS_PER_DAY", 3)
COMMISSION = _cfg_float("COMMISSION", 0.25)
PROMO_BUFF_PERCENT = _cfg_float("PROMO_BUFF_PERCENT", 0.05)
PROMO_BUFF_MAX_USES = _cfg_int("PROMO_BUFF_MAX_USES", 100)
SEND_STARTUP_MESSAGE = _cfg_bool("SEND_STARTUP_MESSAGE", False)
DEV_ALLOW_UNSAFE_INITDATA = _cfg_bool("DEV_ALLOW_UNSAFE_INITDATA", False)
INITDATA_MAX_AGE = _cfg_int("INITDATA_MAX_AGE", 86400)
SESSION_TTL_DAYS = _cfg_int("SESSION_TTL_DAYS", 30)
PASSWORD_RESET_ALLOWED = _cfg_bool("PASSWORD_RESET_ALLOWED", True)
TEST_MODE = _cfg_bool("TEST_MODE", False)
SKIP_SUBSCRIPTION_CHECK = _cfg_bool("SKIP_SUBSCRIPTION_CHECK", False)

try:
    raw_admins = os.getenv("ADMIN_IDS_JSON")
    parsed_admins = json.loads(raw_admins) if raw_admins else LOCAL_CONFIG.get("ADMIN_IDS", {})
except Exception:
    parsed_admins = LOCAL_CONFIG.get("ADMIN_IDS", {})
ADMIN_IDS = {int(k): str(v) for k, v in parsed_admins.items()}
if MAIN_ADMIN_ID and MAIN_ADMIN_ID not in ADMIN_IDS:
    ADMIN_IDS[MAIN_ADMIN_ID] = "Главный админ"

MINI_APP_URL = _cfg_text("MINI_APP_URL", "").strip()
ADMIN_MINI_APP_URL = _cfg_text("ADMIN_MINI_APP_URL", "").strip()
if PUBLIC_BASE_URL:
    MINI_APP_URL = MINI_APP_URL or f"{PUBLIC_BASE_URL}/"
    ADMIN_MINI_APP_URL = ADMIN_MINI_APP_URL or f"{PUBLIC_BASE_URL}/?mode=admin"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(BASE_DIR / "bot.log", encoding="utf-8")],
)
log = logging.getLogger("shokerefund")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# ----------------------------
# Utility helpers
# ----------------------------

def now_ts() -> float:
    return time.time()


def h(text: Any) -> str:
    return html.escape(str(text or ""))


def full_name_from_user(user_obj: Any) -> str:
    if not user_obj:
        return ""
    if isinstance(user_obj, dict):
        first = user_obj.get("first_name")
        last = user_obj.get("last_name")
    else:
        first = getattr(user_obj, "first_name", None)
        last = getattr(user_obj, "last_name", None)
    return " ".join([part for part in [first, last] if part]).strip()


def format_dt(ts: Optional[float]) -> str:
    if not ts:
        return "—"
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(float(ts)))


def format_money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS or (MAIN_ADMIN_ID and int(user_id) == MAIN_ADMIN_ID)


def admin_name(admin_id: Optional[int]) -> Optional[str]:
    if not admin_id:
        return None
    admin_id = int(admin_id)
    return ADMIN_IDS.get(admin_id, f"Админ {admin_id}")


def status_label(status: str) -> str:
    mapping = {
        "new": "Новая",
        "in_progress": "В работе",
        "waiting_user": "Ждёт пользователя",
        "awaiting_payment": "Ожидает оплату",
        "payment_review": "Проверка оплаты",
        "closed": "Закрыта",
        "rejected": "Отклонена",
    }
    return mapping.get(status, status or "—")


def payment_status_label(status: str) -> str:
    mapping = {
        "none": "Не выставлен",
        "invoice_sent": "Счёт выставлен",
        "check_requested": "Запрошена проверка",
        "paid": "Оплачено",
        "rejected": "Не подтверждено",
    }
    return mapping.get(status or "none", status or "—")


def user_main_kb(user_id: Optional[int] = None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if MINI_APP_URL:
        kb.add(types.KeyboardButton("🖥 Открыть кабинет", web_app=types.WebAppInfo(MINI_APP_URL)))
    else:
        kb.add(types.KeyboardButton("🖥 Открыть кабинет"))
    if user_id and is_admin(user_id) and ADMIN_MINI_APP_URL:
        kb.add(types.KeyboardButton("🧿 Открыть админку", web_app=types.WebAppInfo(ADMIN_MINI_APP_URL)))
    return kb


def user_inline_open():
    if not MINI_APP_URL:
        return None
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Открыть кабинет", web_app=types.WebAppInfo(MINI_APP_URL)))
    return kb


def admin_inline_open():
    if not ADMIN_MINI_APP_URL:
        return None
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Открыть админку", web_app=types.WebAppInfo(ADMIN_MINI_APP_URL)))
    return kb


# ----------------------------
# DB
# ----------------------------

def db() -> sqlite3.Connection:
    db_file = Path(DB_PATH).expanduser()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    conn = db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            cabinet_login TEXT UNIQUE,
            password_hash TEXT,
            password_salt TEXT,
            password_updated_at REAL,
            last_login_at REAL,
            buff_used_at REAL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            assigned_admin INTEGER,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            closed_at REAL,
            invoice_amount REAL NOT NULL DEFAULT 0,
            invoice_note TEXT,
            payment_method TEXT,
            payment_status TEXT NOT NULL DEFAULT 'none',
            promo_code TEXT,
            promo_discount REAL NOT NULL DEFAULT 0,
            promo_applied INTEGER NOT NULL DEFAULT 0,
            payment_check_requested_at REAL,
            payment_verified_at REAL,
            payment_provider_ref TEXT,
            payment_note TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            sender_role TEXT NOT NULL,
            sender_id INTEGER,
            sender_name TEXT,
            text TEXT NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            user_agent TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ticket_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS payment_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            requested_by INTEGER NOT NULL,
            method TEXT NOT NULL,
            requested_at REAL NOT NULL,
            resolved_at REAL,
            status TEXT NOT NULL DEFAULT 'pending',
            note TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON ticket_messages(ticket_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_attachments_ticket ON ticket_attachments(ticket_id)")
    conn.commit()
    conn.close()
    log.info("База данных инициализирована: %s", DB_PATH)


# ----------------------------
# User accounts and auth
# ----------------------------

def upsert_user_from_telegram(user_obj: Any) -> Dict[str, Any]:
    user_id = int(user_obj.get("id") if isinstance(user_obj, dict) else getattr(user_obj, "id"))
    username = user_obj.get("username") if isinstance(user_obj, dict) else getattr(user_obj, "username", None)
    full_name = full_name_from_user(user_obj)
    ts = now_ts()
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row:
        conn.execute(
            "UPDATE users SET username=?, full_name=?, updated_at=? WHERE user_id=?",
            (username, full_name, ts, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO users(user_id, username, full_name, created_at, updated_at) VALUES(?,?,?,?,?)",
            (user_id, username, full_name, ts, ts),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def get_user_record(user_id: int) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def validate_login_value(login: str) -> bool:
    if not login or len(login) < 4 or len(login) > 32:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return all(ch in allowed for ch in login)


def validate_password_value(password: str) -> bool:
    return bool(password) and len(password) >= 6 and len(password) <= 128


def password_hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 200_000).hex()


def set_user_password(user_id: int, login: str, password: str) -> Dict[str, Any]:
    salt = secrets.token_hex(16)
    hashed = password_hash(password, salt)
    ts = now_ts()
    conn = db()
    conn.execute(
        """UPDATE users
           SET cabinet_login=?, password_hash=?, password_salt=?, password_updated_at=?, updated_at=?
           WHERE user_id=?""",
        (login.lower(), hashed, salt, ts, ts, int(user_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),)).fetchone()
    conn.close()
    return dict(row)


def verify_user_password(user_id: int, login: str, password: str) -> bool:
    row = get_user_record(user_id)
    if not row or not row.get("password_hash") or not row.get("password_salt"):
        return False
    if (row.get("cabinet_login") or "").lower() != login.lower():
        return False
    return hmac.compare_digest(row["password_hash"], password_hash(password, row["password_salt"]))


def create_session(user_id: int, user_agent: str = "") -> str:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    ts = now_ts()
    expires = ts + SESSION_TTL_DAYS * 86400
    conn = db()
    conn.execute(
        "INSERT INTO user_sessions(user_id, token_hash, created_at, expires_at, user_agent) VALUES(?,?,?,?,?)",
        (int(user_id), token_hash, ts, expires, user_agent[:200]),
    )
    conn.execute("UPDATE users SET last_login_at=? WHERE user_id=?", (ts, int(user_id)))
    conn.commit()
    conn.close()
    return raw


def clear_expired_sessions() -> None:
    conn = db()
    conn.execute("DELETE FROM user_sessions WHERE expires_at < ?", (now_ts(),))
    conn.commit()
    conn.close()


def revoke_user_session(token: str) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = db()
    conn.execute("DELETE FROM user_sessions WHERE token_hash=?", (token_hash,))
    conn.commit()
    conn.close()


def validate_session_token(user_id: int, token: str) -> bool:
    if not token:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = db()
    row = conn.execute(
        "SELECT * FROM user_sessions WHERE user_id=? AND token_hash=? AND expires_at>?",
        (int(user_id), token_hash, now_ts()),
    ).fetchone()
    conn.close()
    return bool(row)


def parse_init_data(init_data: str) -> Dict[str, str]:
    return dict(parse_qsl(init_data or "", keep_blank_values=True))


def validate_webapp_init_data(init_data: str) -> Optional[Dict[str, Any]]:
    if not init_data:
        return None
    parsed_pairs = parse_qsl(init_data, keep_blank_values=True)
    data = {k: v for k, v in parsed_pairs}
    if DEV_ALLOW_UNSAFE_INITDATA and "hash" not in data:
        user_payload = {}
        if data.get("user"):
            try:
                user_payload = json.loads(data["user"])
            except Exception:
                user_payload = {}
        return {"ok": True, "user": user_payload, "raw": data}

    their_hash = data.get("hash")
    if not their_hash:
        return None
    check_pairs = [f"{k}={v}" for k, v in sorted(parsed_pairs) if k != "hash"]
    data_check_string = "\n".join(check_pairs)
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, their_hash):
        return None
    auth_date = int(data.get("auth_date", "0") or 0)
    if auth_date and abs(now_ts() - auth_date) > INITDATA_MAX_AGE:
        return None
    user_payload = {}
    if data.get("user"):
        try:
            user_payload = json.loads(data["user"])
        except Exception:
            return None
    return {"ok": True, "user": user_payload, "raw": data}


def auth_user_from_http(init_data: str, session_token: str = "") -> Optional[Dict[str, Any]]:
    auth = validate_webapp_init_data(init_data)
    if not auth:
        return None
    user = auth.get("user") or {}
    try:
        user_id = int(user.get("id"))
    except Exception:
        return None
    row = upsert_user_from_telegram(user)
    has_password = bool(row.get("password_hash"))
    session_valid = validate_session_token(user_id, session_token) if has_password else True
    return {
        "user_id": user_id,
        "telegram_user": user,
        "db_user": row,
        "has_password": has_password,
        "session_valid": session_valid,
    }


def require_user_session(init_data: str, session_token: str = "") -> Optional[Dict[str, Any]]:
    auth = auth_user_from_http(init_data, session_token)
    if not auth:
        return None
    if not auth["has_password"] or not auth["session_valid"]:
        return None
    return auth


def auth_admin_from_http(init_data: str) -> Optional[Dict[str, Any]]:
    auth = validate_webapp_init_data(init_data)
    if not auth:
        return None
    user = auth.get("user") or {}
    try:
        user_id = int(user.get("id"))
    except Exception:
        return None
    if not is_admin(user_id):
        return None
    upsert_user_from_telegram(user)
    return {"user_id": user_id, "telegram_user": user}


# ----------------------------
# Tickets, messages, attachments, invoices
# ----------------------------

def active_statuses() -> set:
    return set(USER_ACTIVE_STATUSES)


def ticket_is_visible_to_user(status: str) -> bool:
    return status in USER_ACTIVE_STATUSES or status in {"closed", "rejected"}


def commission_amount(amount: float) -> float:
    return round(float(amount or 0) * COMISSION_SAFE(), 2)


def COMISSION_SAFE() -> float:
    return COMISSION if False else COMMISSION


def ticket_effective_amount(ticket: Dict[str, Any]) -> float:
    base = format_money(ticket.get("invoice_amount") or ticket.get("amount") or 0)
    discount = format_money(ticket.get("promo_discount") or 0)
    return max(0.0, round(base - discount, 2))


def get_promo_usage_count(conn: Optional[sqlite3.Connection] = None) -> int:
    owns = conn is None
    conn = conn or db()
    count = conn.execute("SELECT COUNT(*) FROM tickets WHERE promo_code=? AND promo_applied=1", (PROMO_CODE,)).fetchone()[0]
    if owns:
        conn.close()
    return int(count or 0)


def promo_discount_for_ticket(ticket: Dict[str, Any]) -> float:
    invoice_amount = format_money(ticket.get("invoice_amount") or 0)
    if invoice_amount <= 0:
        return 0.0
    return round(invoice_amount * PROMO_BUFF_PERCENT, 2)


def add_ticket_message(ticket_id: int, sender_role: str, text: str, sender_id: Optional[int] = None, sender_name: Optional[str] = None) -> None:
    clean = (text or "").strip()
    if not clean:
        return
    conn = db()
    conn.execute(
        """INSERT INTO ticket_messages(ticket_id, sender_role, sender_id, sender_name, text, created_at)
           VALUES(?,?,?,?,?,?)""",
        (int(ticket_id), sender_role[:30], sender_id, (sender_name or "")[:120], clean[:4000], now_ts()),
    )
    conn.execute("UPDATE tickets SET updated_at=? WHERE id=?", (now_ts(), int(ticket_id)))
    conn.commit()
    conn.close()


def get_ticket_messages(ticket_id: int) -> List[Dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        "SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY created_at ASC, id ASC",
        (int(ticket_id),),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def attachment_storage_dir(ticket_id: int) -> Path:
    root = Path(UPLOAD_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    folder = root / str(int(ticket_id))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def attachment_file_path(attachment: Dict[str, Any]) -> Path:
    return attachment_storage_dir(int(attachment["ticket_id"])) / str(attachment["stored_name"])


def serialize_attachment(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    data = dict(row)
    data["url"] = f"/media/{data['id']}"
    data["created_at_label"] = format_dt(data.get("created_at"))
    return data


def add_ticket_attachment(ticket_id: int, user_id: int, filename: str, mime_type: str, content_b64: str) -> Dict[str, Any]:
    safe_name = Path(filename or "image.jpg").name[:120] or "image.jpg"
    mime_type = (mime_type or "application/octet-stream")[:100]
    if not mime_type.startswith("image/"):
        raise ValueError("Можно загружать только изображения.")
    raw = base64.b64decode(content_b64.encode("utf-8"), validate=True)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError("Файл слишком большой. Максимум 10 МБ.")
    suffix = Path(safe_name).suffix or mimetypes.guess_extension(mime_type) or ".jpg"
    stored_name = f"{secrets.token_hex(16)}{suffix}"
    file_path = attachment_storage_dir(ticket_id) / stored_name
    file_path.write_bytes(raw)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO ticket_attachments(ticket_id, user_id, filename, stored_name, mime_type, size_bytes, created_at)
           VALUES(?,?,?,?,?,?,?)""",
        (int(ticket_id), int(user_id), safe_name, stored_name, mime_type, len(raw), now_ts()),
    )
    attachment_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM ticket_attachments WHERE id=?", (attachment_id,)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", f"К заявке добавлено фото: {safe_name}.")
    return serialize_attachment(dict(row))


def get_attachment(attachment_id: int) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute("SELECT * FROM ticket_attachments WHERE id=?", (int(attachment_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_ticket_attachments(ticket_id: int) -> List[Dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        "SELECT * FROM ticket_attachments WHERE ticket_id=? ORDER BY created_at ASC, id ASC",
        (int(ticket_id),),
    ).fetchall()
    conn.close()
    return [serialize_attachment(dict(row)) for row in rows]


def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_active_ticket(user_id: int) -> Optional[Dict[str, Any]]:
    conn = db()
    row = conn.execute(
        f"SELECT * FROM tickets WHERE user_id=? AND status IN ({','.join('?' * len(USER_ACTIVE_STATUSES))}) ORDER BY created_at DESC LIMIT 1",
        (int(user_id), *USER_ACTIVE_STATUSES),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_tickets(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    conn = db()
    rows = conn.execute(
        "SELECT * FROM tickets WHERE user_id=? ORDER BY updated_at DESC, id DESC LIMIT ?",
        (int(user_id), int(limit)),
    ).fetchall()
    conn.close()
    return [serialize_ticket(dict(row)) for row in rows]


def user_ticket_count_today(user_id: int) -> int:
    day_ago = now_ts() - 86400
    conn = db()
    count = conn.execute("SELECT COUNT(*) FROM tickets WHERE user_id=? AND created_at>=?", (int(user_id), day_ago)).fetchone()[0]
    conn.close()
    return int(count or 0)


def create_ticket(user_id: int, service: str, amount: float, description: str) -> Dict[str, Any]:
    ts = now_ts()
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO tickets(user_id, service, amount, description, status, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?)""",
        (int(user_id), service[:120], float(amount), description[:4000], "new", ts, ts),
    )
    ticket_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", "Заявка создана. Ожидайте ответа от поддержки.")
    return dict(row)


def assign_ticket(ticket_id: int, admin_id: int) -> None:
    conn = db()
    conn.execute("UPDATE tickets SET assigned_admin=?, updated_at=? WHERE id=?", (int(admin_id), now_ts(), int(ticket_id)))
    conn.commit()
    conn.close()


def update_ticket_status(ticket_id: int, status: str) -> None:
    payload = {"updated_at": now_ts(), "status": status}
    conn = db()
    if status in {"closed", "rejected"}:
        conn.execute("UPDATE tickets SET status=?, updated_at=?, closed_at=? WHERE id=?", (status, payload["updated_at"], now_ts(), int(ticket_id)))
    else:
        conn.execute("UPDATE tickets SET status=?, updated_at=? WHERE id=?", (status, payload["updated_at"], int(ticket_id)))
    conn.commit()
    conn.close()


def set_invoice(ticket_id: int, amount: float, note: str) -> Dict[str, Any]:
    conn = db()
    conn.execute(
        """UPDATE tickets
           SET invoice_amount=?, invoice_note=?, payment_status='invoice_sent', status='awaiting_payment',
               updated_at=?, closed_at=?
           WHERE id=?""",
        (format_money(amount), note[:4000], now_ts(), now_ts(), int(ticket_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", "Поддержка выставила счёт. Выберите способ оплаты в кабинете.")
    return dict(row)


def set_payment_method(ticket_id: int, method: str) -> Dict[str, Any]:
    conn = db()
    conn.execute(
        "UPDATE tickets SET payment_method=?, updated_at=? WHERE id=?",
        (method, now_ts(), int(ticket_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    return dict(row)


def apply_promo_code(ticket_id: int, user_id: int, code: str) -> Dict[str, Any]:
    code = (code or "").strip().upper()
    if code != PROMO_CODE:
        raise ValueError("Промокод не найден.")
    conn = db()
    user_row = conn.execute("SELECT buff_used_at FROM users WHERE user_id=?", (int(user_id),)).fetchone()
    ticket_row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    if not ticket_row:
        conn.close()
        raise ValueError("Заявка не найдена.")
    ticket = dict(ticket_row)
    if user_row and user_row["buff_used_at"]:
        conn.close()
        raise ValueError("Промокод BUFF уже использован этим пользователем.")
    if ticket.get("promo_applied"):
        conn.close()
        raise ValueError("Промокод уже применён к этой заявке.")
    total_uses = get_promo_usage_count(conn)
    if total_uses >= PROMO_BUFF_MAX_USES:
        conn.close()
        raise ValueError("Промокод BUFF больше недоступен.")
    if format_money(ticket.get("invoice_amount") or 0) <= 0:
        conn.close()
        raise ValueError("Промокод можно применить только после выставления счёта.")
    discount = promo_discount_for_ticket(ticket)
    conn.execute(
        "UPDATE tickets SET promo_code=?, promo_discount=?, promo_applied=1, updated_at=? WHERE id=?",
        (PROMO_CODE, discount, now_ts(), int(ticket_id)),
    )
    conn.execute("UPDATE users SET buff_used_at=?, updated_at=? WHERE user_id=?", (now_ts(), now_ts(), int(user_id)))
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    percent = int(round(PROMO_BUFF_PERCENT * 100))
    add_ticket_message(ticket_id, "system", f"Применён промокод {PROMO_CODE}. Скидка {percent}% от суммы счёта ({discount:.2f} ₽).")
    return dict(row)


def request_payment_check(ticket_id: int, user_id: int) -> Dict[str, Any]:
    conn = db()
    ticket_row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    if not ticket_row:
        conn.close()
        raise ValueError("Заявка не найдена.")
    ticket = dict(ticket_row)
    method = ticket.get("payment_method") or "unknown"
    ts = now_ts()
    conn.execute(
        "INSERT INTO payment_checks(ticket_id, requested_by, method, requested_at, status) VALUES(?,?,?,?,?)",
        (int(ticket_id), int(user_id), method, ts, "pending"),
    )
    conn.execute(
        "UPDATE tickets SET payment_status='check_requested', status='payment_review', payment_check_requested_at=?, updated_at=? WHERE id=?",
        (ts, ts, int(ticket_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", "Пользователь запросил проверку оплаты.")
    return dict(row)


def resolve_payment(ticket_id: int, approved: bool, note: str = "", provider_ref: str = "") -> Dict[str, Any]:
    conn = db()
    ticket_row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    if not ticket_row:
        conn.close()
        raise ValueError("Заявка не найдена.")
    status = "paid" if approved else "rejected"
    ticket_status = "closed" if approved else "awaiting_payment"
    ts = now_ts()
    conn.execute(
        """UPDATE tickets
           SET payment_status=?, status=?, payment_verified_at=?, payment_provider_ref=?, payment_note=?, updated_at=?
           WHERE id=?""",
        (status, ticket_status, ts, provider_ref[:200], note[:4000], ts, int(ticket_id)),
    )
    conn.execute(
        "UPDATE payment_checks SET status=?, resolved_at=?, note=? WHERE ticket_id=? AND status='pending'",
        (status, ts, note[:4000], int(ticket_id)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (int(ticket_id),)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", "Оплата подтверждена." if approved else "Оплата не подтверждена. Проверьте реквизиты и попробуйте снова.")
    return dict(row)


def serialize_ticket(row: Optional[Dict[str, Any]], include_attachments: bool = False) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    data = dict(row)
    data["status_label"] = status_label(data.get("status"))
    data["commission"] = round(format_money(data.get("amount")) * COMMISSION, 2)
    data["created_at_label"] = format_dt(data.get("created_at"))
    data["updated_at_label"] = format_dt(data.get("updated_at"))
    data["closed_at_label"] = format_dt(data.get("closed_at"))
    data["assigned_admin_name"] = admin_name(data.get("assigned_admin"))
    data["invoice_amount"] = format_money(data.get("invoice_amount"))
    data["promo_discount"] = format_money(data.get("promo_discount"))
    data["payable_amount"] = ticket_effective_amount(data)
    data["payment_status_label"] = payment_status_label(data.get("payment_status") or "none")
    data["payment_method_label"] = PAYMENT_METHODS.get(data.get("payment_method") or "", "Не выбран")
    attachments = get_ticket_attachments(data["id"])
    data["attachments_count"] = len(attachments)
    if include_attachments:
        data["attachments"] = attachments
    return data


def admin_summary() -> Dict[str, Any]:
    conn = db()
    summary = {
        "users": int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0),
        "new": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='new'").fetchone()[0] or 0),
        "in_progress": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0] or 0),
        "waiting_user": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='waiting_user'").fetchone()[0] or 0),
        "awaiting_payment": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='awaiting_payment'").fetchone()[0] or 0),
        "payment_review": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='payment_review'").fetchone()[0] or 0),
        "closed": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0] or 0),
        "rejected": int(conn.execute("SELECT COUNT(*) FROM tickets WHERE status='rejected'").fetchone()[0] or 0),
        "revenue_paid": format_money(conn.execute("SELECT COALESCE(SUM(invoice_amount - promo_discount),0) FROM tickets WHERE payment_status='paid'").fetchone()[0] or 0),
        "revenue_open": format_money(conn.execute("SELECT COALESCE(SUM(invoice_amount - promo_discount),0) FROM tickets WHERE payment_status IN ('invoice_sent','check_requested')").fetchone()[0] or 0),
    }
    conn.close()
    return summary


def list_admin_tickets(status: str = "all", search: str = "") -> List[Dict[str, Any]]:
    sql = "SELECT * FROM tickets WHERE 1=1"
    params: List[Any] = []
    if status and status != "all":
        sql += " AND status=?"
        params.append(status)
    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        sql += " AND (CAST(id AS TEXT) LIKE ? OR CAST(user_id AS TEXT) LIKE ? OR service LIKE ? OR IFNULL(description,'') LIKE ? OR IFNULL(invoice_note,'') LIKE ?)"
        params.extend([like, like, like, like, like])
    sql += " ORDER BY CASE status WHEN 'new' THEN 0 WHEN 'in_progress' THEN 1 WHEN 'waiting_user' THEN 2 WHEN 'awaiting_payment' THEN 3 WHEN 'payment_review' THEN 4 ELSE 5 END, updated_at DESC, created_at DESC LIMIT 250"
    conn = db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [serialize_ticket(dict(row)) for row in rows]


# ----------------------------
# Notifications
# ----------------------------

def safe_send_message(chat_id: int, text: str, reply_markup=None) -> None:
    try:
        bot.send_message(int(chat_id), text, reply_markup=reply_markup)
    except Exception as exc:
        log.warning("Не удалось отправить сообщение %s: %s", chat_id, exc)


def notify_admin_new_ticket(ticket: Dict[str, Any]) -> None:
    text = (
        f"🆕 <b>Новая заявка #{ticket['id']}</b>\n"
        f"👤 Пользователь: <code>{ticket['user_id']}</code>\n"
        f"🛍 Сервис: {h(ticket['service'])}\n"
        f"💳 Сумма заказа: {format_money(ticket['amount']):.0f} ₽\n"
        f"📝 {h(ticket.get('description') or 'Без комментария')}"
    )
    if ADMIN_CHAT_ID:
        safe_send_message(ADMIN_CHAT_ID, text)
    for admin_id in ADMIN_IDS:
        safe_send_message(admin_id, text, reply_markup=admin_inline_open())


def notify_admin_text(text: str) -> None:
    if ADMIN_CHAT_ID:
        safe_send_message(ADMIN_CHAT_ID, text)
    for admin_id in ADMIN_IDS:
        safe_send_message(admin_id, text)


def notify_user_ticket_update(user_id: int, text: str) -> None:
    safe_send_message(int(user_id), text, reply_markup=user_main_kb(int(user_id)))


# ----------------------------
# Telegram bot
# ----------------------------

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    row = upsert_user_from_telegram(user)
    text = (
        f"👋 <b>Добро пожаловать в ShokeRefund</b>\n\n"
        "Мы помогаем оформить обращение по заказу, загрузить фото, отслеживать статус и общаться с поддержкой в одном кабинете.\n\n"
        "Что можно сделать в кабинете:\n"
        "• оформить заявку;\n"
        "• прикрепить фото заказа;\n"
        "• следить за статусом;\n"
        "• получить счёт и выбрать способ оплаты;\n"
        "• переписываться с поддержкой."
    )
    if row.get("cabinet_login"):
        text += f"\n\nВаш логин: <code>{h(row['cabinet_login'])}</code>"
    safe_send_message(user.id, text, reply_markup=user_main_kb(user.id))


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if not is_admin(message.from_user.id):
        safe_send_message(message.chat.id, "⛔️ Доступ только для администраторов.")
        return
    upsert_user_from_telegram(message.from_user)
    text = (
        "🧿 <b>ShokeRefund Admin</b>\n\n"
        "Откройте админку, чтобы смотреть очередь тикетов, назначать ответственных, вести чат, выставлять счёт и отмечать оплату."
    )
    safe_send_message(message.chat.id, text, reply_markup=user_main_kb(message.from_user.id))
    if admin_inline_open():
        safe_send_message(message.chat.id, "Панель администратора:", reply_markup=admin_inline_open())


@bot.message_handler(content_types=["web_app_data"])
def on_web_app_data(message):
    upsert_user_from_telegram(message.from_user)
    # кнопка меню открывает мини-апп; отдельная обработка данных не требуется
    safe_send_message(message.chat.id, "Кабинет открыт. Все действия выполняются внутри Mini App.", reply_markup=user_main_kb(message.from_user.id))


@bot.message_handler(content_types=["text", "photo", "document", "video", "audio", "voice", "sticker"])
def on_other_message(message):
    if message.content_type == "text" and message.text and message.text.startswith("/"):
        return
    upsert_user_from_telegram(message.from_user)
    if is_admin(message.from_user.id):
        safe_send_message(message.chat.id, "Используйте /admin или кнопку ниже, чтобы открыть админку.", reply_markup=user_main_kb(message.from_user.id))
    else:
        safe_send_message(message.chat.id, "Откройте кабинет кнопкой ниже — все заявки и фото отправляются через Mini App.", reply_markup=user_main_kb(message.from_user.id))


# ----------------------------
# HTTP API
# ----------------------------

def payment_methods_payload() -> List[Dict[str, Any]]:
    return [
        {"key": "lolz", "label": "LOLZ", "description": "Оплата по счёту через LOLZ."},
        {"key": "stars", "label": "Telegram Stars", "description": "Оплата через Telegram Stars после выставления счёта."},
        {"key": "cryptobot", "label": "CryptoBot", "description": "Оплата через CryptoBot по реквизитам из счёта."},
    ]


def user_bootstrap_payload(auth: Dict[str, Any]) -> Dict[str, Any]:
    db_user = auth["db_user"]
    user = auth["telegram_user"]
    has_password = bool(db_user.get("password_hash"))
    session_valid = auth["session_valid"] if has_password else False
    active_ticket = find_active_ticket(auth["user_id"]) if session_valid and has_password else None
    if not active_ticket and session_valid and has_password:
        tickets = get_user_tickets(auth["user_id"], 1)
        active_ticket = tickets[0] if tickets else None
    selected_ticket = serialize_ticket(active_ticket, include_attachments=True) if active_ticket else None
    messages = get_ticket_messages(selected_ticket["id"]) if selected_ticket else []
    return {
        "ok": True,
        "user": {
            "id": auth["user_id"],
            "username": user.get("username"),
            "fullName": full_name_from_user(user),
        },
        "account": {
            "login": db_user.get("cabinet_login"),
            "hasPassword": has_password,
            "sessionValid": session_valid,
            "passwordResetAllowed": PASSWORD_RESET_ALLOWED,
            "promoBuffUsed": bool(db_user.get("buff_used_at")),
        },
        "activeTicket": selected_ticket,
        "messages": messages,
        "tickets": get_user_tickets(auth["user_id"]),
        "paymentMethods": payment_methods_payload(),
        "promo": {
            "code": PROMO_CODE,
            "percent": int(round(PROMO_BUFF_PERCENT * 100)),
            "maxUses": PROMO_BUFF_MAX_USES,
            "remainingUses": max(0, PROMO_BUFF_MAX_USES - get_promo_usage_count()),
            "used": bool(db_user.get("buff_used_at")),
        },
        "links": {
            "reviews": REVIEWS_URL,
            "agreement": AGREEMENT_URL,
            "channel": CHANNEL_URL,
        },
    }


class MiniAppHandler(BaseHTTPRequestHandler):
    server_version = "ShokeRefund/3.0"

    def log_message(self, format, *args):
        log.info("HTTP %s - %s", self.address_string(), format % args)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send_json(self, payload: Dict[str, Any], status: int = 200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, file_path: Path):
        if not file_path.exists():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except Exception:
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if path == "/healthz":
            return self._send_json({"ok": True, "service": "shokerefund", "port": WEB_PORT})
        if path.startswith("/api/"):
            return self.handle_api_get(path, query)
        if path.startswith("/media/"):
            try:
                attachment_id = int(path.split("/")[2])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_media_id"}, 400)
            attachment = get_attachment(attachment_id)
            if not attachment:
                return self._send_json({"ok": False, "error": "not_found"}, 404)
            return self._send_file(attachment_file_path(attachment))
        rel = path.lstrip("/") or "index.html"
        file_path = (MINIAPP_DIR / rel).resolve()
        if not str(file_path).startswith(str(MINIAPP_DIR.resolve())):
            return self._send_json({"ok": False, "error": "forbidden"}, 403)
        if file_path.is_dir():
            file_path = file_path / "index.html"
        if not file_path.exists():
            file_path = MINIAPP_DIR / "index.html"
        return self._send_file(file_path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()
        if not path.startswith("/api/"):
            return self._send_json({"ok": False, "error": "not_found"}, 404)
        return self.handle_api_post(path, body)

    def handle_api_get(self, path: str, query: Dict[str, str]):
        if path == "/api/user/bootstrap":
            auth = auth_user_from_http(query.get("initData", ""), query.get("sessionToken", ""))
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            return self._send_json(user_bootstrap_payload(auth))

        if path.startswith("/api/user/tickets/"):
            auth = require_user_session(query.get("initData", ""), query.get("sessionToken", ""))
            if not auth:
                return self._send_json({"ok": False, "error": "session_required"}, 401)
            try:
                ticket_id = int(path.split("/")[4])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            ticket = get_ticket(ticket_id)
            if not ticket or int(ticket["user_id"]) != auth["user_id"]:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            return self._send_json({
                "ok": True,
                "ticket": serialize_ticket(ticket, include_attachments=True),
                "messages": get_ticket_messages(ticket_id),
                "attachments": get_ticket_attachments(ticket_id),
            })

        if path == "/api/admin/bootstrap":
            auth = auth_admin_from_http(query.get("initData", ""))
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            return self._send_json({
                "ok": True,
                "summary": admin_summary(),
                "tickets": list_admin_tickets(),
                "admins": [{"id": admin_id, "name": name} for admin_id, name in ADMIN_IDS.items()],
                "paymentMethods": payment_methods_payload(),
            })

        if path == "/api/admin/tickets":
            auth = auth_admin_from_http(query.get("initData", ""))
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            return self._send_json({
                "ok": True,
                "tickets": list_admin_tickets(query.get("status", "all"), query.get("search", "")),
                "summary": admin_summary(),
            })

        if path.startswith("/api/admin/tickets/"):
            auth = auth_admin_from_http(query.get("initData", ""))
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            try:
                ticket_id = int(path.split("/")[4])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            ticket = get_ticket(ticket_id)
            if not ticket:
                return self._send_json({"ok": False, "error": "not_found"}, 404)
            return self._send_json({
                "ok": True,
                "ticket": serialize_ticket(ticket, include_attachments=True),
                "messages": get_ticket_messages(ticket_id),
                "attachments": get_ticket_attachments(ticket_id),
                "admins": [{"id": admin_id, "name": name} for admin_id, name in ADMIN_IDS.items()],
            })

        return self._send_json({"ok": False, "error": "not_found"}, 404)

    def handle_api_post(self, path: str, body: Dict[str, Any]):
        init_data = str(body.get("initData") or "")
        session_token = str(body.get("sessionToken") or "")
        user_agent = self.headers.get("User-Agent", "")

        # account
        if path == "/api/user/account/register":
            auth = auth_user_from_http(init_data, session_token)
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            login_value = str(body.get("login") or "").strip().lower()
            password_value = str(body.get("password") or "")
            if not validate_login_value(login_value):
                return self._send_json({"ok": False, "error": "bad_login", "message": "Логин: 4-32 символа, латиница, цифры, . _ -"}, 400)
            if not validate_password_value(password_value):
                return self._send_json({"ok": False, "error": "bad_password", "message": "Пароль должен быть не короче 6 символов."}, 400)
            conn = db()
            exists = conn.execute("SELECT user_id FROM users WHERE cabinet_login=? AND user_id<>?", (login_value, auth["user_id"])).fetchone()
            conn.close()
            if exists:
                return self._send_json({"ok": False, "error": "login_taken"}, 409)
            set_user_password(auth["user_id"], login_value, password_value)
            token = create_session(auth["user_id"], user_agent)
            return self._send_json({"ok": True, "token": token, "login": login_value})

        if path == "/api/user/account/login":
            auth = auth_user_from_http(init_data, session_token="")
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            login_value = str(body.get("login") or "").strip().lower()
            password_value = str(body.get("password") or "")
            if not verify_user_password(auth["user_id"], login_value, password_value):
                return self._send_json({"ok": False, "error": "invalid_credentials"}, 401)
            token = create_session(auth["user_id"], user_agent)
            return self._send_json({"ok": True, "token": token})

        if path == "/api/user/account/logout":
            revoke_user_session(session_token)
            return self._send_json({"ok": True})

        if path == "/api/user/account/reset-password":
            if not PASSWORD_RESET_ALLOWED:
                return self._send_json({"ok": False, "error": "disabled"}, 403)
            auth = auth_user_from_http(init_data, session_token="")
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            login_value = str(body.get("login") or "").strip().lower()
            password_value = str(body.get("password") or "")
            if not validate_login_value(login_value) or not validate_password_value(password_value):
                return self._send_json({"ok": False, "error": "bad_payload"}, 400)
            conn = db()
            exists = conn.execute("SELECT user_id FROM users WHERE cabinet_login=? AND user_id<>?", (login_value, auth["user_id"])).fetchone()
            conn.close()
            if exists:
                return self._send_json({"ok": False, "error": "login_taken"}, 409)
            set_user_password(auth["user_id"], login_value, password_value)
            token = create_session(auth["user_id"], user_agent)
            return self._send_json({"ok": True, "token": token})

        # user ticket actions
        if path == "/api/user/tickets/create":
            auth = require_user_session(init_data, session_token)
            if not auth:
                return self._send_json({"ok": False, "error": "session_required"}, 401)
            if find_active_ticket(auth["user_id"]):
                return self._send_json({"ok": False, "error": "active_ticket_exists", "message": "У вас уже есть активная заявка."}, 409)
            if user_ticket_count_today(auth["user_id"]) >= MAX_TICKETS_PER_DAY:
                return self._send_json({"ok": False, "error": "daily_limit", "message": "Достигнут дневной лимит по заявкам."}, 429)
            service = str(body.get("service") or "").strip()
            description = str(body.get("description") or "").strip()
            try:
                amount = float(body.get("amount") or 0)
            except Exception:
                amount = 0.0
            if not service:
                return self._send_json({"ok": False, "error": "service_required"}, 400)
            if amount < 100 or amount > 100000:
                return self._send_json({"ok": False, "error": "bad_amount", "message": "Сумма должна быть от 100 до 100000 ₽."}, 400)
            ticket = create_ticket(auth["user_id"], service, amount, description)
            notify_admin_new_ticket(ticket)
            notify_user_ticket_update(auth["user_id"], f"✅ Заявка #{ticket['id']} создана. Прикрепите фото заказа в кабинете.")
            return self._send_json({"ok": True, "ticket": serialize_ticket(ticket, include_attachments=True), "messages": get_ticket_messages(ticket["id"]), "attachments": get_ticket_attachments(ticket["id"]), "tickets": get_user_tickets(auth["user_id"])})

        if path.startswith("/api/user/tickets/"):
            auth = require_user_session(init_data, session_token)
            if not auth:
                return self._send_json({"ok": False, "error": "session_required"}, 401)
            parts = [p for p in path.split("/") if p]
            if len(parts) < 4:
                return self._send_json({"ok": False, "error": "bad_path"}, 400)
            try:
                ticket_id = int(parts[3])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            ticket = get_ticket(ticket_id)
            if not ticket or int(ticket["user_id"]) != auth["user_id"]:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)

            if len(parts) >= 5 and parts[4] == "reply":
                text = str(body.get("text") or "").strip()
                if not text:
                    return self._send_json({"ok": False, "error": "empty_text"}, 400)
                add_ticket_message(ticket_id, "user", text, sender_id=auth["user_id"], sender_name=full_name_from_user(auth["telegram_user"]) or "Клиент")
                if ticket["status"] in {"new", "waiting_user"}:
                    update_ticket_status(ticket_id, "in_progress")
                notify_admin_text(f"📨 Новый ответ от клиента по заявке #{ticket_id}\nПользователь: <code>{auth['user_id']}</code>\n\n{h(text)}")
                return self._send_json({"ok": True, "ticket": serialize_ticket(get_ticket(ticket_id), include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id), "tickets": get_user_tickets(auth["user_id"])})

            if len(parts) >= 5 and parts[4] == "attachments":
                filename = str(body.get("filename") or "image.jpg")
                mime_type = str(body.get("mimeType") or "image/jpeg")
                content_b64 = str(body.get("contentBase64") or "")
                try:
                    add_ticket_attachment(ticket_id, auth["user_id"], filename, mime_type, content_b64)
                except ValueError as exc:
                    return self._send_json({"ok": False, "error": "bad_file", "message": str(exc)}, 400)
                return self._send_json({"ok": True, "ticket": serialize_ticket(get_ticket(ticket_id), include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id), "tickets": get_user_tickets(auth["user_id"])})

            if len(parts) >= 5 and parts[4] == "payment-method":
                method = str(body.get("method") or "").strip()
                if method not in PAYMENT_METHODS:
                    return self._send_json({"ok": False, "error": "bad_method"}, 400)
                ticket = set_payment_method(ticket_id, method)
                add_ticket_message(ticket_id, "system", f"Пользователь выбрал способ оплаты: {PAYMENT_METHODS[method]}.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(ticket, include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id)})

            if len(parts) >= 5 and parts[4] == "apply-promo":
                code = str(body.get("code") or "")
                try:
                    updated = apply_promo_code(ticket_id, auth["user_id"], code)
                except ValueError as exc:
                    return self._send_json({"ok": False, "error": "promo_error", "message": str(exc)}, 400)
                return self._send_json({"ok": True, "ticket": serialize_ticket(updated, include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id), "tickets": get_user_tickets(auth["user_id"])})

            if len(parts) >= 5 and parts[4] == "check-payment":
                try:
                    updated = request_payment_check(ticket_id, auth["user_id"])
                except ValueError as exc:
                    return self._send_json({"ok": False, "error": "payment_error", "message": str(exc)}, 400)
                notify_admin_text(f"💸 Пользователь запросил проверку оплаты по заявке #{ticket_id}.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(updated, include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id), "tickets": get_user_tickets(auth["user_id"])})

        # admin ticket actions
        if path.startswith("/api/admin/tickets/"):
            auth = auth_admin_from_http(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            parts = [p for p in path.split("/") if p]
            if len(parts) < 5:
                return self._send_json({"ok": False, "error": "bad_path"}, 400)
            try:
                ticket_id = int(parts[3])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            ticket = get_ticket(ticket_id)
            if not ticket:
                return self._send_json({"ok": False, "error": "not_found"}, 404)
            action = parts[4]

            if action == "assign":
                target_admin = int(body.get("adminId") or auth["user_id"])
                if target_admin not in ADMIN_IDS:
                    return self._send_json({"ok": False, "error": "bad_admin"}, 400)
                assign_ticket(ticket_id, target_admin)
                add_ticket_message(ticket_id, "system", f"Ответственный администратор: {admin_name(target_admin)}.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(get_ticket(ticket_id), include_attachments=True), "messages": get_ticket_messages(ticket_id)})

            if action == "status":
                status = str(body.get("status") or "").strip()
                if status not in {"new", "in_progress", "waiting_user", "awaiting_payment", "payment_review", "closed", "rejected"}:
                    return self._send_json({"ok": False, "error": "bad_status"}, 400)
                update_ticket_status(ticket_id, status)
                add_ticket_message(ticket_id, "system", f"Статус обновлён: {status_label(status)}.")
                notify_user_ticket_update(ticket["user_id"], f"ℹ️ Статус заявки #{ticket_id}: {status_label(status)}")
                return self._send_json({"ok": True, "ticket": serialize_ticket(get_ticket(ticket_id), include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id)})

            if action == "reply":
                text = str(body.get("text") or "").strip()
                if not text:
                    return self._send_json({"ok": False, "error": "empty_text"}, 400)
                assign_ticket(ticket_id, auth["user_id"])
                update_ticket_status(ticket_id, "waiting_user")
                add_ticket_message(ticket_id, "admin", text, sender_id=auth["user_id"], sender_name=admin_name(auth["user_id"]))
                notify_user_ticket_update(ticket["user_id"], f"💬 Поддержка ответила по заявке #{ticket_id}. Откройте кабинет.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(get_ticket(ticket_id), include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id)})

            if action == "invoice":
                amount = format_money(body.get("amount"))
                note = str(body.get("note") or "").strip()
                if amount <= 0:
                    return self._send_json({"ok": False, "error": "bad_amount"}, 400)
                assign_ticket(ticket_id, auth["user_id"])
                updated = set_invoice(ticket_id, amount, note)
                notify_user_ticket_update(ticket["user_id"], f"🧾 По заявке #{ticket_id} выставлен счёт. Откройте кабинет, выберите способ оплаты и при необходимости введите промокод.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(updated, include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id)})

            if action == "payment":
                approved = str(body.get("decision") or "").strip() == "approve"
                note = str(body.get("note") or "").strip()
                provider_ref = str(body.get("providerRef") or "").strip()
                updated = resolve_payment(ticket_id, approved, note, provider_ref)
                notify_user_ticket_update(ticket["user_id"], f"{'✅' if approved else '⚠️'} Проверка оплаты по заявке #{ticket_id}: {'успешно' if approved else 'не подтверждена'}. Откройте кабинет для деталей.")
                return self._send_json({"ok": True, "ticket": serialize_ticket(updated, include_attachments=True), "messages": get_ticket_messages(ticket_id), "attachments": get_ticket_attachments(ticket_id)})

        return self._send_json({"ok": False, "error": "not_found"}, 404)


# ----------------------------
# Runtime
# ----------------------------

def run_http_server() -> None:
    if not MINIAPP_DIR.exists():
        raise RuntimeError(f"Не найдена папка miniapp: {MINIAPP_DIR}")
    server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), MiniAppHandler)
    log.info("Mini App server listening on http://%s:%s", WEB_HOST, WEB_PORT)
    server.serve_forever()


def setup_bot_commands() -> None:
    try:
        bot.set_my_commands(
            [
                types.BotCommand("start", "Открыть кабинет"),
                types.BotCommand("admin", "Открыть админку"),
            ]
        )
    except Exception as exc:
        log.warning("Не удалось установить команды: %s", exc)


def main() -> None:
    init_db()
    clear_expired_sessions()
    setup_bot_commands()

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    if SEND_STARTUP_MESSAGE and ADMIN_CHAT_ID:
        safe_send_message(ADMIN_CHAT_ID, "🚀 ShokeRefund запущен.")

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as exc:
            log.error("Polling error: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
