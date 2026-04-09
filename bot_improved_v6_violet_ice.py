import os
import json
import html
import time
import sqlite3
import mimetypes
import telebot
import requests
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qsl
from telebot import types
from collections import defaultdict
from dotenv import load_dotenv

# ───────────────────────────────────────────────────
# ЛОКАЛЬНЫЙ ЗАПУСК ИЗ ОДНОГО ФАЙЛА
# 1) Вставь BOT_TOKEN в LOCAL_CONFIG ниже
# 2) Укажи свой ADMIN_CHAT_ID
# 3) Запусти: python bot_improved_v6_violet_ice.py
# 4) Для локальной проверки уже включён TEST_MODE=True
#    и SKIP_SUBSCRIPTION_CHECK=True
# При переносе на хостинг можно просто вынести те же значения в env.
# ───────────────────────────────────────────────────

load_dotenv()  # .env остаётся опциональным — для локального теста достаточно этого файла.

# ╔══════════════════════════════════════════════════╗
# ║           SHOKEREFUND BOT — НАСТРОЙКИ            ║
# ╚══════════════════════════════════════════════════╝
# Для локальной проверки можно вписать значения прямо сюда.
# При переносе на хостинг переменные окружения автоматически переопределят эти поля.
LOCAL_CONFIG = {
    "BOT_TOKEN": "PASTE_YOUR_BOT_TOKEN_HERE",
    "ADMIN_CHAT_ID": 0,
    "CHANNEL_USERNAME": "@shokerefund",
    "CHANNEL_URL": "",
    "REVIEWS_URL": "https://t.me/shokerefund_reviews",
    "AGREEMENT_URL": "https://telegra.ph/Polzovatelskoe-soglashenie-ShokeRefund-Servisa-pomoshchi-v-oformlenii-vozvratov-za-nekachestvennuyu-dostavku-edy-04-05",
    "START_PHOTO": "premium_start.png",
    "STEP1_PHOTO": "step1.png",
    "STEP2_PHOTO": "step2.png",
    "STEP3_PHOTO": "step3.png",
    "STEP4_PHOTO": "step4.png",
    "CRYPTOBOT_TOKEN": "",
    "CRYPTOBOT_API": "https://pay.crypt.bot/api",
    "LOLZ_TOKEN": "",
    "STARS_RATE": 0.5,
    "COMMISSION": 0.25,
    "MAX_TICKETS_PER_DAY": 3,
    "FLOOD_LIMIT": 10,
    "FLOOD_WINDOW": 60,
    "ADMIN_REMIND_HOURS": 24,
    "AUTO_CLOSE_HOURS": 48,
    "MAIN_ADMIN_ID": 0,
    "DB_PATH": "shokerefund.db",
    "PUBLIC_BASE_URL": "",
    "MINI_APP_URL": "",
    "ADMIN_MINI_APP_URL": "",
    "WEB_HOST": "0.0.0.0",
    "WEB_PORT": 8081,
    "TEST_MODE": True,
    "SKIP_SUBSCRIPTION_CHECK": True,
    "SEND_STARTUP_MESSAGE": True,
    "ADMIN_IDS": {
        "123456789": "Главный админ"
    },
}


def _raw_cfg(name, default=None):
    raw = os.getenv(name)
    if raw is not None and raw != "":
        return raw
    return LOCAL_CONFIG.get(name, default)


def _cfg_int(name, default=0):
    raw = _raw_cfg(name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _cfg_float(name, default=0.0):
    raw = _raw_cfg(name, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _cfg_bool(name, default=False):
    raw = _raw_cfg(name, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on", "да"}


def _cfg_text(name, default=""):
    raw = _raw_cfg(name, default)
    return "" if raw is None else str(raw)


def _resolve_asset_path(value: str) -> str:
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if os.path.isabs(value) and os.path.exists(value):
        return value
    local_path = os.path.join(os.path.dirname(__file__), value)
    if os.path.exists(local_path):
        return local_path
    return value


BOT_TOKEN = _cfg_text("BOT_TOKEN", "")
ADMIN_CHAT_ID = _cfg_int("ADMIN_CHAT_ID", 0)
CHANNEL_USERNAME = _cfg_text("CHANNEL_USERNAME", "@shokerefund")
CHANNEL_URL = _cfg_text("CHANNEL_URL", "") or f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
REVIEWS_URL = _cfg_text("REVIEWS_URL", "https://t.me/shokerefund_reviews")
AGREEMENT_URL = _cfg_text(
    "AGREEMENT_URL",
    "https://telegra.ph/Polzovatelskoe-soglashenie-ShokeRefund-Servisa-pomoshchi-v-oformlenii-vozvratov-za-nekachestvennuyu-dostavku-edy-04-05",
)
START_PHOTO = _resolve_asset_path(_cfg_text("START_PHOTO", "premium_start.png"))
STEP1_PHOTO = _resolve_asset_path(_cfg_text("STEP1_PHOTO", "step1.png"))
STEP2_PHOTO = _resolve_asset_path(_cfg_text("STEP2_PHOTO", "step2.png"))
STEP3_PHOTO = _resolve_asset_path(_cfg_text("STEP3_PHOTO", "step3.png"))
STEP4_PHOTO = _resolve_asset_path(_cfg_text("STEP4_PHOTO", "step4.png"))

# ─── Оплата ───
CRYPTOBOT_TOKEN = _cfg_text("CRYPTOBOT_TOKEN", "")
CRYPTOBOT_API = _cfg_text("CRYPTOBOT_API", "https://pay.crypt.bot/api")
LOLZ_TOKEN = _cfg_text("LOLZ_TOKEN", "")
STARS_RATE = _cfg_float("STARS_RATE", 0.5)
COMMISSION = _cfg_float("COMMISSION", 0.25)

# ─── Лимиты и тайм-ауты ───
MAX_TICKETS_PER_DAY = _cfg_int("MAX_TICKETS_PER_DAY", 3)
FLOOD_LIMIT = _cfg_int("FLOOD_LIMIT", 10)
FLOOD_WINDOW = _cfg_int("FLOOD_WINDOW", 60)
ADMIN_REMIND_HOURS = _cfg_int("ADMIN_REMIND_HOURS", 24)
AUTO_CLOSE_HOURS = _cfg_int("AUTO_CLOSE_HOURS", 48)

# ─── Режимы ───
TEST_MODE = _cfg_bool("TEST_MODE", True)
SKIP_SUBSCRIPTION_CHECK = _cfg_bool("SKIP_SUBSCRIPTION_CHECK", TEST_MODE)
SEND_STARTUP_MESSAGE = _cfg_bool("SEND_STARTUP_MESSAGE", True)

# ─── Главный админ ───
_DEFAULT_ADMINS = LOCAL_CONFIG.get("ADMIN_IDS", {"123456789": "Главный админ"})
try:
    raw_admins = os.getenv("ADMIN_IDS_JSON")
    _raw_admins = json.loads(raw_admins) if raw_admins else _DEFAULT_ADMINS
except Exception:
    _raw_admins = _DEFAULT_ADMINS
ADMIN_IDS = {int(uid): name for uid, name in _raw_admins.items()}
MAIN_ADMIN_ID = _cfg_int("MAIN_ADMIN_ID", next(iter(ADMIN_IDS), 0) if ADMIN_IDS else 0)

DB_PATH = _cfg_text("DB_PATH", "shokerefund.db")
PUBLIC_BASE_URL = _cfg_text("PUBLIC_BASE_URL", "").strip().rstrip("/")
MINI_APP_URL = _cfg_text("MINI_APP_URL", "").strip()
ADMIN_MINI_APP_URL = _cfg_text("ADMIN_MINI_APP_URL", "").strip()
WEB_HOST = _cfg_text("WEB_HOST", "0.0.0.0")
WEB_PORT = _cfg_int("WEB_PORT", 8081)

if PUBLIC_BASE_URL:
    MINI_APP_URL = MINI_APP_URL or f"{PUBLIC_BASE_URL}/"
    ADMIN_MINI_APP_URL = ADMIN_MINI_APP_URL or f"{PUBLIC_BASE_URL}/?mode=admin"

# ╔══════════════════════════════════════════════════╗
# ║                   ЛОГИРОВАНИЕ                    ║
# ╚══════════════════════════════════════════════════╝

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("Не задан BOT_TOKEN. Впиши токен в LOCAL_CONFIG[\"BOT_TOKEN\"] или передай переменную окружения BOT_TOKEN.")

# ╔══════════════════════════════════════════════════╗
# ║                   ИНИЦИАЛИЗАЦИЯ                  ║
# ╚══════════════════════════════════════════════════╝

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def is_admin(uid):
    return uid in ADMIN_IDS


def get_admin_name(uid):
    return ADMIN_IDS.get(uid, f"Адм {uid}")

# ╔══════════════════════════════════════════════════╗
# ║                  БАЗА ДАННЫХ                     ║
# ╚══════════════════════════════════════════════════╝

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        created_at REAL, is_subscribed INTEGER DEFAULT 0, banned INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, service TEXT, amount REAL, description TEXT,
        status TEXT, payment_status TEXT, assigned_admin INTEGER DEFAULT NULL,
        created_at REAL, updated_at REAL,
        last_user_msg REAL, last_admin_msg REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ticket_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER, media_type TEXT, file_id TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ticket_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER, ts REAL, actor TEXT, action TEXT, details TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        sender_role TEXT NOT NULL,
        sender_id INTEGER,
        sender_name TEXT,
        text TEXT NOT NULL,
        created_at REAL NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER, method TEXT, amount REAL,
        currency TEXT, status TEXT, tx_id TEXT, invoice_id TEXT, created_at REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS message_tracker (
        chat_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        msg_role TEXT NOT NULL,
        is_welcome INTEGER DEFAULT 0,
        PRIMARY KEY(chat_id, message_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ui_state (
        chat_id INTEGER NOT NULL,
        ui_key TEXT NOT NULL,
        message_id INTEGER NOT NULL,
        PRIMARY KEY(chat_id, ui_key)
    )""")

    conn.commit(); conn.close()
    log.info("БД инициализирована")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_admin_mini_app_url() -> str:
    base = ADMIN_MINI_APP_URL or MINI_APP_URL
    if not base:
        return ""
    if ADMIN_MINI_APP_URL:
        return ADMIN_MINI_APP_URL
    return f"{base}{'&' if '?' in base else '?'}mode=admin"


def admin_mini_app_enabled() -> bool:
    url = build_admin_mini_app_url()
    return bool(url and url.startswith(("https://", "http://")))


def admin_mini_app_webapp_info():
    url = build_admin_mini_app_url()
    if not admin_mini_app_enabled():
        return None
    try:
        return types.WebAppInfo(url)
    except Exception:
        return None


def add_ticket_message(tid, sender_role, text, sender_id=None, sender_name=None):
    clean = (text or "").strip()
    if not clean:
        return
    conn = db(); c = conn.cursor()
    c.execute(
        "INSERT INTO ticket_messages(ticket_id,sender_role,sender_id,sender_name,text,created_at) VALUES(?,?,?,?,?,?)",
        (tid, sender_role, sender_id, sender_name, clean[:4000], time.time()),
    )
    conn.commit(); conn.close()


def get_ticket_messages(tid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY created_at ASC, id ASC", (tid,))
    rows = c.fetchall(); conn.close()
    return [dict(r) for r in rows]


def parse_init_data_unsafe(init_data: str):
    payload = {}
    if not init_data:
        return payload
    for key, value in parse_qsl(init_data, keep_blank_values=True):
        if key == "user":
            try:
                payload[key] = json.loads(value)
            except Exception:
                payload[key] = None
        else:
            payload[key] = value
    return payload


def auth_web_user(init_data: str):
    parsed = parse_init_data_unsafe(init_data)
    user = parsed.get("user") or {}
    try:
        uid = int(user.get("id"))
    except Exception:
        return None
    return {"user_id": uid, "user": user}


def auth_web_admin(init_data: str):
    auth = auth_web_user(init_data)
    if not auth:
        return None
    if not is_admin(auth["user_id"]):
        return None
    return auth


def ticket_to_api(ticket):
    if not ticket:
        return None
    row = dict(ticket)
    row["commission"] = commission_amount(row.get("amount") or 0)
    row["status_label"] = ticket_status_label(row.get("status"))
    row["payment_status_label"] = payment_status_label(row.get("payment_status"))
    row["created_at_label"] = format_dt(row.get("created_at"))
    row["updated_at_label"] = format_dt(row.get("updated_at"))
    row["assigned_admin_name"] = get_admin_name(row.get("assigned_admin")) if row.get("assigned_admin") else None
    return row


def admin_summary_payload():
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='new'"); new_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'"); in_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='done'"); done_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='rejected'"); rej_n = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'"); rev = float(c.fetchone()[0] or 0)
    conn.close()
    return {"users": users, "new": new_n, "in_progress": in_n, "done": done_n, "rejected": rej_n, "revenue": rev}


def list_admin_tickets(status='all', search=''):
    conn = db(); c = conn.cursor()
    sql = "SELECT t.*, (SELECT COUNT(*) FROM ticket_media tm WHERE tm.ticket_id=t.id) AS media_count FROM tickets t WHERE 1=1"
    params = []
    if status and status != 'all':
        sql += " AND t.status=?"
        params.append(status)
    q = (search or '').strip()
    if q:
        like = f"%{q}%"
        sql += " AND (CAST(t.id AS TEXT) LIKE ? OR CAST(t.user_id AS TEXT) LIKE ? OR t.service LIKE ? OR IFNULL(t.description,'') LIKE ?)"
        params.extend([like, like, like, like])
    sql += " ORDER BY t.created_at DESC LIMIT 100"
    c.execute(sql, params)
    rows = [ticket_to_api(r) for r in c.fetchall()]
    conn.close()
    return rows

# ╔══════════════════════════════════════════════════╗
# ║               ПАМЯТЬ В ОЗУ                       ║
# ╚══════════════════════════════════════════════════╝

user_state                = {}
user_session              = {}
messages                  = {}
sort_new_first            = True
admin_wait_payment_amount = {}
pending_payments          = {}
flood_counter             = defaultdict(list)
flood_warned              = set()

# ╔══════════════════════════════════════════════════╗
# ║           ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ                ║
# ╚══════════════════════════════════════════════════╝

def ensure_msgs(uid):
    if uid in messages:
        return

    data = {"bot": [], "user": [], "welcome": None}
    try:
        conn = db(); c = conn.cursor()
        c.execute(
            "SELECT message_id, msg_role, is_welcome FROM message_tracker WHERE chat_id=? ORDER BY message_id ASC",
            (uid,)
        )
        for row in c.fetchall():
            mid = row["message_id"]
            role = row["msg_role"]
            if role == "bot":
                data["bot"].append(mid)
            elif role == "user":
                data["user"].append(mid)
            if row["is_welcome"]:
                data["welcome"] = mid
        conn.close()
    except Exception:
        pass

    messages[uid] = data


def _persist_track(uid, mid, role, is_welcome=False):
    try:
        conn = db(); c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO message_tracker(chat_id,message_id,msg_role,is_welcome) VALUES(?,?,?,?)",
            (uid, mid, role, 1 if is_welcome else 0)
        )
        if is_welcome:
            c.execute(
                "UPDATE message_tracker SET is_welcome=0 WHERE chat_id=? AND message_id<>?",
                (uid, mid)
            )
        conn.commit(); conn.close()
    except Exception:
        pass


def _persist_untrack(uid, mid=None):
    try:
        conn = db(); c = conn.cursor()
        if mid is None:
            c.execute("DELETE FROM message_tracker WHERE chat_id=?", (uid,))
        else:
            c.execute("DELETE FROM message_tracker WHERE chat_id=? AND message_id=?", (uid, mid))
        conn.commit(); conn.close()
    except Exception:
        pass


def ui_get(uid, ui_key):
    try:
        conn = db(); c = conn.cursor()
        c.execute("SELECT message_id FROM ui_state WHERE chat_id=? AND ui_key=?", (uid, ui_key))
        row = c.fetchone()
        conn.close()
        return int(row[0]) if row else None
    except Exception:
        return None


def ui_set(uid, ui_key, message_id):
    try:
        conn = db(); c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO ui_state(chat_id, ui_key, message_id) VALUES(?,?,?)",
            (uid, ui_key, message_id)
        )
        conn.commit(); conn.close()
    except Exception:
        pass


def ui_drop(uid, ui_key=None):
    try:
        conn = db(); c = conn.cursor()
        if ui_key is None:
            c.execute("DELETE FROM ui_state WHERE chat_id=?", (uid,))
        else:
            c.execute("DELETE FROM ui_state WHERE chat_id=? AND ui_key=?", (uid, ui_key))
        conn.commit(); conn.close()
    except Exception:
        pass


def track_bot(uid, mid, is_welcome=False):
    ensure_msgs(uid)
    if mid not in messages[uid]["bot"]:
        messages[uid]["bot"].append(mid)
    if is_welcome:
        messages[uid]["welcome"] = mid
    _persist_track(uid, mid, "bot", is_welcome=is_welcome)


def track_user(uid, mid):
    ensure_msgs(uid)
    if mid not in messages[uid]["user"]:
        messages[uid]["user"].append(mid)
    _persist_track(uid, mid, "user", is_welcome=False)


def _del(uid, mid):
    try:
        bot.delete_message(uid, mid)
    except Exception:
        pass
    finally:
        _persist_untrack(uid, mid)


def purge_dialog(uid, keep_welcome=False):
    ensure_msgs(uid)
    welcome_mid = messages[uid].get("welcome")
    if keep_welcome and welcome_mid is None:
        # Дополнительная подстраховка для старых БД: если welcome-флаг потерян,
        # оставляем самое позднее бот-сообщение как стартовую карточку.
        bot_ids = list(messages[uid].get("bot", []))
        if bot_ids:
            welcome_mid = bot_ids[-1]
            messages[uid]["welcome"] = welcome_mid
            _persist_track(uid, welcome_mid, "bot", is_welcome=True)
    kept_bot = []

    for mid in list(messages[uid]["bot"]):
        if keep_welcome and welcome_mid and mid == welcome_mid:
            kept_bot.append(mid)
            continue
        _del(uid, mid)

    for mid in list(messages[uid]["user"]):
        _del(uid, mid)

    messages[uid]["bot"] = kept_bot
    messages[uid]["user"] = []
    ui_drop(uid, "ticket_card")
    if not keep_welcome:
        messages[uid]["welcome"] = None
        _persist_untrack(uid)
    elif welcome_mid:
        _persist_untrack(uid)
        _persist_track(uid, welcome_mid, "bot", is_welcome=True)


def clear_flow(uid):
    if get_state(uid) == "in_chat":
        return
    purge_dialog(uid, keep_welcome=True)


def full_clear(uid, keep_welcome=False):
    purge_dialog(uid, keep_welcome=keep_welcome)


def _open_photo_payload(photo):
    if isinstance(photo, str) and photo and not photo.startswith(("http://", "https://")) and os.path.exists(photo):
        fh = open(photo, "rb")
        return fh, True
    return photo, False


def _send_photo_message(chat_id, photo, caption=None, reply_markup=None, **kwargs):
    payload, should_close = _open_photo_payload(photo)
    try:
        return bot.send_photo(chat_id, photo=payload, caption=caption, reply_markup=reply_markup, **kwargs)
    finally:
        if should_close:
            payload.close()


def send_clean(uid, text, markup=None):
    clear_flow(uid)
    msg = bot.send_message(uid, text, reply_markup=markup)
    track_bot(uid, msg.message_id)
    return msg


def send_clean_photo(uid, photo, caption=None, markup=None, **kwargs):
    clear_flow(uid)
    msg = _send_photo_message(uid, photo=photo, caption=caption, reply_markup=markup, **kwargs)
    track_bot(uid, msg.message_id)
    return msg


def send_final(uid, text, markup=None):
    msg = bot.send_message(uid, text, reply_markup=markup)
    track_bot(uid, msg.message_id)
    return msg


def send_tracked_text(uid, text, markup=None, **kwargs):
    msg = bot.send_message(uid, text, reply_markup=markup, **kwargs)
    track_bot(uid, msg.message_id)
    return msg


def send_tracked_photo(uid, photo, caption=None, markup=None, **kwargs):
    msg = _send_photo_message(uid, photo=photo, caption=caption, reply_markup=markup, **kwargs)
    track_bot(uid, msg.message_id)
    return msg


def send_tracked_document(uid, document, caption=None, markup=None, **kwargs):
    msg = bot.send_document(uid, document=document, caption=caption, reply_markup=markup, **kwargs)
    track_bot(uid, msg.message_id)
    return msg


def send_tracked_video(uid, video, caption=None, markup=None, **kwargs):
    msg = bot.send_video(uid, video=video, caption=caption, reply_markup=markup, **kwargs)
    track_bot(uid, msg.message_id)
    return msg


def set_state(uid, s):
    user_state[uid] = s


def get_state(uid):
    return user_state.get(uid)


def init_session(uid):
    user_session[uid] = {
        "service": None,
        "amount": None,
        "media": [],
        "agreement_accepted": False,
        "description": "",
        "source": "chat",
    }


def is_subscribed(uid):
    if SKIP_SUBSCRIPTION_CHECK:
        return True
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning(f"Не удалось проверить подписку для {uid}: {e}")
        return False


def upsert_user(user):
    uid = user.id
    name = ((user.first_name or "") + " " + (user.last_name or "")).strip()
    conn = db(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if c.fetchone():
        c.execute(
            "UPDATE users SET username=?, full_name=? WHERE user_id=?",
            (user.username or "", name, uid)
        )
    else:
        c.execute(
            "INSERT INTO users(user_id,username,full_name,created_at) VALUES(?,?,?,?)",
            (uid, user.username or "", name, time.time())
        )
    conn.commit(); conn.close()


def is_banned(uid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    return bool(row and row["banned"])


def set_subscribed(uid):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE users SET is_subscribed=1 WHERE user_id=?", (uid,))
    conn.commit(); conn.close()
# ╔══════════════════════════════════════════════════╗
# ║              АНТИ-СПАМ / ФЛУД                   ║
# ╚══════════════════════════════════════════════════╝

def check_flood(uid) -> bool:
    now = time.time()
    flood_counter[uid] = [t for t in flood_counter[uid] if now - t < FLOOD_WINDOW]
    flood_counter[uid].append(now)
    if len(flood_counter[uid]) >= FLOOD_LIMIT:
        if uid not in flood_warned:
            flood_warned.add(uid)
            try:
                send_tracked_text(
                    uid,
                    "⚠️ <b>Слишком много сообщений!</b>\n\n"
                    "Подождите немного и продолжите.\n"
                    "Злоупотребление сервисом недопустимо."
                )
            except:
                pass
        return True
    flood_warned.discard(uid)
    return False

def tickets_today(uid) -> int:
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets WHERE user_id=? AND created_at>?",
              (uid, time.time() - 86400))
    n = c.fetchone()[0]; conn.close()
    return n

# ╔══════════════════════════════════════════════════╗
# ║              РАБОТА С ТИКЕТАМИ                   ║
# ╚══════════════════════════════════════════════════╝

def create_ticket(uid) -> int:
    s   = user_session[uid]
    now = time.time()
    description = (s.get("description") or "").strip()
    source = s.get("source", "chat")
    conn = db(); c = conn.cursor()
    c.execute("""INSERT INTO tickets
        (user_id,service,amount,description,status,payment_status,
         created_at,updated_at,last_user_msg,last_admin_msg)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (uid, s["service"], s["amount"], description, "new", "none", now, now, now, now))
    tid = c.lastrowid
    for mt, fid in s["media"]:
        c.execute("INSERT INTO ticket_media(ticket_id,media_type,file_id) VALUES(?,?,?)",
                  (tid, mt, fid))
    details = "Пользователь создал заявку через Mini App" if source == "mini_app" else "Пользователь создал заявку"
    c.execute("INSERT INTO ticket_history(ticket_id,ts,actor,action,details) VALUES(?,?,?,?,?)",
              (tid, now, "user", "created", details))
    conn.commit(); conn.close()
    add_ticket_message(tid, "system", "Заявка создана через Mini App." if source == "mini_app" else "Заявка создана через чат бота.")
    if description:
        add_ticket_message(tid, "user", description, sender_id=uid, sender_name="Клиент")
    log.info(f"Создана заявка #{tid} от {uid}")
    return tid

def get_ticket(tid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE id=?", (tid,))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def get_ticket_media(tid):
    conn = db(); c = conn.cursor()
    c.execute("SELECT media_type, file_id FROM ticket_media WHERE ticket_id=?", (tid,))
    rows = c.fetchall(); conn.close()
    return [(r["media_type"], r["file_id"]) for r in rows]

def add_history(tid, actor, action, details=""):
    conn = db(); c = conn.cursor()
    c.execute("INSERT INTO ticket_history(ticket_id,ts,actor,action,details) VALUES(?,?,?,?,?)",
              (tid, time.time(), actor, action, details))
    conn.commit(); conn.close()

def update_status(tid, status):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE tickets SET status=?,updated_at=? WHERE id=?", (status, time.time(), tid))
    conn.commit(); conn.close()

def update_pay_status(tid, ps):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE tickets SET payment_status=?,updated_at=? WHERE id=?", (ps, time.time(), tid))
    conn.commit(); conn.close()

def assign_ticket(tid, admin_id):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE tickets SET assigned_admin=? WHERE id=?", (admin_id, tid))
    conn.commit(); conn.close()

def touch_user_msg(tid):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE tickets SET last_user_msg=? WHERE id=?", (time.time(), tid))
    conn.commit(); conn.close()

def touch_admin_msg(tid):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE tickets SET last_admin_msg=? WHERE id=?", (time.time(), tid))
    conn.commit(); conn.close()

def create_payment(tid, method, amount, currency, status="pending", invoice_id=None):
    conn = db(); c = conn.cursor()
    c.execute("""INSERT INTO payments(ticket_id,method,amount,currency,status,invoice_id,created_at)
                 VALUES(?,?,?,?,?,?,?)""",
              (tid, method, amount, currency, status, invoice_id, time.time()))
    conn.commit(); conn.close()

def update_payment_status(invoice_id, status):
    conn = db(); c = conn.cursor()
    c.execute("UPDATE payments SET status=? WHERE invoice_id=?", (status, invoice_id))
    conn.commit(); conn.close()

def get_next_new_ticket():
    conn = db(); c = conn.cursor()
    order = "DESC" if sort_new_first else "ASC"
    c.execute(f"SELECT * FROM tickets WHERE status='new' ORDER BY created_at {order} LIMIT 1")
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def find_active_ticket(uid):
    conn = db(); c = conn.cursor()
    c.execute("""SELECT * FROM tickets WHERE user_id=? AND status IN ('new','in_progress')
                 ORDER BY created_at DESC LIMIT 1""", (uid,))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

# ╔══════════════════════════════════════════════════╗
# ║                   УТИЛИТЫ                        ║
# ╚══════════════════════════════════════════════════╝

def rub_to_stars(rub):
    return max(1, int(round(rub * STARS_RATE)))


def commission_amount(rub):
    return round(rub * COMMISSION, 2)


def format_dt(ts):
    if not ts:
        return "—"
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts))


def ticket_status_label(status):
    return {
        "new": "🕓 Ожидание",
        "in_progress": "🟡 В работе",
        "done": "🏁 Завершена",
        "rejected": "❌ Отклонена",
    }.get(status, status)


def payment_status_label(status):
    return {
        "none": "— не запрошена",
        "pending": "⏳ ожидается",
        "paid": "✅ оплачена",
        "failed": "❌ отклонена",
    }.get(status, status)


def user_stage_label(ticket):
    status = ticket.get("status")
    payment_status = ticket.get("payment_status")
    if status == "new":
        return "🕓 Создана"
    if status == "rejected":
        return "❌ Отклонена"
    if status == "done":
        return "✅ Завершена"
    if payment_status == "pending":
        return "💳 Ожидаем оплату"
    if payment_status == "paid":
        return "⚙️ В обработке"
    return "🟡 Принята в работу"


def format_last_touch(ts):
    return format_dt(ts) if ts else "—"


def render_user_ticket_card(ticket, banner=None, closed_note=None):
    admin_label = get_admin_name(ticket["assigned_admin"]) if ticket.get("assigned_admin") else "назначается"
    commission = int(commission_amount(ticket["amount"]))
    safe_description = html.escape(str(ticket.get("description") or "")).strip()
    lines = []
    if banner:
        lines.append(f"{banner}\n")
    lines.append(f"📌 <b>Заявка #{ticket['id']}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"Статус: <b>{user_stage_label(ticket)}</b>")
    lines.append(f"Сервис: <b>{ticket['service']}</b>")
    lines.append(f"Сумма заказа: <b>{int(ticket['amount'])} ₽</b>")
    lines.append(f"Комиссия сервиса 25%: <b>{commission} ₽</b>")
    if safe_description:
        lines.append(f"Комментарий: <b>{safe_description}</b>")
    lines.append(f"Оплата: <b>{payment_status_label(ticket['payment_status'])}</b>")
    lines.append(f"Администратор: <b>{admin_label}</b>")
    lines.append(f"Обновлено: <code>{format_last_touch(ticket['updated_at'])}</code>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    if closed_note:
        lines.append(closed_note)
    else:
        lines.append("Для уточнений просто напишите сообщение в этот чат — оно автоматически уйдёт по вашей заявке.")
    return "\n".join(lines)


def upsert_ticket_card(uid, ticket, banner=None, final=False):
    text = render_user_ticket_card(
        ticket,
        banner=banner,
        closed_note=(
            "Если возврат уже оформлен, ожидайте зачисление. При новой ситуации можно сразу открыть следующую заявку."
            if final else None
        ),
    )
    markup = user_closed_inline_kb() if final else user_ticket_inline_kb()
    message_id = ui_get(uid, "ticket_card")

    if message_id:
        try:
            bot.edit_message_text(text, uid, message_id, reply_markup=markup)
            return message_id
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return message_id
            try:
                _del(uid, message_id)
            except Exception:
                pass
            ui_drop(uid, "ticket_card")

    msg = send_tracked_text(uid, text, markup=markup)
    ui_set(uid, "ticket_card", msg.message_id)
    return msg.message_id


def show_user_ticket_status(uid, force_text=False):
    ticket = find_active_ticket(uid)
    if not ticket:
        conn = db(); c = conn.cursor()
        c.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (uid,))
        row = c.fetchone()
        conn.close()
        if row:
            ticket = dict(row)
            upsert_ticket_card(uid, ticket, banner="ℹ️ <b>Сейчас активной заявки нет</b>", final=ticket["status"] in ("done", "rejected"))
            return
        send_tracked_text(uid, "ℹ️ <b>Сейчас у вас нет активной заявки.</b>\n\nКогда будете готовы, откройте Mini App со стартового экрана.")
        return
    upsert_ticket_card(uid, ticket)


def user_main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app = mini_app_webapp_info()
    if web_app:
        kb.row(types.KeyboardButton(text="🖥 Открыть Mini App", web_app=web_app))
    else:
        kb.row("/start")
    return kb


def user_closed_inline_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("⭐ Оставить отзыв", url=REVIEWS_URL))
    kb.add(types.InlineKeyboardButton("🔄 Новая заявка", callback_data="done_new_application"))
    return kb


def user_ticket_inline_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 Обновить статус", callback_data="my_ticket_refresh"),
        types.InlineKeyboardButton("💬 Как написать", callback_data="my_ticket_write"),
    )
    kb.add(types.InlineKeyboardButton("🏠 В стартовое меню", callback_data="my_ticket_home"))
    return kb


ADMIN_KB = types.ReplyKeyboardMarkup(resize_keyboard=True)
ADMIN_KB.row("🧿 Открыть Web Admin")


def admin_start_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    web_app = admin_mini_app_webapp_info()
    if web_app:
        kb.add(types.InlineKeyboardButton("🧿 Открыть Web Admin", web_app=web_app))
    return kb


def _admin_panel_text():
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='new'"); new_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'"); in_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='done'"); done_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='rejected'"); rej_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users"); usr_n = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'"); rev = int(c.fetchone()[0])
    conn.close()
    mode = "🧪 TEST MODE" if TEST_MODE else "🚀 PROD MODE"
    return (
        "🖥 <b>ShokeRefund • Admin Panel</b>\n"
        f"<i>{mode}</i>\n"
        "╭──────────────────╮\n"
        f"👥 Пользователи: <b>{usr_n}</b>\n"
        f"🕓 Новые: <b>{new_n}</b>    🟡 В работе: <b>{in_n}</b>\n"
        f"🏁 Завершены: <b>{done_n}</b>    ❌ Отклонены: <b>{rej_n}</b>\n"
        f"💰 Выручка: <b>{rev} ₽</b>\n"
        "╰──────────────────╯\n"
        "Ниже доступны быстрые действия по тикетам, статистике и управлению."
    )


def _admin_panel_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🕓 Новые", callback_data="ap_list_new"),
        types.InlineKeyboardButton("🟡 В работе", callback_data="ap_list_in"),
        types.InlineKeyboardButton("🏁 Завершённые", callback_data="ap_list_done"),
        types.InlineKeyboardButton("❌ Отклонённые", callback_data="ap_list_rejected"),
    )
    kb.add(
        types.InlineKeyboardButton("⏭ Следующий тикет", callback_data="act_next_ticket"),
        types.InlineKeyboardButton("🔔 Напоминания", callback_data="ap_reminders"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="ap_stats"),
        types.InlineKeyboardButton("🔄 Обновить", callback_data="ap_refresh"),
    )
    kb.add(
        types.InlineKeyboardButton("🔁 Сортировка", callback_data="ap_sort"),
        types.InlineKeyboardButton("⚙️ Управление", callback_data="ap_manage"),
    )
    return kb


def send_admin_panel(chat_id, edit_mid=None):
    text = _admin_panel_text()
    kb = _admin_panel_kb()
    if edit_mid:
        try:
            bot.edit_message_text(text, chat_id, edit_mid, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def _admin_ticket_card_text(ticket, media_count=0):
    assigned = get_admin_name(ticket["assigned_admin"]) if ticket.get("assigned_admin") else "—"
    safe_description = html.escape(str(ticket.get("description") or "")).strip()
    return (
        f"🎫 <b>Заявка #{ticket['id']}</b>\n"
        "╭──────────────────╮\n"
        f"👤 Пользователь: <code>{ticket['user_id']}</code>\n"
        f"🏷 Сервис: <b>{ticket['service']}</b>\n"
        f"💰 Сумма заказа: <b>{int(ticket['amount'])} ₽</b>\n"
        f"💸 Комиссия: <b>{int(commission_amount(ticket['amount']))} ₽</b>\n"
        + (f"📝 Комментарий: <b>{safe_description}</b>\n" if safe_description else "")
        + f"📌 Статус: <b>{ticket_status_label(ticket['status'])}</b>\n"
        f"💳 Оплата: <b>{payment_status_label(ticket['payment_status'])}</b>\n"
        f"👷 Ответственный: <b>{assigned}</b>\n"
        f"📎 Файлов: <b>{media_count}</b>\n"
        f"🕒 Создана: <code>{format_dt(ticket['created_at'])}</code>\n"
        f"♻️ Обновлена: <code>{format_dt(ticket['updated_at'])}</code>\n"
        "╰──────────────────╯"
    )


def _admin_ticket_kb(ticket_id, status, payment_status):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if status == "new":
        kb.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_{ticket_id}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{ticket_id}"),
        )
    if status == "in_progress":
        kb.add(
            types.InlineKeyboardButton("💰 Запросить оплату", callback_data=f"pay_{ticket_id}"),
            types.InlineKeyboardButton("💬 Написать", callback_data=f"msg_{ticket_id}"),
        )
        kb.add(
            types.InlineKeyboardButton("📸 Запросить фото", callback_data=f"act_photo_{ticket_id}"),
            types.InlineKeyboardButton("🧺 Корзина", callback_data=f"act_cart_{ticket_id}"),
        )
        kb.add(
            types.InlineKeyboardButton("👤 Аккаунт", callback_data=f"act_account_{ticket_id}"),
            types.InlineKeyboardButton("🔐 Код/инфо", callback_data=f"act_code_{ticket_id}"),
        )
        kb.add(
            types.InlineKeyboardButton("⏳ Мы работаем", callback_data=f"act_wait_{ticket_id}"),
            types.InlineKeyboardButton("💰 Возврат готов", callback_data=f"act_refund_{ticket_id}"),
        )
        kb.add(
            types.InlineKeyboardButton("📄 Документы", callback_data=f"act_docs_{ticket_id}"),
            types.InlineKeyboardButton("✅ Данные получены", callback_data=f"act_confirm_{ticket_id}"),
        )
        kb.add(
            types.InlineKeyboardButton("🙏 Спасибо", callback_data=f"act_thanks_{ticket_id}"),
            types.InlineKeyboardButton("🏁 Завершить", callback_data=f"done_{ticket_id}"),
        )
    kb.add(
        types.InlineKeyboardButton("📜 История", callback_data=f"act_history_{ticket_id}"),
        types.InlineKeyboardButton("🔄 Обновить карточку", callback_data=f"open_{ticket_id}"),
    )
    kb.add(types.InlineKeyboardButton("🖥 В панель", callback_data="ap_panel"))
    return kb


def send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=None):
    ticket = get_ticket(tid)
    if not ticket:
        bot.send_message(chat_id, f"⚠️ Заявка #{tid} не найдена.")
        return
    media_count = len(get_ticket_media(tid))
    text = _admin_ticket_card_text(ticket, media_count)
    kb = _admin_ticket_kb(tid, ticket["status"], ticket["payment_status"])
    if edit_mid:
        try:
            bot.edit_message_text(text, chat_id, edit_mid, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)
# ╔══════════════════════════════════════════════════╗
# ║                    ОПЛАТА                        ║
# ╚══════════════════════════════════════════════════╝

def send_stars_invoice(uid, tid, amount_rub):
    stars = rub_to_stars(amount_rub)
    try:
        msg = bot.send_invoice(
            chat_id=uid, title="⭐ Оплата — ShokeRefund",
            description=f"Заявка #{tid} · комиссия {int(amount_rub)} ₽",
            invoice_payload=f"stars_{tid}", provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice("Услуга ShokeRefund", stars)],
            start_parameter=f"pay{tid}"
        )
        track_bot(uid, msg.message_id)
        return True
    except Exception as e:
        log.error(f"Stars invoice: {e}"); return False

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def on_stars_paid(message):
    uid     = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_"):
        tid = int(payload.split("_")[1])
        update_pay_status(tid, "paid")
        add_history(tid, "user", "paid_stars", "Telegram Stars")
        pending_payments.pop(tid, None)
        send_clean(uid,
            "⭐ <b>Оплата Stars подтверждена!</b>\n\n"
            "Продолжаем работу по вашей заявке.\n"
            "Спасибо за доверие к <b>ShokeRefund</b> 🙌"
        )
        bot.send_message(ADMIN_CHAT_ID,
            f"⭐ Stars · заявка <b>#{tid}</b> · <code>{uid}</code>\n"
            f"Звёзд: {message.successful_payment.total_amount}"
        )

def cryptobot_create(amount_rub, tid):
    usdt    = round(amount_rub / 90, 2)
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.post(f"{CRYPTOBOT_API}/createInvoice", headers=headers, timeout=10, json={
            "asset": "USDT", "amount": str(usdt),
            "description": f"ShokeRefund #{tid} · {int(amount_rub)} ₽",
            "payload": f"crypto_{tid}", "expires_in": 3600
        })
        d = r.json()
        if d.get("ok"):
            inv = d["result"]
            return {"invoice_id": str(inv["invoice_id"]), "pay_url": inv["pay_url"], "usdt": usdt}
        log.error(f"CryptoBot: {d}")
    except Exception as e: log.error(f"CryptoBot req: {e}")
    return None

def cryptobot_check(invoice_id):
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    try:
        r = requests.get(f"{CRYPTOBOT_API}/getInvoices",
                         params={"invoice_ids": invoice_id}, headers=headers, timeout=10)
        d = r.json()
        if d.get("ok") and d["result"]["items"]:
            return d["result"]["items"][0]["status"]
    except Exception as e: log.error(f"CryptoBot check: {e}")
    return None

def lolz_create(amount_rub, tid):
    headers = {"Authorization": f"Bearer {LOLZ_TOKEN}", "Content-Type": "application/json"}
    try:
        r = requests.post("https://api.lzt.market/payment/create", headers=headers, timeout=10,
                          json={"amount": int(amount_rub), "comment": f"ShokeRefund #{tid}", "currency": "rub"})
        d = r.json()
        if d.get("payment_url"):
            return {"invoice_id": str(d.get("id", tid)), "pay_url": d["payment_url"]}
        log.error(f"LOLZ: {d}")
    except Exception as e: log.error(f"LOLZ req: {e}")
    return None

def send_payment_choice(uid, tid, amount_rub):
    commission = commission_amount(amount_rub)
    stars_n = rub_to_stars(commission)
    usdt_n = round(commission / 90, 2)

    kb = types.InlineKeyboardMarkup(row_width=1)
    payment_methods = 0

    if TEST_MODE:
        kb.add(types.InlineKeyboardButton("🧪 Тестовая оплата (без списания)", callback_data=f"pay_test_{tid}"))
        payment_methods += 1

    kb.add(types.InlineKeyboardButton(f"⭐ Telegram Stars (~{stars_n} ⭐)", callback_data=f"pay_stars_{tid}"))
    payment_methods += 1

    if CRYPTOBOT_TOKEN:
        kb.add(types.InlineKeyboardButton(f"💎 CryptoBot (~{usdt_n} USDT)", callback_data=f"pay_crypto_{tid}"))
        payment_methods += 1

    if LOLZ_TOKEN:
        kb.add(types.InlineKeyboardButton("🟣 LOLZ (lzt.market)", callback_data=f"pay_lolz_{tid}"))
        payment_methods += 1

    if payment_methods == 0:
        send_clean(
            uid,
            f"💳 <b>Оплата для заявки #{tid}</b>\n\n"
            f"К оплате: <b>{int(commission)} ₽</b>\n"
            "Сейчас платёжные способы не настроены. Напишите администратору.",
        )
        return

    note = "\n🧪 <i>Включён тестовый режим: можно проверить сценарий оплаты без реального списания.</i>" if TEST_MODE else ""
    send_clean(
        uid,
        f"💳 <b>Оплата услуги ShokeRefund</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Заявка: <b>#{tid}</b>\n"
        f"Сумма заказа: <b>{int(amount_rub)} ₽</b>\n"
        f"Комиссия сервиса 25%: <b>{int(commission)} ₽</b>\n"
        f"К оплате: <b>{int(commission)} ₽</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"Выберите удобный способ оплаты ниже.{note}",
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_test_"))
def on_pay_test(call):
    tid = int(call.data.split("_")[2])
    ticket = get_ticket(tid)
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена.")
        return
    update_pay_status(tid, "paid")
    create_payment(tid, "test", commission_amount(ticket["amount"]), "RUB", status="paid", invoice_id=f"test_{tid}")
    add_history(tid, "user", "paid_test", "Тестовая оплата без списания")
    pending_payments.pop(tid, None)
    bot.answer_callback_query(call.id, "Тестовая оплата отмечена ✅")
    send_clean(
        ticket["user_id"],
        "🧪 <b>Тестовая оплата успешно отмечена</b>\n\n"
        "Никаких средств не списывалось. Сценарий оплаты можно проверять локально прямо из этого файла.",
    )
    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"🧪 Тестовая оплата подтверждена по заявке <b>#{tid}</b>.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_stars_"))
def on_pay_stars(call):
    tid    = int(call.data.split("_")[2])
    ticket = get_ticket(tid)
    if not ticket: bot.answer_callback_query(call.id, "Заявка не найдена."); return
    bot.answer_callback_query(call.id)
    commission = commission_amount(ticket["amount"])
    pending_payments[tid] = {"method": "stars", "amount": commission}
    create_payment(tid, "stars", commission, "XTR", invoice_id=f"stars_{tid}")
    if not send_stars_invoice(ticket["user_id"], tid, commission):
        send_clean(ticket["user_id"], "⚠️ Не удалось создать Stars-инвойс. Попробуйте другой способ.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_crypto_"))
def on_pay_crypto(call):
    tid    = int(call.data.split("_")[2])
    ticket = get_ticket(tid)
    if not ticket: bot.answer_callback_query(call.id, "Заявка не найдена."); return
    bot.answer_callback_query(call.id, "Создаём инвойс...")
    uid        = ticket["user_id"]
    commission = commission_amount(ticket["amount"])
    inv        = cryptobot_create(commission, tid)
    if not inv:
        send_clean(uid, "⚠️ Не удалось создать инвойс CryptoBot. Попробуйте другой способ."); return
    pending_payments[tid] = {"method": "crypto", "amount": commission, "invoice_id": inv["invoice_id"]}
    create_payment(tid, "cryptobot", commission, "USDT", invoice_id=inv["invoice_id"])
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💎 Перейти к оплате",  url=inv["pay_url"]))
    kb.add(types.InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_crypto_{tid}"))
    send_clean(uid,
        f"💎 <b>Оплата через CryptoBot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Заявка: <b>#{tid}</b>\n"
        f"💵 К оплате: <b>{inv['usdt']} USDT</b>\n"
        f"⏳ Инвойс действителен 1 час\n\n"
        f"После оплаты нажмите «Проверить».", kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("check_crypto_"))
def on_check_crypto(call):
    tid   = int(call.data.split("_")[2])
    uid   = call.from_user.id
    pdata = pending_payments.get(tid)
    if not pdata: bot.answer_callback_query(call.id, "Инвойс не найден."); return
    status = cryptobot_check(pdata["invoice_id"])
    if status == "paid":
        update_pay_status(tid, "paid")
        update_payment_status(pdata["invoice_id"], "paid")
        add_history(tid, "user", "paid_crypto", "CryptoBot USDT")
        pending_payments.pop(tid, None)
        bot.answer_callback_query(call.id, "Оплата подтверждена ✅")
        send_clean(uid, "💎 <b>Оплата CryptoBot подтверждена!</b>\n\nПродолжаем работу 🙌")
        bot.send_message(ADMIN_CHAT_ID, f"💎 CryptoBot · заявка <b>#{tid}</b> · <code>{uid}</code>")
    elif status == "expired":
        bot.answer_callback_query(call.id, "Инвойс истёк ❌")
        send_clean(uid, "⌛ Инвойс истёк. Свяжитесь с администратором.")
    else:
        bot.answer_callback_query(call.id, "Оплата ещё не поступила. Попробуйте позже.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_lolz_"))
def on_pay_lolz(call):
    tid    = int(call.data.split("_")[2])
    ticket = get_ticket(tid)
    if not ticket: bot.answer_callback_query(call.id, "Заявка не найдена."); return
    bot.answer_callback_query(call.id, "Создаём ссылку LOLZ...")
    uid        = ticket["user_id"]
    commission = commission_amount(ticket["amount"])
    inv        = lolz_create(commission, tid)
    if not inv:
        send_clean(uid, "⚠️ Не удалось создать ссылку LOLZ. Попробуйте другой способ."); return
    pending_payments[tid] = {"method": "lolz", "amount": commission, "invoice_id": inv["invoice_id"]}
    create_payment(tid, "lolz", commission, "RUB", invoice_id=inv["invoice_id"])
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🟣 Перейти к оплате", url=inv["pay_url"]))
    kb.add(types.InlineKeyboardButton("✅ Я оплатил",        callback_data=f"confirm_lolz_{tid}"))
    send_clean(uid,
        f"🟣 <b>Оплата через LOLZ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Заявка: <b>#{tid}</b>\n"
        f"💰 Сумма: <b>{int(commission)} ₽</b>\n\n"
        f"После оплаты нажмите «Я оплатил» — администратор подтвердит.", kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_lolz_"))
def on_confirm_lolz(call):
    tid = int(call.data.split("_")[2])
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "Уведомление отправлено!")
    send_clean(uid, "🟣 Уведомление получено! Администратор проверит платёж в ближайшее время.")
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_pay_ok_{tid}"),
        types.InlineKeyboardButton("❌ Отклонить",   callback_data=f"admin_pay_fail_{tid}"),
    )
    bot.send_message(ADMIN_CHAT_ID,
        f"🟣 <b>LOLZ — пользователь сообщил об оплате</b>\n"
        f"Заявка: <b>#{tid}</b>  Пользователь: <code>{uid}</code>",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_pay_ok_"))
def on_admin_pay_ok(call):
    if call.message.chat.id != ADMIN_CHAT_ID: return
    tid    = int(call.data.split("_")[3])
    ticket = get_ticket(tid)
    if not ticket: bot.answer_callback_query(call.id, "Заявка не найдена."); return
    update_pay_status(tid, "paid")
    add_history(tid, "admin", "paid_lolz_confirmed", "LOLZ подтверждён вручную")
    pending_payments.pop(tid, None)
    bot.answer_callback_query(call.id, "Оплата подтверждена ✅")
    try: bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=None)
    except: pass
    send_clean(ticket["user_id"], "🟣 <b>Оплата LOLZ подтверждена!</b>\n\nПродолжаем работу 🙌")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_pay_fail_"))
def on_admin_pay_fail(call):
    if call.message.chat.id != ADMIN_CHAT_ID: return
    tid    = int(call.data.split("_")[3])
    ticket = get_ticket(tid)
    if not ticket: bot.answer_callback_query(call.id, "Заявка не найдена."); return
    update_pay_status(tid, "failed")
    add_history(tid, "admin", "pay_lolz_rejected", "LOLZ отклонён")
    bot.answer_callback_query(call.id, "Отклонено.")
    try: bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=None)
    except: pass
    send_clean(ticket["user_id"], "❌ <b>Оплата не подтверждена.</b>\nСвяжитесь с администратором.")

# ╔══════════════════════════════════════════════════╗
# ║            ПОЛЬЗОВАТЕЛЬСКИЙ ПОТОК                ║
# ╚══════════════════════════════════════════════════╝

def _start_caption():
    test_note = "\n🧪 <i>Сейчас включён локальный тестовый режим.</i>" if TEST_MODE else ""
    mini_note = "\n🖥 <b>Оформление доступно только через Mini App.</b>" if mini_app_enabled() else ""
    if START_PHOTO:
        return (
            "ShokeRefund • оформление заявок и статус кейса только через Mini App."
            f"{mini_note}{test_note}"
        )
    return (
        "✨ <b>ShokeRefund</b>\n\n"
        "Оформление новых заявок в этой версии работает только через Mini App.\n\n"
        "<b>Как теперь проходит процесс:</b>\n"
        "1️⃣ Открываете Mini App\n"
        "2️⃣ Указываете сервис, сумму и комментарий\n"
        "3️⃣ Возвращаетесь в чат и загружаете материалы по заказу\n"
        "4️⃣ Получаете сопровождение администратора до результата\n"
        "5️⃣ Комиссия сервиса — <b>25% от суммы заказа</b>\n"
        f"{mini_note}\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение."
        f"{test_note}"
    )


ALLOWED_SERVICES = [
    "🍔 Яндекс Еда",
    "🚗 Купер",
    "🛒 Яндекс Лавка",
    "🛵 Самокат",
    "🥗 Delivery Club",
]

SERVICE_ALIASES = {
    "яндекс еда": "🍔 Яндекс Еда",
    "еда": "🍔 Яндекс Еда",
    "купер": "🚗 Купер",
    "яндекс лавка": "🛒 Яндекс Лавка",
    "лавка": "🛒 Яндекс Лавка",
    "самокат": "🛵 Самокат",
    "delivery club": "🥗 Delivery Club",
    "delivery": "🥗 Delivery Club",
}


def mini_app_enabled() -> bool:
    return bool(MINI_APP_URL and MINI_APP_URL.startswith(("https://", "http://")))


def mini_app_webapp_info():
    if not mini_app_enabled():
        return None
    try:
        return types.WebAppInfo(MINI_APP_URL)
    except Exception:
        return None


def normalize_service_name(value):
    raw = (value or "").strip()
    if raw in ALLOWED_SERVICES:
        return raw
    compact = " ".join(raw.lower().replace("ё", "е").split())
    return SERVICE_ALIASES.get(compact)


def parse_web_app_payload(message):
    wad = getattr(message, "web_app_data", None)
    raw = getattr(wad, "data", "") if wad else ""
    if not raw:
        raise ValueError("Пустые данные Mini App")
    try:
        payload = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Невалидный JSON: {e}")
    if not isinstance(payload, dict):
        raise ValueError("Mini App должен отправлять объект JSON")
    return payload


def start_mini_app_draft(uid, payload, user_obj=None):
    if user_obj is not None:
        upsert_user(user_obj)

    if is_banned(uid):
        send_tracked_text(uid, "🚫 Доступ ограничен. Обратитесь в поддержку.")
        return

    active_ticket = find_active_ticket(uid)
    if active_ticket:
        upsert_ticket_card(uid, active_ticket, banner="ℹ️ <b>Сначала завершите текущую заявку</b>")
        send_tracked_text(uid, "Пока активная заявка не закрыта, новая не создаётся. Напишите сюда сообщение, если хотите уточнить текущий кейс.")
        return

    if tickets_today(uid) >= MAX_TICKETS_PER_DAY:
        send_tracked_text(uid, f"⚠️ <b>Лимит заявок исчерпан</b>\n\nНе более <b>{MAX_TICKETS_PER_DAY}</b> заявок в сутки. Попробуйте завтра.")
        return

    if not is_subscribed(uid):
        _subscription_prompt(uid)
        return

    if not payload.get("agreementAccepted"):
        send_tracked_text(uid, "⚠️ Подтвердите согласие с условиями сервиса внутри Mini App.")
        return

    service_name = normalize_service_name(payload.get("service"))
    if not service_name:
        send_tracked_text(uid, "⚠️ В Mini App передан неизвестный сервис. Откройте форму ещё раз.")
        return

    try:
        amount = float(str(payload.get("amount", "")).replace(" ", "").replace(",", "."))
    except Exception:
        send_tracked_text(uid, "⚠️ Сумма из Mini App не распознана. Проверьте поле и попробуйте ещё раз.")
        return

    if amount < 100:
        send_tracked_text(uid, "⚠️ Минимальная сумма — <b>100 ₽</b>.")
        return
    if amount > 100000:
        send_tracked_text(uid, "⚠️ Максимальная сумма — <b>100 000 ₽</b>. Свяжитесь с администратором.")
        return

    description = str(payload.get("description") or "").strip()[:1000]

    init_session(uid)
    user_session[uid].update({
        "service": service_name,
        "amount": amount,
        "description": description,
        "agreement_accepted": True,
        "source": "mini_app",
    })
    set_state(uid, "need_media")
    full_clear(uid, keep_welcome=True)
    _send_media_step(uid, service_name, amount)
    if description:
        send_tracked_text(uid, "📝 Комментарий из Mini App сохранён. Теперь отправьте фото, видео или документы по заказу и нажмите «✅ Готово». ")


def _send_service_step(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(ALLOWED_SERVICES[0], ALLOWED_SERVICES[1])
    kb.row(ALLOWED_SERVICES[2], ALLOWED_SERVICES[3])
    kb.row(ALLOWED_SERVICES[4])
    text = (
        "<b>Шаг 1 из 3 · Сервис доставки</b>\n\n"
        "Выберите сервис, по которому хотите оформить заявку."
    )
    if STEP1_PHOTO:
        return send_clean_photo(uid, STEP1_PHOTO, caption=text, markup=kb)
    return send_clean(uid, "📍 <b>Шаг 1 из 3 — сервис доставки</b>\n━━━━━━━━━━━━━━━━━━━━━\n\nВыберите сервис, в котором возникла проблема 👇", kb)


def _send_amount_step(uid, service_name):
    text = (
        "<b>Шаг 2 из 3 · Сумма заказа</b>\n\n"
        f"Сервис: <b>{service_name}</b>\n"
        "Укажите сумму заказа цифрами.\n"
        "Сразу после ввода покажем точную сумму комиссии 25%."
    )
    if STEP2_PHOTO:
        return send_clean_photo(uid, STEP2_PHOTO, caption=text, markup=types.ReplyKeyboardRemove())
    return send_clean(uid, f"📍 <b>Шаг 2 из 3 — сумма заказа</b>\n━━━━━━━━━━━━━━━━━━━━━\n✅ Сервис: <b>{service_name}</b>\n\nВведите сумму заказа цифрами.\nПример: <code>1599</code>", types.ReplyKeyboardRemove())


def _send_media_step(uid, service_name, amount_value):
    commission = commission_amount(amount_value)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Готово")
    text = (
        "<b>Шаг 3 из 3 · Материалы по заказу</b>\n\n"
        f"Сервис: <b>{service_name}</b>\n"
        f"Сумма заказа: <b>{int(amount_value)} ₽</b>\n"
        f"Комиссия сервиса 25%: <b>{int(commission)} ₽</b>\n"
        f"К оплате: <b>{int(commission)} ₽</b>\n\n"
        "Прикрепите фото, скриншоты или документы по заказу. Чем полнее материалы, тем быстрее обработка."
    )
    if STEP3_PHOTO:
        return send_clean_photo(uid, STEP3_PHOTO, caption=text, markup=kb)
    return send_clean(uid, f"📍 <b>Шаг 3 из 3 — файлы по заказу</b>\n━━━━━━━━━━━━━━━━━━━━━\n✅ Сервис: <b>{service_name}</b>\n✅ Сумма: <b>{int(amount_value)} ₽</b>\n💳 Комиссия: <b>{int(commission)} ₽</b>\n\nОтправьте фото, скриншоты или документы по заказу.\nКогда всё загрузите — нажмите «✅ Готово».", kb)


def _send_confirm_step(uid):
    s = user_session[uid]
    commission = commission_amount(s["amount"])
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✅ Отправить заявку", callback_data="send_ticket"))
    kb.add(types.InlineKeyboardButton("🔁 Начать заново", callback_data="restart"))
    text = (
        "<b>Подтверждение заявки</b>\n\n"
        f"Сервис: <b>{s['service']}</b>\n"
        f"Сумма заказа: <b>{int(s['amount'])} ₽</b>\n"
        f"Комиссия сервиса 25%: <b>{int(commission)} ₽</b>\n"
        f"К оплате: <b>{int(commission)} ₽</b>\n"
        f"Загружено файлов: <b>{len(s['media'])}</b>\n\n"
        "Проверьте данные перед отправкой заявки. После отправки она сразу появится у администратора."
    )
    if STEP4_PHOTO:
        return send_clean_photo(uid, STEP4_PHOTO, caption=text, markup=kb)
    return send_clean(uid, "🔎 <b>Проверьте заявку перед отправкой</b>\n━━━━━━━━━━━━━━━━━━━━━\n" + text.replace("\n", "\n"), kb)


def _start_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    web_app = mini_app_webapp_info()
    if web_app:
        kb.add(types.InlineKeyboardButton("🖥 Открыть Mini App", web_app=web_app))
    kb.add(types.InlineKeyboardButton("💬 Канал с отзывами", url=REVIEWS_URL))
    return kb


def _pin_callback_message_as_welcome(call):
    """Страховка: если callback пришёл со стартовой карточки, помечаем её как welcome,
    чтобы очистка не удалила текущий стартовый экран даже при старом/битом трекинге.
    """
    try:
        uid = call.from_user.id
        mid = call.message.message_id
        ensure_msgs(uid)
        track_bot(uid, mid, is_welcome=True)
    except Exception:
        pass


def _refresh_welcome(uid):
    ensure_msgs(uid)
    welcome_mid = messages[uid].get("welcome")
    if welcome_mid:
        try:
            bot.edit_message_caption(
                caption=_start_caption(),
                chat_id=uid,
                message_id=welcome_mid,
                reply_markup=_start_kb(),
                parse_mode="HTML",
            )
            return
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return
            try:
                bot.edit_message_text(
                    _start_caption(),
                    uid,
                    welcome_mid,
                    reply_markup=_start_kb(),
                )
                return
            except Exception as e2:
                if "message is not modified" in str(e2).lower():
                    return
                _del(uid, welcome_mid)
                messages[uid]["bot"] = [mid for mid in messages[uid]["bot"] if mid != welcome_mid]
                messages[uid]["welcome"] = None
    try:
        msg = _send_photo_message(uid, photo=START_PHOTO, caption=_start_caption(), reply_markup=_start_kb())
    except Exception:
        msg = bot.send_message(uid, _start_caption(), reply_markup=_start_kb())
    messages[uid]["welcome"] = msg.message_id
    track_bot(uid, msg.message_id, is_welcome=True)


def _start_new_application(uid, user_obj=None):
    if user_obj is not None:
        upsert_user(user_obj)
    init_session(uid)
    set_state(uid, "wait_start")
    full_clear(uid, keep_welcome=True)
    _refresh_welcome(uid)


@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)
    if is_banned(uid):
        send_tracked_text(uid, "🚫 Доступ ограничен. Обратитесь в поддержку.")
        return
    _start_new_application(uid, message.from_user)


def _new_application(uid_or_message):
    if isinstance(uid_or_message, int):
        uid = uid_or_message
        try:
            chat = bot.get_chat(uid)
            upsert_user(chat)
        except Exception:
            pass
    else:
        uid = uid_or_message.from_user.id
        upsert_user(uid_or_message.from_user)
    _start_new_application(uid)


def _subscription_prompt(uid):
    set_state(uid, "wait_sub")
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
    kb.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub"))
    kb.add(types.InlineKeyboardButton("💬 Отзывы", url=REVIEWS_URL))
    send_clean(
        uid,
        "📢 <b>Подписка перед стартом</b>\n\n"
        "Чтобы открыть оформление, подпишитесь на канал и затем нажмите кнопку проверки.\n\n"
        "<b>Порядок действий:</b>\n"
        "• открыть канал\n"
        "• подписаться\n"
        "• вернуться и нажать «Проверить подписку»",
        kb,
    )


def go_agreement(uid):
    set_state(uid, "agreement")
    user_session.setdefault(uid, {}).update({"agreement_accepted": False})
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📄 Открыть соглашение", url=AGREEMENT_URL))
    kb.add(types.InlineKeyboardButton("✔️ Подтвердить согласие", callback_data="agree"))
    send_clean(
        uid,
        "📄 <b>Подтверждение соглашения</b>\n\n"
        "Перед каждой новой заявкой нужно ещё раз подтвердить согласие с условиями сервиса.\n\n"
        "Откройте документ, ознакомьтесь с ним и нажмите кнопку подтверждения ниже.",
        kb,
    )


@bot.callback_query_handler(func=lambda c: c.data == "begin_flow")
def on_begin_flow(call):
    uid = call.from_user.id
    _pin_callback_message_as_welcome(call)
    bot.answer_callback_query(call.id, "Используйте Mini App")
    send_tracked_text(
        uid,
        "🖥 <b>Новые заявки принимаются только через Mini App.</b>\n\nОткройте приложение кнопкой со стартового экрана и заполните форму там.",
        markup=user_main_kb(),
    )


@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def on_check_sub(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "Используйте Mini App")
    send_tracked_text(uid, "🖥 Проверка подписки теперь происходит внутри Mini App.", markup=user_main_kb())


@bot.callback_query_handler(func=lambda c: c.data == "agree")
def on_agree(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "Используйте Mini App")
    send_tracked_text(uid, "🖥 Подтверждение соглашения теперь происходит внутри Mini App.", markup=user_main_kb())


@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "service")
def on_service(message):
    send_tracked_text(message.from_user.id, "🖥 Выбор сервиса теперь доступен только в Mini App.", markup=user_main_kb())


@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "amount")
def on_amount(message):
    send_tracked_text(message.from_user.id, "🖥 Ввод суммы теперь доступен только в Mini App.", markup=user_main_kb())


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id) == "need_media",
    content_types=["text", "photo", "document", "video", "voice", "audio", "sticker", "animation", "video_note"]
)
def on_media(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)
    if check_flood(uid):
        return
    if message.content_type == "text" and message.text == "✅ Готово":
        if not user_session[uid]["media"]:
            send_tracked_text(uid, "⚠️ Прикрепите хотя бы одно фото, видео или документ.")
            return
        go_confirm(uid)
        return
    if message.content_type == "text":
        send_tracked_text(uid, "⚠️ На этом шаге можно присылать только файлы. Потом нажмите «✅ Готово».")
        return
    if message.content_type in ["voice", "audio", "sticker", "animation", "video_note"]:
        send_tracked_text(uid, "⚠️ Нужны фото, видео или документы по заказу.")
        return
    if message.content_type == "photo":
        user_session[uid]["media"].append(("photo", message.photo[-1].file_id))
    elif message.content_type == "document":
        user_session[uid]["media"].append(("document", message.document.file_id))
    elif message.content_type == "video":
        user_session[uid]["media"].append(("video", message.video.file_id))
    count = len(user_session[uid]["media"])
    send_tracked_text(uid, f"✅ Файл получен. Сейчас загружено: <b>{count}</b> шт.")


def go_confirm(uid):
    set_state(uid, "confirm")
    _send_confirm_step(uid)


@bot.callback_query_handler(func=lambda c: c.data == "send_ticket")
def on_send_ticket(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    if tickets_today(uid) >= MAX_TICKETS_PER_DAY:
        send_tracked_text(uid, f"⚠️ Лимит {MAX_TICKETS_PER_DAY} заявок в сутки исчерпан.")
        return
    if not user_session.get(uid, {}).get("agreement_accepted"):
        go_agreement(uid)
        return
    tid = create_ticket(uid)
    set_state(uid, "in_chat")
    full_clear(uid, keep_welcome=True)
    send_final(
        uid,
        f"🕓 <b>Заявка #{tid} создана</b>\n\n"
        "Заявка передана на проверку. Для уточнений просто напишите сообщение в этот чат.",
        types.ReplyKeyboardRemove(),
    )
    ticket = get_ticket(tid)
    upsert_ticket_card(uid, ticket, banner="✨ <b>Заявка успешно отправлена</b>")
    media_list = get_ticket_media(tid)
    _notify_admin_new(tid, uid, ticket, media_list)


@bot.callback_query_handler(func=lambda c: c.data == "restart")
def on_restart(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _start_new_application(uid)


@bot.callback_query_handler(func=lambda c: c.data in {"my_ticket_open", "my_ticket_refresh", "my_ticket_write", "my_ticket_home", "done_new_application"})
def on_user_ticket_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data in {"my_ticket_home", "done_new_application"}:
        _pin_callback_message_as_welcome(call)

    if data == "done_new_application":
        bot.answer_callback_query(call.id)
        _start_new_application(uid)
        return

    if data == "my_ticket_write":
        bot.answer_callback_query(call.id, "Просто напишите сообщение в этот чат — оно уйдёт по активной заявке.")
        return

    if data == "my_ticket_home":
        bot.answer_callback_query(call.id, "Стартовое меню уже доступно выше.")
        _refresh_welcome(uid)
        return

    bot.answer_callback_query(call.id, "Статус обновлён")
    show_user_ticket_status(uid)
# ╔══════════════════════════════════════════════════╗
# ║        УВЕДОМЛЕНИЕ АДМИНИСТРАТОРА                ║
# ╚══════════════════════════════════════════════════╝

def _notify_admin_new(tid, uid, ticket, media_list):
    bot.send_message(
        ADMIN_CHAT_ID,
        "📥 <b>Поступила новая заявка</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎫 Номер: <b>#{tid}</b>\n"
        f"👤 Пользователь: <code>{uid}</code>\n"
        f"🏷 Сервис: <b>{ticket['service']}</b>\n"
        f"💰 Сумма: <b>{int(ticket['amount'])} ₽</b>\n"
        f"💳 Комиссия: <b>{int(commission_amount(ticket['amount']))} ₽</b>\n"
        f"📎 Файлов: <b>{len(media_list)}</b>"
    )
    send_admin_ticket_card(tid)
    for mt, fid in media_list:
        try:
            if mt == "photo":
                bot.send_photo(ADMIN_CHAT_ID, fid, caption=f"📎 #{tid}")
            elif mt == "document":
                bot.send_document(ADMIN_CHAT_ID, fid, caption=f"📎 #{tid}")
            elif mt == "video":
                bot.send_video(ADMIN_CHAT_ID, fid, caption=f"📎 #{tid}")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def on_accept(call):
    tid = int(call.data.split("_")[1])
    ticket = get_ticket(tid)
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена.")
        return
    if ticket["status"] != "new":
        bot.answer_callback_query(call.id, "Уже обработана.")
        return

    admin_id = call.from_user.id
    update_status(tid, "in_progress")
    assign_ticket(tid, admin_id)
    add_history(tid, "admin", "accepted", f"Принял: {get_admin_name(admin_id)}")
    touch_admin_msg(tid)
    bot.answer_callback_query(call.id, f"✅ Заявка #{tid} принята")
    send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=call.message.message_id)

    bot.send_message(
        ADMIN_CHAT_ID,
        f"✅ Заявка <b>#{tid}</b> взята в работу администратором <b>{get_admin_name(admin_id)}</b>."
    )
    if admin_id != MAIN_ADMIN_ID:
        try:
            bot.send_message(
                MAIN_ADMIN_ID,
                f"ℹ️ Заявку <b>#{tid}</b> взял <b>{get_admin_name(admin_id)}</b> (<code>{admin_id}</code>)"
            )
        except Exception:
            pass

    uid = ticket["user_id"]
    full_clear(uid, keep_welcome=True)
    set_state(uid, "in_chat")
    send_final(
        uid,
        f"🟡 <b>Заявка #{tid} принята в работу</b>\n\n"
        "Администратор уже подключился к заявке. Все дальнейшие сообщения в этом чате будут относиться к ней.",
        types.ReplyKeyboardRemove(),
    )
    fresh_ticket = get_ticket(tid)
    upsert_ticket_card(uid, fresh_ticket, banner="🟡 <b>Заявка принята в работу</b>")


@bot.callback_query_handler(func=lambda c: c.data.startswith("reject_"))
def on_reject(call):
    tid = int(call.data.split("_")[1])
    ticket = get_ticket(tid)
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена.")
        return
    if ticket["status"] != "new":
        bot.answer_callback_query(call.id, "Уже обработана.")
        return

    update_status(tid, "rejected")
    add_history(tid, "admin", "rejected", f"Отклонил: {get_admin_name(call.from_user.id)}")
    bot.answer_callback_query(call.id, "Отклонено")
    send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=call.message.message_id)

    uid = ticket["user_id"]
    set_state(uid, "chat_closed")
    full_clear(uid, keep_welcome=True)
    send_final(
        uid,
        f"❌ <b>Заявка #{tid} отклонена</b>\n\n"
        "Если ситуация изменится, вы сможете сразу открыть новую заявку.",
        user_main_kb(),
    )
    fresh_ticket = get_ticket(tid)
    upsert_ticket_card(uid, fresh_ticket, banner="❌ <b>Заявка отклонена</b>", final=True)


# ╔══════════════════════════════════════════════════╗
# ║              ЗАВЕРШЕНИЕ ТИКЕТА                   ║
# ╚══════════════════════════════════════════════════╝

def close_ticket(tid, uid, reason="done"):
    update_status(tid, reason)
    add_history(tid, "admin" if reason == "done" else "system", reason, "Заявка закрыта")
    set_state(uid, "chat_closed")
    full_clear(uid, keep_welcome=True)
    send_final(
        uid,
        f"✅ <b>Заявка #{tid} завершена</b>\n\n"
        "Если возврат уже оформлен, ожидайте зачисление в стандартные сроки платёжной системы.",
        user_main_kb(),
    )
    fresh_ticket = get_ticket(tid)
    upsert_ticket_card(uid, fresh_ticket, banner="✅ <b>Заявка завершена</b>", final=True)


@bot.callback_query_handler(func=lambda c: c.data.startswith("done_"))
def on_done(call):
    tid = int(call.data.split("_")[1])
    ticket = get_ticket(tid)
    if not ticket:
        bot.answer_callback_query(call.id, "Заявка не найдена.")
        return
    bot.answer_callback_query(call.id, "✅ Завершено")
    close_ticket(tid, ticket["user_id"])
    send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=call.message.message_id)
    bot.send_message(ADMIN_CHAT_ID, f"🏁 Заявка <b>#{tid}</b> завершена.")
# ╔══════════════════════════════════════════════════╗
# ║            ЗАПРОС ОПЛАТЫ (ADMIN)                 ║
# ╚══════════════════════════════════════════════════╝

@bot.callback_query_handler(func=lambda c:
    c.data.startswith("pay_") and
    not any(c.data.startswith(p) for p in ["pay_stars_","pay_crypto_","pay_lolz_"])
)
def on_pay_request(call):
    if call.message.chat.id != ADMIN_CHAT_ID: return
    tid      = int(call.data.split("_")[1])
    admin_id = call.from_user.id
    admin_wait_payment_amount[admin_id] = tid
    bot.answer_callback_query(call.id)
    bot.send_message(ADMIN_CHAT_ID,
        f"💰 Введите <b>сумму заказа</b> (₽) для заявки <b>#{tid}</b>\n"
        f"(комиссия 25% рассчитается автоматически):"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("msg_"))
def on_msg_user(call):
    if call.message.chat.id != ADMIN_CHAT_ID: return
    tid = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    ticket = get_ticket(tid)
    if ticket:
        bot.send_message(ADMIN_CHAT_ID,
            f"✏️ Ответьте <b>реплаем</b> на любое сообщение с UID <code>{ticket['user_id']}</code>."
        )

@bot.message_handler(content_types=["web_app_data"])
def on_web_app_data(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)

    try:
        payload = parse_web_app_payload(message)
    except ValueError as e:
        log.warning(f"Mini App payload error for {uid}: {e}")
        send_tracked_text(uid, "⚠️ Не удалось прочитать данные Mini App. Откройте форму ещё раз и повторите отправку.")
        return

    action = str(payload.get("action") or "create_ticket")
    if action == "open_status":
        show_user_ticket_status(uid)
        return
    if action != "create_ticket":
        send_tracked_text(uid, "⚠️ Неизвестное действие Mini App.")
        return

    start_mini_app_draft(uid, payload, message.from_user)


@bot.message_handler(func=lambda m: m.chat.id != ADMIN_CHAT_ID and m.content_type == "text" and m.text == "📌 Моя заявка")
def on_my_ticket_text(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)
    show_user_ticket_status(uid)


@bot.message_handler(func=lambda m: m.chat.id != ADMIN_CHAT_ID and m.content_type == "text" and m.text == "🔄 Оформить новую заявку" and get_state(m.from_user.id) == "in_chat")
def on_new_application_while_active(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)
    ticket = find_active_ticket(uid)
    if ticket:
        upsert_ticket_card(uid, ticket, banner="ℹ️ <b>Сначала завершите текущую заявку</b>")
        send_tracked_text(uid, "Пока активная заявка не закрыта, новая не создаётся. Напишите сюда сообщение, если хотите уточнить текущий кейс.")
        return
    send_tracked_text(uid, "🖥 Для новой заявки снова откройте Mini App.", markup=user_main_kb())


# ╔══════════════════════════════════════════════════╗
# ║                ПЕРЕПИСКА                         ║
# ╚══════════════════════════════════════════════════╝

@bot.message_handler(
    func=lambda m: m.chat.id != ADMIN_CHAT_ID,
    content_types=["text","photo","document","video"]
)
def user_to_admin(message):
    uid   = message.from_user.id
    state = get_state(uid)
    track_user(uid, message.message_id)

    if is_banned(uid): return
    if check_flood(uid): return

    if state in ["wait_start","wait_sub","agreement","service","amount"]:
        send_tracked_text(uid, "🖥 Для создания заявки используйте Mini App со стартового экрана.", markup=user_main_kb())
        return
    if state in ["need_media","confirm"]:
        return

    if state == "chat_closed":
        if message.content_type == "text" and message.text == "🔄 Оформить новую заявку":
            send_tracked_text(uid, "🖥 Для новой заявки снова откройте Mini App.", markup=user_main_kb())
            return
        send_tracked_text(uid, "🖥 Новые заявки доступны только через Mini App.",
                         markup=user_main_kb())
        return

    ticket = find_active_ticket(uid)
    if ticket: touch_user_msg(ticket["id"])

    header = f"📨 От <code>{uid}</code>:"
    if   message.content_type == "text":     bot.send_message(ADMIN_CHAT_ID, f"{header}\n{message.text}")
    elif message.content_type == "photo":    bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=header)
    elif message.content_type == "document": bot.send_document(ADMIN_CHAT_ID, message.document.file_id, caption=header)
    elif message.content_type == "video":    bot.send_video(ADMIN_CHAT_ID, message.video.file_id, caption=header)


@bot.message_handler(
    func=lambda m: m.chat.id == ADMIN_CHAT_ID,
    content_types=["text","photo","document","video"]
)
def admin_reply(message):
    admin_id = message.from_user.id

    # Проверка: ждём сумму оплаты
    if admin_id in admin_wait_payment_amount and message.content_type == "text":
        _handle_set_payment(message); return

    # Обработка текстовых кнопок постоянной клавиатуры
    if message.content_type == "text" and message.text in ["📋 Тикеты","📊 Статистика","🔔 Напоминания","⚙️ Управление","🧿 Открыть Web Admin"]:
        admin_kb_handler(message); return

    if not message.reply_to_message: return

    reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    uid = None
    for part in reply_text.split():
        clean = part.replace("<code>","").replace("</code>","")
        if clean.isdigit() and len(clean) >= 5:
            uid = int(clean); break
    if not uid: return

    admin_name = get_admin_name(admin_id)
    ticket     = find_active_ticket(uid)
    if ticket: touch_admin_msg(ticket["id"])

    if   message.content_type == "text":     send_tracked_text(uid, f"💬 <b>{admin_name}:</b>\n{message.text}")
    elif message.content_type == "photo":    send_tracked_photo(uid, message.photo[-1].file_id, caption=f"💬 {admin_name}")
    elif message.content_type == "document": send_tracked_document(uid, message.document.file_id, caption=f"💬 {admin_name}")
    elif message.content_type == "video":    send_tracked_video(uid, message.video.file_id, caption=f"💬 {admin_name}")

# ╔══════════════════════════════════════════════════╗
# ║           УСТАНОВКА СУММЫ ОПЛАТЫ                 ║
# ╚══════════════════════════════════════════════════╝

def _handle_set_payment(message):
    admin_id = message.from_user.id
    tid      = admin_wait_payment_amount.get(admin_id)
    ticket   = get_ticket(tid) if tid else None
    if not ticket:
        admin_wait_payment_amount.pop(admin_id, None)
        bot.send_message(ADMIN_CHAT_ID, "Заявка не найдена."); return
    try:
        amount = float(message.text.replace(",",".").replace(" ",""))
    except:
        bot.send_message(ADMIN_CHAT_ID, "Введите число. Пример: 1490"); return

    admin_wait_payment_amount.pop(admin_id, None)
    uid        = ticket["user_id"]
    commission = commission_amount(amount)

    update_pay_status(tid, "pending")
    add_history(tid, "admin", "set_amount", f"Запрошена оплата {int(commission)} ₽ (заказ {int(amount)} ₽)")
    send_payment_choice(uid, tid, amount)
    fresh_ticket = get_ticket(tid)
    if fresh_ticket:
        upsert_ticket_card(uid, fresh_ticket, banner="💳 <b>Ожидаем оплату</b>")
    bot.send_message(ADMIN_CHAT_ID,
        f"💳 Клиенту <code>{uid}</code> выставлен счёт <b>{int(commission)} ₽</b>\n"
        f"(25% от {int(amount)} ₽) · заявка #{tid}"
    )

# ╔══════════════════════════════════════════════════╗
# ║          БЫСТРЫЕ ДЕЙСТВИЯ НАД ТИКЕТОМ            ║
# ╚══════════════════════════════════════════════════╝

AUTO_REPLIES = {
    "act_hello_":   "👋 Здравствуйте! Ваша заявка принята — скоро вернёмся с ответом.",
    "act_thanks_":  "🙏 Спасибо за предоставленную информацию! Продолжаем работу.",
    "act_photo_":   "📸 Пожалуйста, отправьте дополнительные фото или скриншоты заказа.",
    "act_cart_":    "🧺 Пришлите скриншот корзины или списка позиций заказа.",
    "act_account_": "👤 Укажите телефон или e-mail аккаунта сервиса доставки.",
    "act_code_":    "🔐 Если есть код подтверждения или доп. информация от сервиса — отправьте её здесь.",
    "act_wait_":    "⏳ Заявка в обработке. Благодарим за терпение — мы работаем!",
    "act_docs_":    "📄 Пришлите скриншот заказа из приложения сервиса доставки.",
    "act_refund_":  "💰 Ваш возврат подготовлен. Ожидайте зачисления в течение 1–3 рабочих дней.",
    "act_confirm_": "✅ Информация получена, приступаем к оформлению возврата.",
}

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def on_ticket_action(call):
    if call.message.chat.id != ADMIN_CHAT_ID: return
    data = call.data

    # Быстрые автоответы
    for prefix, text in AUTO_REPLIES.items():
        if data.startswith(prefix):
            tid    = int(data[len(prefix):])
            ticket = get_ticket(tid)
            if not ticket: bot.answer_callback_query(call.id, "Нет заявки."); return
            bot.answer_callback_query(call.id)
            send_tracked_text(ticket["user_id"], f"💬 <b>Администратор:</b>\n{text}")
            touch_admin_msg(tid)
            return

    # Завершить из панели
    if data.startswith("act_done_"):
        tid    = int(data[len("act_done_"):])
        ticket = get_ticket(tid)
        if not ticket: bot.answer_callback_query(call.id, "Нет заявки."); return
        bot.answer_callback_query(call.id, "Завершено ✅")
        close_ticket(tid, ticket["user_id"])
        send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=call.message.message_id)
        bot.send_message(ADMIN_CHAT_ID, f"🏁 Заявка #{tid} завершена из панели.")
        return

    # Ответить (подсказка)
    if data.startswith("act_reply_"):
        tid    = int(data[len("act_reply_"):])
        ticket = get_ticket(tid)
        if not ticket: bot.answer_callback_query(call.id, "Нет заявки."); return
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_CHAT_ID,
            f"✏️ Ответьте <b>реплаем</b> на любое сообщение с UID <code>{ticket['user_id']}</code>.")
        return

    # История
    if data.startswith("act_history_"):
        tid  = int(data[len("act_history_"):])
        conn = db(); c = conn.cursor()
        c.execute("SELECT ts,actor,action,details FROM ticket_history WHERE ticket_id=? ORDER BY ts ASC", (tid,))
        rows = c.fetchall(); conn.close()
        bot.answer_callback_query(call.id)
        if not rows:
            bot.send_message(ADMIN_CHAT_ID, f"История #{tid} пуста."); return
        lines = [f"📜 <b>История заявки #{tid}</b>\n"]
        for row in rows:
            t = time.strftime("%d.%m %H:%M", time.localtime(row["ts"]))
            lines.append(f"<code>{t}</code> {row['actor']} · {row['action']}\n└ {row['details']}")
        bot.send_message(ADMIN_CHAT_ID, "\n".join(lines))
        return

    # Следующий тикет
    if data == "act_next_ticket":
        bot.answer_callback_query(call.id)
        ticket = get_next_new_ticket()
        if not ticket:
            bot.send_message(ADMIN_CHAT_ID, "🎉 Новых заявок нет!"); return
        tid        = ticket["id"]
        media_list = get_ticket_media(tid)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("✅ Принять",   callback_data=f"accept_{tid}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{tid}"),
        )
        bot.send_message(ADMIN_CHAT_ID,
            f"📥 <b>Заявка #{tid}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <code>{ticket['user_id']}</code>\n"
            f"🏷 {ticket['service']}  💰 <b>{int(ticket['amount'])} ₽</b>\n"
            f"📎 {len(media_list)} файл(ов) · "
            f"🕐 {time.strftime('%d.%m %H:%M', time.localtime(ticket['created_at']))}",
            reply_markup=kb
        )

# ╔══════════════════════════════════════════════════╗
# ║             ПОСТОЯННАЯ КЛАВИАТУРА АДМИНА         ║
# ╚══════════════════════════════════════════════════╝

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.content_type == "text" and m.text in {"/admin", "/start", "🧿 Открыть Web Admin"})
def cmd_admin(message):
    bot.send_message(
        message.chat.id,
        "🧿 <b>Управление тикетами перенесено в Web Admin Mini App.</b>\n\nОткройте панель кнопкой ниже.",
        reply_markup=ADMIN_KB,
    )
    if admin_mini_app_enabled():
        bot.send_message(message.chat.id, _admin_panel_text(), reply_markup=admin_start_kb())
    else:
        bot.send_message(message.chat.id, "⚠️ ADMIN_MINI_APP_URL не настроен.")


def admin_kb_handler(message):
    bot.send_message(message.chat.id, "🧿 Используйте Web Admin Mini App для работы с тикетами.", reply_markup=admin_start_kb())


def _show_admin_manage_panel():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📛 Забанить", callback_data="ap_ban_prompt"),
        types.InlineKeyboardButton("✅ Разбанить", callback_data="ap_unban_prompt"),
    )
    kb.add(
        types.InlineKeyboardButton("🔁 Переключить сортировку", callback_data="ap_sort"),
        types.InlineKeyboardButton("🖥 Вернуться в панель", callback_data="ap_panel"),
    )
    bot.send_message(
        ADMIN_CHAT_ID,
        "⚙️ <b>Управление</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
        "Все основные слэш-команды продублированы кнопками ниже.",
        reply_markup=kb,
    )


def _full_stats():
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); usr = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='new'"); new_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'"); in_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='done'"); done_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE status='rejected'"); rej_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE payment_status='paid'"); paid_n = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid'"); total = int(c.fetchone()[0])
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid' AND method='stars'"); stars_r = int(c.fetchone()[0])
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid' AND method='cryptobot'"); crypt_r = int(c.fetchone()[0])
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid' AND method='lolz'"); lolz_r = int(c.fetchone()[0])
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='paid' AND method='test'"); test_r = int(c.fetchone()[0])
    since = time.time() - 86400
    c.execute("SELECT COUNT(*) FROM tickets WHERE created_at>?", (since,)); today_n = c.fetchone()[0]
    conn.close()
    mode = "🧪 тестовый режим" if TEST_MODE else "🚀 рабочий режим"
    bot.send_message(
        ADMIN_CHAT_ID,
        "📊 <b>Статистика ShokeRefund</b>\n"
        f"<i>{mode}</i>\n"
        "╭──────────────────╮\n"
        f"👥 Пользователей: <b>{usr}</b>\n"
        f"📅 Заявок за 24 часа: <b>{today_n}</b>\n"
        f"🕓 Новые: <b>{new_n}</b>\n"
        f"🟡 В работе: <b>{in_n}</b>\n"
        f"🏁 Завершены: <b>{done_n}</b>\n"
        f"❌ Отклонены: <b>{rej_n}</b>\n"
        f"💳 Оплаченных заявок: <b>{paid_n}</b>\n"
        f"💰 Общая выручка: <b>{total} ₽</b>\n"
        f"⭐ Stars: <b>{stars_r} ₽</b>\n"
        f"💎 Crypto: <b>{crypt_r} ₽</b>\n"
        f"🟣 LOLZ: <b>{lolz_r} ₽</b>\n"
        f"🧪 Тестовые оплаты: <b>{test_r} ₽</b>\n"
        "╰──────────────────╯",
    )


def _send_reminders():
    now = time.time()
    remind_thresh = now - ADMIN_REMIND_HOURS * 3600
    close_thresh = now - AUTO_CLOSE_HOURS * 3600
    conn = db(); c = conn.cursor()
    c.execute(
        "SELECT id,user_id,service,amount,last_admin_msg,last_user_msg,assigned_admin FROM tickets WHERE status='in_progress'"
    )
    rows = c.fetchall(); conn.close()
    if not rows:
        bot.send_message(ADMIN_CHAT_ID, "🔔 Активных тикетов сейчас нет.")
        return

    lines = ["🔔 <b>Тикеты, которым нужно внимание</b>\n"]
    issues = 0
    for row in rows:
        last_admin = row["last_admin_msg"] or 0
        last_user = row["last_user_msg"] or 0
        flags = []
        if last_admin < remind_thresh:
            flags.append(f"⚠️ Нет ответа админа более {ADMIN_REMIND_HOURS} ч")
        if last_user < close_thresh:
            flags.append(f"💤 Нет ответа пользователя более {AUTO_CLOSE_HOURS} ч")
        if flags:
            admin_n = get_admin_name(row["assigned_admin"]) if row["assigned_admin"] else "не назначен"
            lines.append(
                f"🎫 <b>#{row['id']}</b> · {row['service']} · <b>{int(row['amount'])} ₽</b>\n"
                f"👤 <code>{row['user_id']}</code> · 👷 {admin_n}\n"
                f"{' | '.join(flags)}\n"
            )
            issues += 1

    if issues == 0:
        bot.send_message(ADMIN_CHAT_ID, "✅ Просроченных тикетов сейчас нет.")
    else:
        bot.send_message(ADMIN_CHAT_ID, "\n".join(lines))


@bot.callback_query_handler(func=lambda c: c.data.startswith("open_"))
def on_open_ticket(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        return
    tid = int(call.data.split("_")[1])
    bot.answer_callback_query(call.id)
    send_admin_ticket_card(tid, chat_id=ADMIN_CHAT_ID, edit_mid=call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ap_"))
def on_ap(call):
    global sort_new_first
    if call.message.chat.id != ADMIN_CHAT_ID:
        return
    data = call.data

    if data == "ap_panel":
        bot.answer_callback_query(call.id)
        send_admin_panel(ADMIN_CHAT_ID, call.message.message_id)
        return

    if data == "ap_refresh":
        bot.answer_callback_query(call.id, "Обновлено")
        send_admin_panel(ADMIN_CHAT_ID, call.message.message_id)
        return

    if data == "ap_stats":
        bot.answer_callback_query(call.id)
        _full_stats()
        return

    if data == "ap_reminders":
        bot.answer_callback_query(call.id)
        _send_reminders()
        return

    if data == "ap_sort":
        sort_new_first = not sort_new_first
        mode = "сначала новые ⬆️" if sort_new_first else "сначала старые ⬇️"
        bot.answer_callback_query(call.id, f"Сортировка: {mode}")
        send_admin_panel(ADMIN_CHAT_ID, call.message.message_id)
        return

    if data == "ap_manage":
        bot.answer_callback_query(call.id)
        _show_admin_manage_panel()
        return

    if data == "ap_ban_prompt":
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_CHAT_ID, "Введите: /ban <user_id>")
        return

    if data == "ap_unban_prompt":
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_CHAT_ID, "Введите: /unban <user_id>")
        return

    status_map = {
        "ap_list_new": ("t.status='new'", (), "🕓 <b>Новые заявки</b>"),
        "ap_list_in": ("t.status='in_progress'", (), "🟡 <b>Заявки в работе</b>"),
        "ap_list_paywait": ("t.status='in_progress' AND t.payment_status='pending'", (), "💳 <b>Заявки, ожидающие оплату</b>"),
        "ap_list_done": ("t.status='done'", (), "🏁 <b>Завершённые заявки</b>"),
        "ap_list_rejected": ("t.status='rejected'", (), "❌ <b>Отклонённые заявки</b>"),
    }
    if data == "ap_list_silent":
        bot.answer_callback_query(call.id)
        _ticket_list_where(
            "⌛ <b>Тикеты без ответа администратора</b>",
            "t.status='in_progress' AND COALESCE(t.last_admin_msg,0)<?",
            (time.time() - ADMIN_REMIND_HOURS * 3600,),
        )
        return

    if data in status_map:
        bot.answer_callback_query(call.id)
        where_sql, params, title = status_map[data]
        _ticket_list_where(title, where_sql, params)


def _ticket_list_where(title, where_sql, params=()):
    conn = db(); c = conn.cursor()
    c.execute(
        f"""SELECT t.id,t.user_id,t.service,t.amount,t.payment_status,t.assigned_admin,t.updated_at
           FROM tickets t WHERE {where_sql} ORDER BY t.updated_at DESC LIMIT 20""",
        params
    )
    rows = c.fetchall(); conn.close()
    if not rows:
        bot.send_message(ADMIN_CHAT_ID, f"{title}\n\n<i>Тикетов нет.</i>")
        return
    bot.send_message(ADMIN_CHAT_ID, title)
    for row in rows:
        pay = payment_status_label(row["payment_status"])
        admin_n = get_admin_name(row["assigned_admin"]) if row["assigned_admin"] else "—"
        text = (
            f"🎫 <b>#{row['id']}</b> · {row['service']} · <b>{int(row['amount'])} ₽</b>\n"
            f"👤 <code>{row['user_id']}</code>\n"
            f"💸 {pay}\n"
            f"👷 {admin_n} · {format_dt(row['updated_at'])}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Открыть карточку", callback_data=f"open_{row['id']}"))
        bot.send_message(ADMIN_CHAT_ID, text, reply_markup=kb)
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_CHAT_ID, commands=["ban"])
def cmd_ban(message):
    parts = message.text.split()
    if len(parts) < 2: bot.send_message(ADMIN_CHAT_ID, "Использование: /ban <user_id>"); return
    try: target = int(parts[1])
    except: bot.send_message(ADMIN_CHAT_ID, "Неверный user_id."); return
    conn = db(); c = conn.cursor()
    c.execute("UPDATE users SET banned=1 WHERE user_id=?", (target,)); conn.commit(); conn.close()
    bot.send_message(ADMIN_CHAT_ID, f"🚫 <code>{target}</code> заблокирован.")
    try: send_tracked_text(target, "🚫 Ваш доступ к боту ограничен.")
    except: pass

@bot.message_handler(func=lambda m: m.chat.id == ADMIN_CHAT_ID, commands=["unban"])
def cmd_unban(message):
    parts = message.text.split()
    if len(parts) < 2: bot.send_message(ADMIN_CHAT_ID, "Использование: /unban <user_id>"); return
    try: target = int(parts[1])
    except: bot.send_message(ADMIN_CHAT_ID, "Неверный user_id."); return
    conn = db(); c = conn.cursor()
    c.execute("UPDATE users SET banned=0 WHERE user_id=?", (target,)); conn.commit(); conn.close()
    bot.send_message(ADMIN_CHAT_ID, f"✅ <code>{target}</code> разблокирован.")
    try: send_tracked_text(target, "✅ Ваш доступ восстановлен.")
    except: pass

# ╔══════════════════════════════════════════════════╗
# ║         ПОСЛЕ ЗАКРЫТИЯ ЧАТА                      ║
# ╚══════════════════════════════════════════════════╝

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "chat_closed")
def on_chat_closed(message):
    uid = message.from_user.id
    track_user(uid, message.message_id)
    if message.text == "🔄 Оформить новую заявку":
        send_tracked_text(uid, "🖥 Для новой заявки снова откройте Mini App.", markup=user_main_kb())
    else:
        send_tracked_text(uid, "🖥 Новые заявки доступны только через Mini App.",
                         markup=user_main_kb())

# ╔══════════════════════════════════════════════════╗
# ║       ФОНОВЫЕ ЗАДАЧИ: НАПОМИНАНИЯ + АВТО-CLOSE   ║
# ╚══════════════════════════════════════════════════╝

def _scheduler():
    while True:
        time.sleep(3600)
        try: _check_stale()
        except Exception as e: log.error(f"Scheduler: {e}")

def _check_stale():
    now           = time.time()
    remind_thresh = now - ADMIN_REMIND_HOURS * 3600
    close_thresh  = now - AUTO_CLOSE_HOURS   * 3600
    conn = db(); c = conn.cursor()
    c.execute("SELECT id,user_id,last_admin_msg,last_user_msg FROM tickets WHERE status='in_progress'")
    rows = c.fetchall(); conn.close()

    for row in rows:
        tid        = row["id"]
        uid        = row["user_id"]
        last_admin = row["last_admin_msg"] or 0
        last_user  = row["last_user_msg"]  or 0

        if last_user < close_thresh:
            log.info(f"Авто-закрытие #{tid}")
            close_ticket(tid, uid, "done")
            add_history(tid, "system", "auto_closed", f"Нет активности {AUTO_CLOSE_HOURS}ч")
            try: bot.send_message(ADMIN_CHAT_ID,
                f"🤖 Заявка <b>#{tid}</b> авто-закрыта — пользователь не отвечал {AUTO_CLOSE_HOURS} ч.")
            except: pass

        elif last_admin < remind_thresh:
            log.info(f"Напоминание #{tid}")
            try:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("➡️ К заявке", callback_data=f"act_reply_{tid}"))
                bot.send_message(ADMIN_CHAT_ID,
                    f"⏰ <b>Напоминание!</b> Заявка <b>#{tid}</b> — нет ответа > {ADMIN_REMIND_HOURS} ч.\n"
                    f"👤 <code>{uid}</code>",
                    reply_markup=kb
                )
                touch_admin_msg(tid)
            except: pass

# ╔══════════════════════════════════════════════════╗
# ║              MINI APP HTTP + API                ║
# ╚══════════════════════════════════════════════════╝

MINIAPP_DIR = os.path.join(os.path.dirname(__file__), "miniapp")


class MiniAppRequestHandler(BaseHTTPRequestHandler):
    server_version = "ShokeRefundMiniApp/1.0"

    def _send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if path == "/healthz":
            return self._send_json({"ok": True, "status": "healthy", "port": WEB_PORT})
        if path.startswith("/api/"):
            return self.handle_api_get(path, query)

        rel = path.lstrip("/") or "index.html"
        base_dir = os.path.abspath(MINIAPP_DIR)
        file_path = os.path.abspath(os.path.normpath(os.path.join(base_dir, rel)))
        if not file_path.startswith(base_dir):
            self.send_error(403)
            return
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")
        if not os.path.exists(file_path):
            file_path = os.path.join(base_dir, "index.html")
        return self._send_file(file_path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self.send_error(404)
            return
        return self.handle_api_post(path, self._read_json())

    def handle_api_get(self, path, query):
        init_data = query.get("initData", "")
        if path == "/api/user/active-ticket":
            auth = auth_web_user(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            ticket = find_active_ticket(auth["user_id"])
            messages = get_ticket_messages(ticket["id"]) if ticket else []
            return self._send_json({"ok": True, "ticket": ticket_to_api(ticket), "messages": messages})

        if path == "/api/admin/bootstrap":
            auth = auth_web_admin(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            return self._send_json({"ok": True, "summary": admin_summary_payload(), "tickets": list_admin_tickets()})

        if path == "/api/admin/tickets":
            auth = auth_web_admin(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            return self._send_json({"ok": True, "tickets": list_admin_tickets(query.get("status", "all"), query.get("search", ""))})

        if path.startswith("/api/admin/tickets/"):
            auth = auth_web_admin(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            parts = [p for p in path.split("/") if p]
            if len(parts) == 4:
                try:
                    tid = int(parts[3])
                except Exception:
                    return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
                ticket = get_ticket(tid)
                if not ticket:
                    return self._send_json({"ok": False, "error": "not_found"}, 404)
                return self._send_json({"ok": True, "ticket": ticket_to_api(ticket), "messages": get_ticket_messages(tid)})

        return self._send_json({"ok": False, "error": "not_found"}, 404)

    def handle_api_post(self, path, body):
        init_data = body.get("initData", "")

        if path.startswith("/api/user/tickets/") and path.endswith("/reply"):
            auth = auth_web_user(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "unauthorized"}, 401)
            try:
                tid = int(path.split("/")[4])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            ticket = get_ticket(tid)
            if not ticket or int(ticket["user_id"]) != auth["user_id"]:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            msg_text = str(body.get("text") or "").strip()
            if not msg_text:
                return self._send_json({"ok": False, "error": "empty_text"}, 400)
            add_ticket_message(tid, "user", msg_text, sender_id=auth["user_id"], sender_name="Клиент")
            touch_user_msg(tid)
            try:
                bot.send_message(ADMIN_CHAT_ID, f"📨 Сообщение из Mini App по заявке #{tid} от <code>{auth['user_id']}</code>:\n{msg_text}")
            except Exception:
                pass
            return self._send_json({"ok": True, "messages": get_ticket_messages(tid)})

        if path.startswith("/api/admin/tickets/"):
            auth = auth_web_admin(init_data)
            if not auth:
                return self._send_json({"ok": False, "error": "forbidden"}, 403)
            parts = [p for p in path.split("/") if p]
            if len(parts) < 5:
                return self._send_json({"ok": False, "error": "bad_path"}, 400)
            try:
                tid = int(parts[3])
            except Exception:
                return self._send_json({"ok": False, "error": "bad_ticket_id"}, 400)
            action = parts[4]
            ticket = get_ticket(tid)
            if not ticket:
                return self._send_json({"ok": False, "error": "not_found"}, 404)

            if action == "assign":
                assign_ticket(tid, auth["user_id"])
                add_history(tid, "admin", "assign", f"Назначено на {auth['user_id']}")
                return self._send_json({"ok": True, "ticket": ticket_to_api(get_ticket(tid))})

            if action == "status":
                status = str(body.get("status") or "").strip()
                if status not in {"new", "in_progress", "done", "rejected"}:
                    return self._send_json({"ok": False, "error": "bad_status"}, 400)
                update_status(tid, status)
                add_history(tid, "admin", "status", f"Статус изменён на {status}")
                add_ticket_message(tid, "system", f"Статус заявки изменён: {ticket_status_label(status)}")
                refreshed = get_ticket(tid)
                try:
                    upsert_ticket_card(refreshed["user_id"], refreshed)
                except Exception:
                    pass
                return self._send_json({"ok": True, "ticket": ticket_to_api(refreshed)})

            if action == "reply":
                msg_text = str(body.get("text") or "").strip()
                if not msg_text:
                    return self._send_json({"ok": False, "error": "empty_text"}, 400)
                admin_name = get_admin_name(auth["user_id"])
                add_ticket_message(tid, "admin", msg_text, sender_id=auth["user_id"], sender_name=admin_name)
                touch_admin_msg(tid)
                send_tracked_text(ticket["user_id"], f"💬 <b>{admin_name}:</b>\n{msg_text}")
                return self._send_json({"ok": True, "ticket": ticket_to_api(get_ticket(tid)), "messages": get_ticket_messages(tid)})

        return self._send_json({"ok": False, "error": "not_found"}, 404)

    def log_message(self, format, *args):
        return


def start_miniapp_server():
    if not os.path.isdir(MINIAPP_DIR):
        log.warning(f"Mini App папка не найдена: {MINIAPP_DIR}")
        return

    def _run():
        try:
            httpd = ThreadingHTTPServer((WEB_HOST, WEB_PORT), MiniAppRequestHandler)
            log.info(f"🌐 Mini App сервер поднят на http://{WEB_HOST}:{WEB_PORT}")
            httpd.serve_forever()
        except Exception as e:
            log.error(f"Mini App сервер не запустился: {e}")

    threading.Thread(target=_run, daemon=True).start()


# ╔══════════════════════════════════════════════════╗
# ║                    ЗАПУСК                        ║
# ╚══════════════════════════════════════════════════╝

def setup_bot_commands():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "Открыть стартовое меню"),
            types.BotCommand("admin", "Открыть админ-панель"),
        ])
    except Exception as e:
        log.warning(f"Не удалось установить команды бота: {e}")


if __name__ == "__main__":
    init_db()
    setup_bot_commands()
    start_miniapp_server()
    threading.Thread(target=_scheduler, daemon=True).start()
    run_mode = "TEST MODE" if TEST_MODE else "PROD MODE"
    log.info(f"🚀 ShokeRefund Bot запущен ({run_mode})")

    if SEND_STARTUP_MESSAGE and ADMIN_CHAT_ID:
        try:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"🤖 <b>Бот перезапущен</b>\n<i>{run_mode}</i>",
                reply_markup=admin_start_kb(),
            )
        except Exception as e:
            log.warning(f"Стартовое сообщение не отправлено: {e}")

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            log.error(f"Polling: {e}")
            time.sleep(5)
