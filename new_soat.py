# aza bot
# S fixed · PY
# ═══════════════════════════════════════════════════════════════
# 🔥 JONLI SOAT BOT — MUKAMMAL VERSIYA 3.0
# Barcha funksiyalar: VIP, o'yinlar, kabinet, feedback, admin panel
# ═══════════════════════════════════════════════════════════════
import asyncio, sqlite3, logging, re, io, os, random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pytz
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, FloodWaitError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, PhoneNumberInvalidError, PhoneNumberBannedError,
    PhoneNumberUnoccupiedError, ApiIdInvalidError, SendCodeUnavailableError,
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BOT_TOKEN = "8518801019:AAEh_xguZ01w_LcAam_GRagHbs987TiEruY"
API_ID = 2691229
API_HASH = "b90611f46f1a08fe9584828ff1425bc4"
DB_PATH = "soatbot.db"
DEVICE_KWARGS = dict(device_model="Samsung Galaxy S23", system_version="4.16.30-vxCUSTOM",
                    app_version="10.5.4", lang_code="uz")
TZ = pytz.timezone("Asia/Tashkent")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
router = Router()

_pending: Dict[int, Dict[str, Any]] = {}
_tasks: Dict[int, asyncio.Task] = {}
_photos: Dict[int, List[bytes]] = {}
_bio_texts: Dict[int, List[str]] = {}
_admins: set = set()
_feedback_user: Dict[int, int] = {}  # admin -> user reply mapping

# ═══════════════════════════════════════════════
# O'ZBEK TILIDA TO'LIQ LUG'AT
# ═══════════════════════════════════════════════
T = {
    "welcome": {"uz": "Assalomu alaykum! 👋\n«Jonli Soat Bot» ga xush kelibsiz!\n\nBot imkoniyatlari:\n⏰ Nikga jonli soat\n🖼 Rasmga chiroyli soat\n📝 Bio ga matn + umr/tug'ilgan kun\n🎰 O'yinlar orqali coin ishlang\n🎁 Referal va kunlik bonuslar\n💎 VIP status\n\n👇 Boshlash uchun tilni tanlang:"},
    "choose_lang": {"uz": "Tilni tanlang 👇"},
    "lang_done": {"uz": "✅ O'zbek tili tanlandi!"},
    "main_menu": {"uz": "🤖 <b>JONLI SOAT BOTI</b>\n━━━━━━━━━━━━━━━\n💰 Balans: {coins} Coin{vip}\n\n👇 Bo'limni tanlang:"},
    "btn_login": {"uz": "🔐 Ulanish"},
    "btn_clock": {"uz": "⚙️ Soat"},
    "btn_bio": {"uz": "📝 Bio"},
    "btn_games": {"uz": "🎮 O'yinlar"},
    "btn_shop": {"uz": "💎 Do'kon/VIP"},
    "btn_cabinet": {"uz": "👤 Kabinet"},
    "btn_coins": {"uz": "🎁 Bonus"},
    "btn_feedback": {"uz": "📞 Adminga"},
    "btn_lang": {"uz": "🌐 Til"},
    "vip_badge": {"uz": " 👑 VIP"},
    # Sozlamalar
    "clock_menu": {"uz": "⚙️ <b>SOAT SOZLAMALARI</b>\n\n👇 Bo'lim:"},
    "btn_nick": {"uz": "✏️ Nik soati"},
    "btn_photo": {"uz": "🖼 Rasm soati"},
    "btn_prefix": {"uz": "🏷 Emoji prefix"},
    "btn_timeformat": {"uz": "⏱ Vaqt formati"},
    "btn_stop_nick": {"uz": "⏹ Nikni to'xtatish"},
    "btn_stop_photo": {"uz": "⏹ Rasmni to'xtatish"},
    "btn_back": {"uz": "⬅️ Orqaga"},
    # Login
    "send_phone": {"uz": "🔐 <b>TELEGRAMGA ULANISH</b>\n\n📱 Telefon raqamingizni yuboring:\n\n<i>Masalan: +998901234567</i>"},
    "phone_btn": {"uz": "📱 Raqam yuborish"},
    "code_sending": {"uz": "🔄 Kod yuborilmoqda..."},
    "code_sent_app": {"uz": "📩 <b>Kod Telegramga yuborildi!</b>\n\n⚠️ <b>JUDA MUHIM!</b> Telegram bloklamasligi uchun kodning <b>boshiga BITTA HARF qo'shib</b> yuboring!\n\n✅ Masalan, kod <code>12345</code> bo'lsa: <code>a12345</code> yoki <code>x12345</code>\n❌ FAQAT raqam yubormang — <code>12345</code> noto'g'ri!\n\n<i>Bot harfni o'zi olib tashlaydi, xavfsiz.</i>"},
    "code_sent_sms": {"uz": "📲 <b>Kod SMS orqali keldi!</b>\n\n⚠️ Kod oldiga BITTA HARF qo'shib yuboring! (a12345)"},
    "resend_sms": {"uz": "📲 SMS orqali qayta yuborish"},
    "enter_2fa": {"uz": "🔐 2FA parolni kiriting:"},
    "login_ok": {"uz": "🎉 <b>Muvaffaqiyatli ulandiz!</b>"},
    "login_err": {"uz": "❌ Xato: "},
    "code_wrong": {"uz": "❌ Kod noto'g'ri! 1 ta harf qo'shib qayta kiriting:"},
    "need_login": {"uz": "⚠️ Avval 🔐 ulanish kerak!"},
    "phone_invalid": {"uz": "❌ Raqam noto'g'ri! Qayta kiriting:"},
    "phone_banned": {"uz": "❌ Raqam bloklangan!"},
    "flood_wait": {"uz": "⏳ {sec} soniya kuting"},
    "timeout_err": {"uz": "⏳ Ulanish vaqti tugadi"},
    "already_logged": {"uz": "✅ Siz allaqachon ulangansiz!"},
    "not_registered": {"uz": "❌ Bu raqamda akkaunt yo'q!"},
}

T2 = {
    # Coin
    "coin_menu": {"uz": "🎁 <b>BONUSLAR</b>\n\n📅 Kunlik: {daily} Coin\n👥 Har bir do'st: {ref} Coin"},
    "btn_daily": {"uz": "🎁 Kunlik olish"},
    "btn_ref": {"uz": "🔗 Referal havola"},
    "daily_ok": {"uz": "🎉 {amount} Coin olindi!"},
    "daily_wait": {"uz": "⏳ {h} soat {m} daqiqa kuting!"},
    "ref_text": {"uz": "🔗 <b>DO'ST CHAQIRISH</b>\n\nHavola: <code>{link}</code>\n\n👥 Do'stlar: {count} ta\n🎁 Har biriga: {bonus} Coin"},
    "balance": {"uz": "💰 <b>BALANS:</b> {coins} Coin{vip}\n\n💳 Coin sotib olish uchun admin bilan bog'laning:\n{support}\n\n👨‍💻 Admin: {admin}"},
    # Kabinet
    "cabinet": {"uz": "👤 <b>SIZNING KABINETINGIZ</b>\n\n🆔 ID: <code>{uid}</code>\n👤 Ism: {name}\n📅 Qo'shilgan: {joined}\n📊 Kunlar: {days} kun\n\n💰 Balans: {coins} Coin{vip}\n🎯 Sotib olingan nik stillar: {n_styles}\n🎯 Sotib olingan rasm stillar: {p_styles}\n👥 Taklif qilingan: {refs} ta\n\n⏰ Hozirgi rejim: {modes}"},
    "mode_none": {"uz": "⏹ To'xtatilgan"},
    "mode_nick": {"uz": "✏️ Nik soati"},
    "mode_photo": {"uz": "🖼 Rasm soati"},
    "mode_bio": {"uz": "📝 Bio"},
    # Feedback
    "feedback_menu": {"uz": "📞 <b>ADMINGA XABAR</b>\n\nXabaringizni yozing, admin tez orada javob beradi:"},
    "feedback_sent": {"uz": "✅ Xabar adminga yuborildi! Javobni kuting."},
    "feedback_reply": {"uz": "✍️ Javob yozing (userga yuboriladi):"},
    "feedback_from": {"uz": "📩 <b>Yangi xabar!</b>\n\n👤: <a href='tg://user?id={uid}'>{name}</a> (ID: <code>{uid}</code>)\n💬: {text}"},
    "feedback_ans_ok": {"uz": "✅ Javob yuborildi!"},
    # Bio
    "bio_menu": {"uz": "📝 <b>BIO SOZLAMALARI</b>\n\n💰 Balans: {coins} Coin{vip}"},
    "btn_bio_add": {"uz": "➕ Matn qo'shish"},
    "btn_bio_list": {"uz": "📋 Matnlarim"},
    "btn_bio_del": {"uz": "🗑 Matn o'chirish"},
    "btn_bio_umr": {"uz": "⏳ Umr hisoblagichi ({p} Coin)"},
    "btn_bio_bd": {"uz": "🎂 Tug'ilgan kun ({p} Coin)"},
    "btn_stop_bio": {"uz": "⏹ Bio to'xtatish"},
    "ask_bio_text": {"uz": "📝 Bio matn yuboring (10 tagacha, 70 belgigacha):"},
    "bio_text_ok": {"uz": "✅ Qo'shildi! ({c}/10)"},
    "bio_text_max": {"uz": "⚠️ 10 tadan ko'p bo'lmaydi!"},
    "bio_text_long": {"uz": "⚠️ Juda uzun! 70 belgigacha."},
    "bio_list_empty": {"uz": "📋 Matn yo'q."},
    "ask_del_bio": {"uz": "🗑 O'chirish uchun raqam kiriting (1-{c}):"},
    "bio_deleted": {"uz": "✅ O'chirildi!"},
    "ask_birth_date": {"uz": "⏳ Tug'ilgan sana: <b>kun.oy.yil</b>\n\nMasalan: <code>21.12.2005</code>"},
    "bad_date": {"uz": "❌ Noto'g'ri! Kun.Oy.Yil (21.12.2005)"},
    "umr_started": {"uz": "✅ Umr hisoblagichi yoqildi! Har daqiqa yangilanadi."},
    "ask_bd_date": {"uz": "🎂 Tug'ilgan kuningiz: <b>kun.oy</b> (yilsiz)\n\nMasalan: <code>21.12</code>"},
    "bd_started": {"uz": "✅ Tug'ilgan kun sanagichi yoqildi!"},
    "bio_stopped": {"uz": "⏹ Bio to'xtatildi!"},
    # Nick styles
    "nick_title": {"uz": "✏️ <b>NIK SOAT STILINI TANLANG</b>\n\n🆓 Oddiy — {n_price} Coin\n💎 Premium — {p_price} Coin\n\n💰 Balans: {coins}\n\n👇 Stilni tanlang:"},
    "nick_bought": {"uz": "✅ Sotib olingan"},
    "nick_started": {"uz": "✅ Nik soati yoqildi! ({name})"},
    "no_coins": {"uz": "❌ Coin yetarli emas!"},
    "style_bought": {"uz": "🎉 {name} — {price} Coinga sotib olindi!"},
    # Prefix
    "prefix_menu": {"uz": "🏷 <b>EMOJI PREFIX</b>\n\nSoat oldiga qo'yiladigan emoji/bayroq tanlang. Yoki o'zingiz yoqqan emojini yuboring.\n\nJoriy: <b>{cur}</b>"},
    "prefix_none": {"uz": "❌ Yo'q"},
    "prefix_set": {"uz": "✅ Prefix o'rnatildi: {p}"},
    # Time format
    "tf_menu": {"uz": "⏱ <b>VAQT FORMATI</b>\n\nJoriy: <b>{cur}</b>"},
    "tf_24": {"uz": "🕐 24 soat (HH:MM)"},
    "tf_12": {"uz": "🕐 12 soat (HH:MM AM/PM)"},
    "tf_date": {"uz": "📅 Sana+Vaqt (HH:MM DD.MM)"},
    "tf_set": {"uz": "✅ Format o'rnatildi!"},
    # Photo
    "photo_menu": {"uz": "🖼 <b>RASM SOAT</b>\n\nRasmlar: {count}/10 (VIP: {vip_max})"},
    "btn_add_photo": {"uz": "➕ Yangi rasm"},
    "btn_my_photos": {"uz": "🖼 Rasmlarim"},
    "btn_del_photo": {"uz": "🗑 Rasm o'chirish"},
    "photo_send": {"uz": "🖼 Yangi rasm yuboring:"},
    "photo_added": {"uz": "✅ Rasm qo'shildi! ({count}/{mx})\n\n👇 Stil tanlang:"},
    "photo_max": {"uz": "⚠️ Limit to'la! Avval rasm o'chiring."},
    "photo_color": {"uz": "🎨 Rang tanlang:"},
    "photo_pos": {"uz": "📍 Joylashuv (TEKIN):"},
    "photo_font": {"uz": "🔤 Shrift tanlang:"},
    "photo_effect": {"uz": "✨ Effekt tanlang:"},
    "photo_started": {"uz": "🎉 Rasm soati yoqildi! Har daqiqa almashadi."},
    "photo_need": {"uz": "❌ Rasm yuboring!"},
    "nick_stopped": {"uz": "⏹ Nik soati o'chirildi!"},
    "photo_stopped": {"uz": "⏹ Rasm soati o'chirildi! Rasmlar saqlandi."},
    "my_photos_empty": {"uz": "🖼 Hali rasm yo'q!"},
    "ask_del_photo": {"uz": "🗑 Nechanchi rasmni o'chirasiz? (1-{count}):"},
    "photo_deleted": {"uz": "✅ {num}-rasm o'chirildi. Qoldi: {left} ta"},
    "photo_bad_num": {"uz": "❌ Noto'g'ri raqam!"},
    "pos_tm": {"uz": "⬆️ Tepa o'rta"},
    "pos_tl": {"uz": "↖️ Tepa chap"},
    "pos_tr": {"uz": "↗️ Tepa o'ng"},
    "pos_bl": {"uz": "↙️ Past chap"},
    "pos_br": {"uz": "↘️ Past o'ng"},
    # Do'kon/VIP
    "shop_menu": {"uz": "💎 <b>DO'KON / VIP</b>\n\n💰 Balans: {coins} Coin{vip}\n\n👇 Tanlang:"},
    "btn_vip": {"uz": "👑 VIP status ({p} Coin / 30 kun)"},
    "btn_buy_coins": {"uz": "💳 Coin sotib olish"},
    "vip_already": {"uz": "👑 Sizda allaqachon VIP bor! {d} kun qoldi."},
    "vip_no_coins": {"uz": "❌ VIP uchun {p} Coin kerak!"},
    "vip_bought": {"uz": "🎉 VIP status olindi! 30 kunga barcha premium stillar bepul!"},
    "buy_coins_text": {"uz": "💳 Coin narxlari:\n\n50 Coin — Admin bilan\n100 Coin — bog'laning\n\nAdmin: {admin}"},
    # O'yinlar
    "games_menu": {"uz": "🎮 <b>O'YINLAR</b>\n\n💰 Balans: {coins} Coin\n\nOmadingizni sinab ko'ring!👇"},
    "btn_slot": {"uz": "🎰 Slot ({min}-{max} Coin)"},
    "btn_dice": {"uz": "🎲 Kubik ({min}-{max} Coin)"},
    "btn_coinflip": {"uz": "🪙 Tanga-gerb ({min}-{max} Coin)"},
    "ask_bet": {"uz": "💵 Miqdorni kiriting ({mn}-{mx} Coin oralig'ida):"},
    "bad_bet": {"uz": "❌ Noto'g'ri miqdor! {mn}-{mx} orasida kiriting."},
    "bet_not_enough": {"uz": "❌ Balansda yetarli coin yo'q!"},
    "slot_title": {"uz": "🎰 <b>SLOT MASHINASI</b>\n\nTikilgan: {bet} Coin\n3 ta bir xil tushsa — 5x yutish!\n2 ta bir xil — 2x yutish!\n\nAylantirish uchun tugmani bosing 👇"},
    "slot_spin": {"uz": "🎰 Aylantirish"},
    "slot_win5": {"uz": "🎉🎉🎉 JACKPOT! {w} Coin yutdingiz! 5x!"},
    "slot_win2": {"uz": "🎉 Yutdingiz! {w} Coin (2x)"},
    "slot_lose": {"uz": "😞 Yutqazdingiz! {bet} Coin yo'qotildi."},
    "dice_title": {"uz": "🎲 <b>KUBIK</b>\n\nTikilgan: {bet} Coin\n1-6 oralig'ida raqam tanlang. To'g'ri topsangiz 5x!\n\n👇 Raqam tanlang:"},
    "dice_win": {"uz": "🎉 Kubik {r} tushdi! To'g'ri! {w} Coin yutdingiz!"},
    "dice_lose": {"uz": "😞 Kubik {r} tushdi, {c} ni tanlagan ediz. {bet} Coin yo'qotildi."},
    "cf_title": {"uz": "🪙 <b>TANGA-GERB</b>\n\nTikilgan: {bet} Coin\nTo'g'ri topsangiz 2x!\n\n👇 Tanlang:"},
    "cf_heads": {"uz": "🪙 Gerb"},
    "cf_tails": {"uz": "🪙 Tanga"},
    "cf_win": {"uz": "🎉 To'g'ri! {w} Coin yutdingiz!"},
    "cf_lose": {"uz": "😞 {r} tushdi. {bet} Coin yo'qotildi."},
    # Admin
    "admin_enter": {"uz": "🔑 Admin parolini kiriting:"},
    "admin_ok": {"uz": "✅ Admin panelga xush kelibsiz!"},
    "admin_wrong": {"uz": "❌ Noto'g'ri parol!"},
    "admin_banned": {"uz": "❌ Siz bloklangansiz!"},
}
T.update(T2)

def t(key, lang="uz", **kw):
    e = T.get(key, {})
    txt = e.get(lang, e.get("uz", f"[{key}]"))
    try:
        return txt.format(**kw) if kw else txt
    except:
        return txt

# ═══════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════
def _db(q, p=(), fo=False, fa=False, c=False):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cur = conn.cursor()
        cur.execute(q, p)
        r = None
        if fo: r = cur.fetchone()
        elif fa: r = cur.fetchall()
        if c: conn.commit()
        return r
    except Exception as e:
        logger.error(f"DB: {e}")
        if c and conn: conn.rollback()
    finally:
        if conn: conn.close()

async def db(q, p=(), fo=False, fa=False, c=False):
    return await asyncio.to_thread(_db, q, p, fo, fa, c)

def init_db():
    _db("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        language TEXT DEFAULT 'uz', phone TEXT, session_string TEXT,
        coins INTEGER DEFAULT 0, banned INTEGER DEFAULT 0,
        is_vip INTEGER DEFAULT 0, vip_until TEXT,
        nick_status TEXT DEFAULT 'stopped', nick_style INTEGER DEFAULT 1,
        nick_prefix TEXT DEFAULT '', time_format TEXT DEFAULT '24',
        photo_status TEXT DEFAULT 'stopped', photo_style INTEGER DEFAULT 1,
        photo_color INTEGER DEFAULT 1, photo_position INTEGER DEFAULT 1,
        photo_font INTEGER DEFAULT 1, photo_effect INTEGER DEFAULT 0,
        bio_status TEXT DEFAULT 'stopped', bio_mode TEXT DEFAULT 'text',
        birth_date TEXT, birthday_date TEXT,
        referrer_id INTEGER, last_bonus TEXT,
        last_bio_idx INTEGER DEFAULT 0, last_photo_idx INTEGER DEFAULT 0,
        original_first_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""", c=True)
    _db("""CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY, value TEXT)""", c=True)
    _db("""CREATE TABLE IF NOT EXISTS user_nick_styles (
        user_id INTEGER, style_id INTEGER, PRIMARY KEY(user_id,style_id))""", c=True)
    _db("""CREATE TABLE IF NOT EXISTS user_photo_styles (
        user_id INTEGER, style_id INTEGER, PRIMARY KEY(user_id,style_id))""", c=True)
    _db("""CREATE TABLE IF NOT EXISTS user_photos (
        user_id INTEGER, idx INTEGER, photo BLOB, PRIMARY KEY(user_id,idx))""", c=True)
    _db("""CREATE TABLE IF NOT EXISTS user_bio_texts (
        user_id INTEGER, idx INTEGER, text TEXT, PRIMARY KEY(user_id,idx))""", c=True)
    defaults = {
        "admin_code": "AzA1221", "daily_bonus": "10", "ref_bonus": "20",
        "nick_normal_price": "15", "nick_premium_price": "50",
        "photo_normal_price": "30", "photo_premium_price": "70",
        "umr_price": "100", "birthday_price": "80",
        "vip_price": "500", "vip_days": "30", "vip_max_photos": "30",
        "slot_min": "5", "slot_max": "50", "slot_mult2": "2", "slot_mult5": "5",
        "dice_min": "5", "dice_max": "30", "dice_mult": "5",
        "cf_min": "5", "cf_max": "100", "cf_mult": "2",
        "admin_contact": "@admin", "support_text": "Adminga yozing.",
    }
    for k,v in defaults.items():
        _db("INSERT OR IGNORE INTO system_settings VALUES(?,?)",(k,v),c=True)

init_db()

async def get_s(k, d=""):
    r = await db("SELECT value FROM system_settings WHERE key=?",(k,),fo=True)
    return r[0] if r and r[0] else d
async def set_s(k, v):
    await db("INSERT INTO system_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,v),c=True)

async def get_lang(uid):
    r = await db("SELECT language FROM users WHERE user_id=?",(uid,),fo=True)
    return r[0] if r and r[0] else "uz"
async def set_lang(uid, l):
    await db("UPDATE users SET language=? WHERE user_id=?",(l,uid),c=True)

async def is_banned(uid):
    r = await db("SELECT banned FROM users WHERE user_id=?",(uid,),fo=True)
    return bool(r and r[0])

async def is_vip(uid):
    r = await db("SELECT is_vip,vip_until FROM users WHERE user_id=?",(uid,),fo=True)
    if not r or not r[0]: return False
    try:
        until = datetime.fromisoformat(r[1]) if r[1] else None
        if until and until > datetime.now(TZ): return True
        # VIP tugagan
        await db("UPDATE users SET is_vip=0,vip_until=NULL WHERE user_id=?",(uid,),c=True)
    except: pass
    return False

async def vip_badge(uid):
    if await is_vip(uid): return " " + t("vip_badge")
    return ""

async def max_photos(uid):
    if await is_vip(uid): return int(await get_s("vip_max_photos","30"))
    return 10

async def get_coins(uid):
    r = await db("SELECT coins FROM users WHERE user_id=?",(uid,),fo=True)
    return r[0] if r and r[0] is not None else 0

async def add_coins(uid, amt):
    await db("UPDATE users SET coins=coins+? WHERE user_id=?",(amt,uid),c=True)

async def reg_user(uid, un, fn, ref=None):
    ex = await db("SELECT user_id FROM users WHERE user_id=?",(uid,),fo=True)
    if not ex:
        rf = ref if ref and ref!=uid else None
        await db("INSERT INTO users(user_id,username,full_name,referrer_id) VALUES(?,?,?,?)",(uid,un,fn,rf),c=True)
        await db("INSERT OR IGNORE INTO user_nick_styles VALUES(?,?)",(uid,1),c=True)
        await db("INSERT OR IGNORE INTO user_photo_styles VALUES(?,?)",(uid,1),c=True)
        if rf:
            b = int(await get_s("ref_bonus","20"))
            await add_coins(rf, b)
    else:
        await db("UPDATE users SET username=?,full_name=? WHERE user_id=?",(un,fn,uid),c=True)

# ═══════════════════════════════════════════════
# STILLAR — NICK
# 7 oddiy + 7 premium = 14
# ═══════════════════════════════════════════════
NICK_STYLES = {
    1:  {"name": "Klassik",         "cat": "normal",  "d": {str(i):str(i) for i in range(10)}},
    2:  {"name": "Kichik pastki",   "cat": "normal",  "d": {"0":"₀","1":"₁","2":"₂","3":"₃","4":"₄","5":"₅","6":"₆","7":"₇","8":"₈","9":"₉"}},
    3:  {"name": "Yuqori",          "cat": "normal",  "d": {"0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵","6":"⁶","7":"⁷","8":"⁸","9":"⁹"}},
    4:  {"name": "[Qavsli]",        "cat": "normal",  "pre":"[","suf":"]",  "d":{str(i):str(i) for i in range(10)}},
    5:  {"name": "Blok qalin",      "cat": "normal",  "d": {"0":"𝟶","1":"𝟷","2":"𝟸","3":"𝟹","4":"𝟺","5":"𝟻","6":"𝟼","7":"𝟽","8":"𝟾","9":"𝟿"}},
    6:  {"name": "Chiroyli serif",  "cat": "normal",  "d": {"0":"𝟎","1":"𝟏","2":"𝟐","3":"𝟑","4":"𝟒","5":"𝟓","6":"𝟔","7":"𝟕","8":"𝟖","9":"𝟗"}},
    7:  {"name": "(Yumaloq)",       "cat": "normal",  "pre":"(","suf":")",  "d":{str(i):str(i) for i in range(10)}},
    8:  {"name": "💎 Aylana to'liq","cat": "premium", "d": {"0":"⓿","1":"❶","2":"❷","3":"❸","4":"❹","5":"❺","6":"❻","7":"❼","8":"❽","9":"❾"}},
    9:  {"name": "💎 Qalin yumaloq","cat": "premium", "d": {"0":"𝟬","1":"𝟭","2":"𝟮","3":"𝟯","4":"𝟰","5":"𝟱","6":"𝟲","7":"𝟳","8":"𝟴","9":"𝟵"}},
    10: {"name": "💎 Bo'sh aylana", "cat": "premium", "d": {"0":"⓪","1":"①","2":"②","3":"③","4":"④","5":"⑤","6":"⑥","7":"⑦","8":"⑧","9":"⑨"}},
    11: {"name": "💎 Emoji raqam",  "cat": "premium", "d": {"0":"0️⃣","1":"1️⃣","2":"2️⃣","3":"3️⃣","4":"4️⃣","5":"5️⃣","6":"6️⃣","7":"7️⃣","8":"8️⃣","9":"9️⃣"}},
    12: {"name": "💎 Jingalak",     "cat": "premium", "pre":"【","suf":"】","d":{str(i):str(i) for i in range(10)}},
    13: {"name": "💎 Chiziqli",     "cat": "premium", "d": {"0":"𝟘","1":"𝟙","2":"𝟚","3":"𝟛","4":"𝟜","5":"𝟝","6":"𝟞","7":"𝟟","8":"𝟠","9":"𝟡"}},
    14: {"name": "💎 Yulduzli",     "cat": "premium", "pre":"★ ","suf":" ★","d":{str(i):str(i) for i in range(10)}},
}

PHOTO_STYLES = {
    1:  {"name": "Oddiy HH:MM",         "cat": "normal",  "fmt":"{t}",        "shadow":False},
    2:  {"name": "• Nuqtali •",         "cat": "normal",  "fmt":"• {t} •",    "shadow":False},
    3:  {"name": "[Qavsli]",            "cat": "normal",  "fmt":"[{t}]",      "shadow":False},
    4:  {"name": "Qora quti",           "cat": "normal",  "fmt":"{t}",        "box":True},
    5:  {"name": "~ Vintage ~",         "cat": "normal",  "fmt":"~ {t} ~",    "shadow":False},
    6:  {"name": "💎 Neon glow",        "cat": "premium", "fmt":"{t}",        "neon":True},
    7:  {"name": "💎 Katta qalin quti", "cat": "premium", "fmt":"{t}",        "boldbox":True},
    8:  {"name": "💎 ⌚ Soat belgili",  "cat": "premium", "fmt":"⌚ {t}",     "shadow":True},
    9:  {"name": "💎 ━ Chiziqli ━",     "cat": "premium", "fmt":"━ {t} ━",    "shadow":True},
    10: {"name": "💎 3D soya",          "cat": "premium", "fmt":"{t}",        "shadow":True, "soff":3},
}

COLORS = {
    1:{"n":"⚪ Oq","c":(255,255,255)},
    2:{"n":"🟡 Oltin","c":(255,215,0)},
    3:{"n":"🔵 Moviy","c":(0,200,255)},
    4:{"n":"🌸 Pushti","c":(255,105,180)},
    5:{"n":"🔴 Qizil","c":(255,50,50)},
    6:{"n":"🟢 Yashil","c":(50,255,100)},
}

POSITIONS = {1:"top_mid",2:"top_left",3:"top_right",4:"bot_left",5:"bot_right"}

PHOTO_FONTS = {
    1: {"name": "Oddiy qalin", "file": "DejaVuSans-Bold.ttf"},
    2: {"name": "Yozuvli",     "file": "DejaVuSerif-Bold.ttf"},
    3: {"name": "Keng",        "file": "DejaVuSans-Bold.ttf"},
}

EFFECTS = {
    0: {"name": "Effektsiz"},
    1: {"name": "Blur orqa fon"},
    2: {"name": "Qora quti"},
}

PREFIX_OPTIONS = ["","⏰","🕐","⌚","⭐","🔥","💎","✨","🌙","☀️","🇺🇿","❤️","🚀","👑","🎯","⚡"]

def fmt_time_str(tformat):
    n = datetime.now(TZ)
    if tformat == "12":
        return n.strftime("%I:%M %p")
    elif tformat == "date":
        return n.strftime("%H:%M %d.%m")
    return n.strftime("%H:%M")

def fmt_nick_time(sid, prefix="", tformat="24"):
    tstr = fmt_time_str(tformat)
    s = NICK_STYLES.get(sid, NICK_STYLES[1])
    d = s.get("d",{})
    r = "".join(d.get(c,c) for c in tstr)
    res = f"{s.get('pre','')}{r}{s.get('suf','')}"
    return f"{prefix} {res}" if prefix else res

def _pos_xy(w,h,tw,th,pid,pad):
    m = int(min(w,h)*0.05)
    p = POSITIONS.get(pid,"top_mid")
    if p=="top_mid":  return (w-tw)/2, m
    if p=="top_left": return m, m
    if p=="top_right":return w-tw-m, m
    if p=="bot_left": return m, h-th-m-pad*2
    if p=="bot_right":return w-tw-m, h-th-m-pad*2
    return (w-tw)/2, m

def draw_clock_img(img_bytes, sid, cid, pid, font_id=1, effect=0):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        if effect == 1:
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
        draw = ImageDraw.Draw(img)
        tstr = fmt_time_str("24")
        w,h = img.size
        fs = int(min(w,h)*0.14)
        font = None
        font_name = PHOTO_FONTS.get(font_id, PHOTO_FONTS[1])["file"]
        for p in [font_name, "arialbd.ttf","DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
            try:
                font = ImageFont.truetype(p,fs); break
            except: continue
        if not font: font = ImageFont.load_default()
        st = PHOTO_STYLES.get(sid, PHOTO_STYLES[1])
        txt = st["fmt"].format(t=tstr)
        col = COLORS.get(cid,COLORS[1])["c"]
        bb = draw.textbbox((0,0),txt,font=font)
        tw,th = bb[2]-bb[0], bb[3]-bb[1]
        pad = int(fs*0.3)
        x,y = _pos_xy(w,h,tw,th,pid,pad)
        ov = Image.new("RGBA",img.size,(0,0,0,0))
        od = ImageDraw.Draw(ov)
        if st.get("box") or st.get("boldbox") or effect==2:
            od.rectangle([x-pad,y-pad,x+tw+pad,y+th+pad],fill=(0,0,0,180 if st.get("boldbox") else 140))
        if st.get("neon"):
            for ox in range(-2,3):
                for oy in range(-2,3):
                    if ox or oy: od.text((x+ox,y+oy),txt,font=font,fill=(*col,180))
        elif st.get("shadow"):
            od.text((x+st.get("soff",2),y+st.get("soff",2)),txt,font=font,fill=(0,0,0,200))
        od.text((x,y),txt,font=font,fill=col)
        img = Image.alpha_composite(img,ov)
        out = io.BytesIO()
        img.convert("RGB").save(out,"JPEG",quality=92)
        return out.getvalue()
    except Exception as e:
        logger.error(f"draw: {e}"); return None

# ═══════════════════════════════════════════════
# BIO, PHOTO YORDAMCHI FUNKSIYALARI
# ═══════════════════════════════════════════════
def calc_age_text(bd: str) -> str:
    try:
        b = datetime.strptime(bd,"%d.%m.%Y").replace(tzinfo=TZ)
        n = datetime.now(TZ)
        d = n - b
        y = d.days//365; mo = (d.days%365)//30; da = (d.days%365)%30
        return f"Siz {y}y {mo}oy {da}kun {n.hour}s {n.minute}daq {n.second}son yashadingiz"
    except: return "Hisoblanmoqda..."

def calc_bd_text(bd: str) -> str:
    try:
        n = datetime.now(TZ)
        d,m = map(int,bd.split("."))
        nb = n.replace(day=d,month=m,year=n.year)
        if nb < n: nb = nb.replace(year=n.year+1)
        dl = nb - n; days = dl.days
        hrs = int(dl.seconds//3600); mnt = int((dl.seconds%3600)//60)
        if days==0: return f"🎂 Bugun! {hrs}s {mnt}daq qoldi"
        return f"🎂 Tug'ilgan kungacha: {days}kun {hrs}s {mnt}daq"
    except: return "Hisoblanmoqda..."

def load_bio_texts(uid) -> List[str]:
    if uid in _bio_texts: return _bio_texts[uid]
    rows = _db("SELECT idx,text FROM user_bio_texts WHERE user_id=? ORDER BY idx",(uid,),fa=True)
    tx = [r[1] for r in (rows or [])]
    _bio_texts[uid] = tx
    return tx

def save_bio_text(uid, text):
    tx = load_bio_texts(uid); tx.append(text[:70])
    _db("INSERT INTO user_bio_texts VALUES(?,?,?)",(uid,len(tx),text[:70]),c=True)
    _bio_texts[uid] = tx

def del_bio_text(uid, idx):
    tx = load_bio_texts(uid)
    if 1<=idx<=len(tx):
        del tx[idx-1]
        _db("DELETE FROM user_bio_texts WHERE user_id=?",(uid,),c=True)
        for i,x in enumerate(tx,1): _db("INSERT INTO user_bio_texts VALUES(?,?,?)",(uid,i,x),c=True)
        _bio_texts[uid] = tx
        return True
    return False

def load_user_photos(uid) -> List[bytes]:
    if uid in _photos and _photos[uid]: return _photos[uid]
    rows = _db("SELECT idx,photo FROM user_photos WHERE user_id=? ORDER BY idx",(uid,),fa=True)
    ps = [r[1] for r in (rows or [])]
    _photos[uid] = ps
    return ps

def add_user_photo(uid, data):
    ps = load_user_photos(uid)
    if len(ps) >= 50: return False  # yuqori chegara (VIP gacha)
    ps.append(data)
    _db("INSERT INTO user_photos VALUES(?,?,?)",(uid,len(ps),data),c=True)
    _photos[uid] = ps
    return True

def del_user_photo(uid, num):
    ps = load_user_photos(uid)
    if 1<=num<=len(ps):
        del ps[num-1]
        _db("DELETE FROM user_photos WHERE user_id=?",(uid,),c=True)
        for i,p in enumerate(ps,1): _db("INSERT INTO user_photos VALUES(?,?,?)",(uid,i,p),c=True)
        _photos[uid] = ps
        return True
    return False

# ═══════════════════════════════════════════════
# WORKER — nik + rasm + bio
# ═══════════════════════════════════════════════
async def profile_worker(uid, sess):
    client = None
    try:
        client = TelegramClient(StringSession(sess),API_ID,API_HASH,**DEVICE_KWARGS)
        await client.connect()
        if not await client.is_user_authorized():
            await db("UPDATE users SET nick_status='stopped',photo_status='stopped',bio_status='stopped',session_string=NULL WHERE user_id=?",(uid,),c=True)
            return
        me = await client.get_me()
        base = (me.first_name or "User").strip() or "User"
        await db("UPDATE users SET original_first_name=? WHERE user_id=? AND (original_first_name IS NULL OR original_first_name='')",(base,uid),c=True)
        while True:
            u = await db("SELECT nick_status,nick_style,nick_prefix,time_format,photo_status,photo_style,photo_color,photo_position,photo_font,photo_effect,bio_status,bio_mode,birth_date,birthday_date,last_bio_idx,last_photo_idx,original_first_name FROM users WHERE user_id=?",(uid,),fo=True)
            if not u: break
            ns,nst,pref,tf,ps,pst,pc,pp,pf,peff,bs,bm,bdr,bdd,lbi,lpi,ofn = u
            if ns=='stopped' and ps=='stopped' and bs=='stopped':
                try:
                    orig = ofn or base
                    if me.first_name and me.first_name!=orig:
                        await client(functions.account.UpdateProfileRequest(first_name=orig))
                except: pass
                break
            # VIP tekshiruvi
            vip = await is_vip(uid)
            # NIK
            if ns=='active':
                try:
                    tstr = fmt_nick_time(nst or 1, pref or "", tf or "24")
                    nn = f"{base} {tstr}"
                    if me.first_name != nn:
                        await client(functions.account.UpdateProfileRequest(first_name=nn))
                        me.first_name = nn
                except FloodWaitError as e: await asyncio.sleep(e.seconds)
                except: pass
            else:
                try:
                    orig = ofn or base
                    if me.first_name and me.first_name!=orig:
                        await client(functions.account.UpdateProfileRequest(first_name=orig))
                        me.first_name = orig
                except: pass
            # RASM
            if ps=='active':
                mx = await max_photos(uid)
                photos = load_user_photos(uid)[:mx]
                if photos:
                    try:
                        np_ = len(photos); ci = (int(lpi)+1) % np_
                        ed = await asyncio.to_thread(draw_clock_img, photos[ci], pst or 1, pc or 1, pp or 1, pf or 1, peff or 0)
                        if ed:
                            old_ids=[]
                            try:
                                op = await client(functions.photos.GetUserPhotosRequest(user_id="me",offset=0,max_id=0,limit=20))
                                old_ids = list(op.photos)
                            except: pass
                            f = await client.upload_file(ed,file_name="c.jpg")
                            await client(functions.photos.UploadProfilePhotoRequest(file=f))
                            await db("UPDATE users SET last_photo_idx=? WHERE user_id=?",(ci,uid),c=True)
                            if old_ids:
                                try: await client(functions.photos.DeletePhotosRequest(id=old_ids))
                                except: pass
                    except FloodWaitError as e: await asyncio.sleep(e.seconds)
                    except Exception as e: logger.debug(f"photo {uid}: {e}")
            # BIO
            if bs=='active':
                try:
                    bt = ""
                    if bm=="umr" and bdr: bt = calc_age_text(bdr)
                    elif bm=="birthday" and bdd: bt = calc_bd_text(bdd)
                    elif bm=="text":
                        tx = load_bio_texts(uid)
                        if tx:
                            nt = len(tx); ci = (int(lbi)+1) % nt; bt = tx[ci]
                            await db("UPDATE users SET last_bio_idx=? WHERE user_id=?",(ci,uid),c=True)
                    if bt and me.about != bt[:70]:
                        await client(functions.account.UpdateProfileRequest(about=bt[:70]))
                        me.about = bt
                except FloodWaitError as e: await asyncio.sleep(e.seconds)
                except: pass
            now = datetime.now(TZ)
            await asyncio.sleep(max(60-now.second,1))
    except asyncio.CancelledError: pass
    except Exception as e: logger.error(f"worker {uid}: {e}")
    finally:
        if client and client.is_connected():
            try: await client.disconnect()
            except: pass

def start_worker(uid, sess):
    old = _tasks.pop(uid,None)
    if old and not old.done(): old.cancel()
    _tasks[uid] = asyncio.create_task(profile_worker(uid,sess))

def stop_worker(uid):
    tk = _tasks.pop(uid,None)
    if tk and not tk.done(): tk.cancel()

def restart_worker(uid):
    """Agar worker ishlayotgan bo'lsa, sessiyani qayta olib qayta ishga tushirish"""
    s = _db("SELECT session_string,nick_status,photo_status,bio_status FROM users WHERE user_id=?",(uid,),fo=True)
    if s and s[0] and (s[1]=='active' or s[2]=='active' or s[3]=='active'):
        start_worker(uid, s[0])

# ═══════════════════════════════════════════════
# STATES & KEYBOARDS
# ═══════════════════════════════════════════════
class St(StatesGroup):
    lang=State(); phone=State(); code=State(); passw=State()
    add_photo=State(); photo_style=State(); photo_color=State()
    photo_pos=State(); photo_font=State(); photo_effect=State(); del_photo=State()
    bio_add=State(); bio_del=State(); bio_umr=State(); bio_bd=State()
    prefix=State(); timeformat=State()
    bet=State(); cf_bet=State(); dice_bet=State()
    feedback=State(); fb_reply=State()
    adm_code=State(); adm_val=State(); adm_bal_who=State()
    adm_bal_amt=State(); adm_bc=State(); adm_ban=State()

def menu_kb(lang="uz"):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t("btn_login",lang)), KeyboardButton(text=t("btn_clock",lang))],
        [KeyboardButton(text=t("btn_bio",lang)), KeyboardButton(text=t("btn_games",lang))],
        [KeyboardButton(text=t("btn_shop",lang)), KeyboardButton(text=t("btn_cabinet",lang))],
        [KeyboardButton(text=t("btn_coins",lang)), KeyboardButton(text=t("btn_feedback",lang))],
        [KeyboardButton(text=t("btn_lang",lang))],
    ],resize_keyboard=True)

def lang_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇿 O'zbekcha")],
    ],resize_keyboard=True,one_time_keyboard=True)

LANG_MAP = {"🇺🇿 O'zbekcha":"uz"}

def phone_kb(lang="uz"):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t("phone_btn",lang),request_contact=True)],
        [KeyboardButton(text=t("btn_back",lang))],
    ],resize_keyboard=True)

def clock_inline(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_nick",lang),callback_data="nick_menu")],
        [InlineKeyboardButton(text=t("btn_photo",lang),callback_data="photo_menu")],
        [InlineKeyboardButton(text=t("btn_prefix",lang),callback_data="prefix_menu")],
        [InlineKeyboardButton(text=t("btn_timeformat",lang),callback_data="tf_menu")],
        [InlineKeyboardButton(text=t("btn_stop_nick",lang),callback_data="stop_nick")],
        [InlineKeyboardButton(text=t("btn_stop_photo",lang),callback_data="stop_photo")],
    ])

def photo_menu_kb(lang,cnt,mx):
    btns = [
        [InlineKeyboardButton(text=t("btn_add_photo",lang),callback_data="photo_add")],
    ]
    if cnt>0:
        btns.append([InlineKeyboardButton(text=t("btn_my_photos",lang),callback_data="photo_list")])
        btns.append([InlineKeyboardButton(text=t("btn_del_photo",lang),callback_data="photo_del")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def bio_kb(lang,up,bp):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_bio_add",lang),callback_data="bio_add")],
        [InlineKeyboardButton(text=t("btn_bio_list",lang),callback_data="bio_list"),
         InlineKeyboardButton(text=t("btn_bio_del",lang),callback_data="bio_del")],
        [InlineKeyboardButton(text=t("btn_bio_umr",lang,p=up),callback_data="bio_umr")],
        [InlineKeyboardButton(text=t("btn_bio_bd",lang,p=bp),callback_data="bio_bd")],
        [InlineKeyboardButton(text=t("btn_stop_bio",lang),callback_data="stop_bio")],
    ])

def games_kb(lang,smin,smax,dmin,dmax,cmin,cmax):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_slot",lang,min=smin,max=smax),callback_data="game_slot")],
        [InlineKeyboardButton(text=t("btn_dice",lang,min=dmin,max=dmax),callback_data="game_dice")],
        [InlineKeyboardButton(text=t("btn_coinflip",lang,min=cmin,max=cmax),callback_data="game_cf")],
    ])

def shop_kb(lang,vprice):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_vip",lang,p=vprice),callback_data="buy_vip")],
        [InlineKeyboardButton(text=t("btn_buy_coins",lang),callback_data="buy_coins")],
    ])

def all_variants(key): return list(T[key].values())


# ═══════════════════════════════════════════════
# /START, LANG, MAIN MENU
# ═══════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    if await is_banned(uid):
        await msg.answer(t("admin_banned","uz")); return
    ref=None
    parts = (msg.text or "").split(maxsplit=1)
    if len(parts)>1 and parts[1].isdigit(): ref=int(parts[1])
    await reg_user(uid, msg.from_user.username, msg.from_user.full_name, ref)
    rl = await db("SELECT language FROM users WHERE user_id=?",(uid,),fo=True)
    if not rl or not rl[0]:
        await msg.answer(t("welcome","uz"),parse_mode="HTML")
        await state.set_state(St.lang); return
    lang = rl[0]
    coins = await get_coins(uid); vb = await vip_badge(uid)
    await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML")

@router.message(St.lang)
async def pick_lang(msg: Message, state: FSMContext):
    uid=msg.from_user.id
    if msg.text not in LANG_MAP:
        await msg.answer("👇 Tugmadan tanlang:"); return
    lang = LANG_MAP[msg.text]
    await set_lang(uid,lang); await state.clear()
    await msg.answer(t("lang_done",lang))
    coins=await get_coins(uid); vb=await vip_badge(uid)
    await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML")

@router.message(F.text.in_(all_variants("btn_lang")))
async def ch_lang(msg: Message):
    lang=await get_lang(msg.from_user.id)
    await msg.answer(t("choose_lang",lang),reply_markup=lang_kb())

@router.message(F.text.in_(all_variants("btn_coins")))
async def btn_coins(msg: Message):
    lang=await get_lang(msg.from_user.id)
    daily=await get_s("daily_bonus","10"); refb=await get_s("ref_bonus","20")
    btns=[[InlineKeyboardButton(text=t("btn_daily",lang),callback_data="daily")],
          [InlineKeyboardButton(text=t("btn_ref",lang),callback_data="ref")]]
    await msg.answer(t("coin_menu",lang,daily=daily,ref=refb),
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")

@router.message(F.text.in_(all_variants("btn_cabinet")))
async def btn_cabinet(msg: Message):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if await is_banned(uid): await msg.answer(t("admin_banned",lang)); return
    r = await db("SELECT full_name,username,created_at,nick_status,photo_status,bio_status,is_vip FROM users WHERE user_id=?",(uid,),fo=True)
    if not r: return
    name,un,created,ns,ps,bs,vip = r
    try:
        d = (datetime.now(TZ) - datetime.fromisoformat(created).replace(tzinfo=TZ)).days
    except: d=0
    refs = (await db("SELECT COUNT(*) FROM users WHERE referrer_id=?",(uid,),fo=True))[0]
    n_styles = (await db("SELECT COUNT(*) FROM user_nick_styles WHERE user_id=?",(uid,),fo=True))[0]
    p_styles = (await db("SELECT COUNT(*) FROM user_photo_styles WHERE user_id=?",(uid,),fo=True))[0]
    coins=await get_coins(uid); vb=await vip_badge(uid)
    modes=[]
    if ns=='active': modes.append(t("mode_nick",lang))
    if ps=='active': modes.append(t("mode_photo",lang))
    if bs=='active': modes.append(t("mode_bio",lang))
    mstr = ", ".join(modes) if modes else t("mode_none",lang)
    nm = name or (f"@{un}" if un else "—")
    await msg.answer(t("cabinet",lang,uid=uid,name=nm,joined=created[:10] if created else "—",days=d,
                       coins=coins,vip=vb,n_styles=n_styles,p_styles=p_styles,refs=refs,modes=mstr),parse_mode="HTML")

@router.message(F.text.in_(all_variants("btn_feedback")))
async def btn_feedback(msg: Message, state: FSMContext):
    lang=await get_lang(msg.from_user.id)
    await msg.answer(t("feedback_menu",lang))
    await state.set_state(St.feedback)

@router.message(St.feedback)
async def fb_recv(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    txt = (msg.text or "").strip()
    if not txt: await msg.answer(t("feedback_menu",lang)); return
    # Admin ID (admin kodini biladigan odam yo'q, admin_contact ga javoban - shuning uchun settings dagi admin contact userini aniqlab bo'lmaydi,
    # biz adminlarga (kod bilib kirganlarga) va admin_code egasiga yuboramiz - _admins setidagi odamlarga)
    name = msg.from_user.full_name or "User"
    sent = 0
    admin_contact = await get_s("admin_contact","")
    # Admin kontaktga yuborish uchun username ni olamiz
    target_username = admin_contact.lstrip("@") if admin_contact else None
    if target_username:
        try:
            # Bu yerda xabarni adminga forward qilamiz - chat ID aniq bo'lmagani uchun izoh qoldiramiz
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Javob yozish", callback_data=f"fb_reply_{uid}")]])
            # Faqat _admins dagilarga (aktiv adminlarga) yuborish
            for aid in list(_admins):
                try:
                    await msg.bot.send_message(aid, t("feedback_from","uz",uid=uid,name=name,text=txt),
                                               reply_markup=kb,parse_mode="HTML")
                    _feedback_user[aid] = uid
                    sent += 1
                except: pass
        except: pass
    await msg.answer(t("feedback_sent",lang),reply_markup=ReplyKeyboardRemove())
    await state.clear()
    # Menyu qaytarish
    coins=await get_coins(uid); vb=await vip_badge(uid)
    await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML")

@router.callback_query(F.data.startswith("fb_reply_"))
async def fb_reply_cb(call: CallbackQuery, state: FSMContext):
    aid = call.from_user.id
    if aid not in _admins: return
    try:
        target = int(call.data.split("_")[2])
    except: return
    _feedback_user[aid] = target
    await call.message.answer(t("feedback_reply","uz"))
    await state.set_state(St.fb_reply)
    await call.answer()

@router.message(St.fb_reply)
async def fb_reply_send(msg: Message, state: FSMContext):
    aid = msg.from_user.id
    target = _feedback_user.get(aid)
    if not target: await state.clear(); return
    try:
        await msg.bot.send_message(target, f"📩 <b>Admin javobi:</b>\n\n{msg.text}",parse_mode="HTML")
        await msg.answer(t("feedback_ans_ok","uz"))
    except Exception as e:
        await msg.answer(f"❌ Yuborib bo'lmadi: {e}")
    _feedback_user.pop(aid,None)
    await state.clear()

# ═══════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════
@router.message(F.text.in_(all_variants("btn_login")))
async def btn_login(msg: Message, state: FSMContext):
    uid=msg.from_user.id
    if await is_banned(uid): await msg.answer(t("admin_banned","uz")); return
    lang=await get_lang(uid)
    s = await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if s and s[0]:
        await msg.answer(t("already_logged",lang),reply_markup=menu_kb(lang)); return
    await msg.answer(t("send_phone",lang),reply_markup=phone_kb(lang),parse_mode="HTML")
    await state.set_state(St.phone)

async def send_code_safely(phone, force_sms=False):
    client = TelegramClient(StringSession(),API_ID,API_HASH,**DEVICE_KWARGS)
    try:
        await asyncio.wait_for(client.connect(),timeout=30)
    except:
        return None,None,None,"timeout"
    if not client.is_connected():
        try: await client.disconnect()
        except: pass
        return None,None,None,"not_connected"
    try:
        res = await asyncio.wait_for(client.send_code_request(phone,force_sms=force_sms),timeout=30)
        tn = type(res.type).__name__.lower()
        via = "sms" if "sms" in tn else ("call" if "call" in tn else "app")
        return client, res.phone_code_hash, via, None
    except FloodWaitError as e:
        try: await client.disconnect()
        except: pass
        return None,None,None,f"flood:{e.seconds}"
    except PhoneNumberInvalidError:
        try: await client.disconnect()
        except: pass
        return None,None,None,"invalid_phone"
    except PhoneNumberBannedError:
        try: await client.disconnect()
        except: pass
        return None,None,None,"banned_phone"
    except PhoneNumberUnoccupiedError:
        try: await client.disconnect()
        except: pass
        return None,None,None,"not_registered"
    except SendCodeUnavailableError:
        try: await client.disconnect()
        except: pass
        return None,None,None,"unavail"
    except ApiIdInvalidError:
        try: await client.disconnect()
        except: pass
        return None,None,None,"api_bad"
    except Exception as e:
        logger.exception(f"send_code: {e}")
        try: await client.disconnect()
        except: pass
        return None,None,None,str(e)

def extract_code(raw): return "".join(filter(str.isdigit, raw or ""))
def normalize_phone(raw):
    c = re.sub(r"[^\d+]","",(raw or "").strip())
    return c if c.startswith("+") else "+"+c

@router.message(St.phone)
async def proc_phone(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if await is_banned(uid): await msg.answer(t("admin_banned",lang)); return
    if msg.text and msg.text.strip()==t("btn_back",lang):
        await state.clear()
        coins=await get_coins(uid); vb=await vip_badge(uid)
        await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML"); return
    if msg.contact: rp = msg.contact.phone_number
    elif msg.text: rp = msg.text
    else: await msg.answer(t("phone_invalid",lang)); return
    phone = normalize_phone(rp)
    if len(phone)<10:
        await msg.answer(t("phone_invalid",lang)); return
    wait = await msg.answer(t("code_sending",lang),reply_markup=ReplyKeyboardRemove())
    old = _pending.pop(uid,None)
    if old and old.get("client"):
        try: await old["client"].disconnect()
        except: pass
    cl,ph,via,err = await send_code_safely(phone)
    if err:
        if err.startswith("flood:"): et = t("flood_wait",lang,sec=err.split(":")[1])
        elif err=="invalid_phone": et = t("phone_invalid",lang)
        elif err=="banned_phone": et = t("phone_banned",lang)
        elif err=="not_registered": et = t("not_registered",lang)
        elif err in ("timeout","not_connected"): et = t("timeout_err",lang)
        else: et = t("login_err",lang)+str(err)
        await wait.edit_text(et,parse_mode="HTML")
        coins=await get_coins(uid); vb=await vip_badge(uid)
        await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML")
        await state.clear(); return
    _pending[uid]={"client":cl,"phone":phone,"hash":ph}
    await state.update_data(phone=phone); await state.set_state(St.code)
    txt = t("code_sent_sms",lang) if via=="sms" else t("code_sent_app",lang)
    kb = None
    if via!="sms":
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("resend_sms",lang),callback_data="resend_sms")]])
    await wait.edit_text(txt,reply_markup=kb,parse_mode="HTML")

@router.callback_query(F.data=="resend_sms")
async def resend_sms_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    info=_pending.get(uid)
    if not info: await call.answer("❌ /start",show_alert=True); return
    await call.answer("🔄 SMS...")
    if info.get("client"):
        try: await info["client"].disconnect()
        except: pass
    cl,ph,via,err = await send_code_safely(info["phone"],force_sms=True)
    if err:
        await call.message.answer(t("login_err",lang)+str(err)); return
    _pending[uid]={"client":cl,"phone":info["phone"],"hash":ph}
    await call.message.answer(t("code_sent_sms",lang),parse_mode="HTML")

@router.message(St.code)
async def proc_code(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    info=_pending.get(uid)
    if not info:
        await msg.answer("❌ Session tugadi. /start",reply_markup=menu_kb(lang))
        await state.clear(); return
    code = extract_code(msg.text)
    if not code or len(code)<3:
        await msg.answer(t("code_wrong",lang)); return
    cl = info["client"]
    try:
        await cl.sign_in(phone=info["phone"],code=code,phone_code_hash=info["hash"])
    except SessionPasswordNeededError:
        await state.set_state(St.passw); await msg.answer(t("enter_2fa",lang)); return
    except PhoneCodeInvalidError:
        await msg.answer(t("code_wrong",lang)); return
    except PhoneCodeExpiredError:
        await msg.answer(t("login_err",lang)+"Kod eskirgan. /start"); await state.clear()
        try: await cl.disconnect()
        except: pass
        _pending.pop(uid,None); return
    except FloodWaitError as e:
        await msg.answer(t("flood_wait",lang,sec=e.seconds)); return
    except Exception as e:
        logger.exception(f"sign_in: {e}")
        await msg.answer(t("login_err",lang)+str(e)); await state.clear()
        try: await cl.disconnect()
        except: pass
        _pending.pop(uid,None); return
    sess = cl.session.save()
    await db("UPDATE users SET phone=?,session_string=? WHERE user_id=?",(info["phone"],sess,uid),c=True)
    try: await cl.disconnect()
    except: pass
    _pending.pop(uid,None); await state.clear()
    await msg.answer(t("login_ok",lang),parse_mode="HTML")
    coins=await get_coins(uid); vb=await vip_badge(uid)
    await msg.answer(t("main_menu",lang,coins=coins,vip=vb),reply_markup=menu_kb(lang),parse_mode="HTML")

@router.message(St.passw)
async def proc_2fa(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    info=_pending.get(uid)
    if not info:
        await msg.answer("❌ /start",reply_markup=menu_kb(lang)); await state.clear(); return
    cl=info["client"]
    try:
        await cl.sign_in(password=msg.text.strip())
    except Exception as e:
        await msg.answer(t("login_err",lang)+str(e)); return
    sess = cl.session.save()
    await db("UPDATE users SET phone=?,session_string=? WHERE user_id=?",(info["phone"],sess,uid),c=True)
    try: await cl.disconnect()
    except: pass
    _pending.pop(uid,None); await state.clear()
    await msg.answer(t("login_ok",lang),reply_markup=menu_kb(lang),parse_mode="HTML")

# ═══════════════════════════════════════════════
# SOAT (NIK + PREFIX + TIMEFORMAT + RASM)
# ═══════════════════════════════════════════════
@router.message(F.text.in_(all_variants("btn_clock")))
async def btn_clock(msg: Message):
    uid=msg.from_user.id
    if await is_banned(uid): await msg.answer(t("admin_banned","uz")); return
    lang = await get_lang(uid)
    await msg.answer(t("clock_menu",lang),reply_markup=clock_inline(lang),parse_mode="HTML")

@router.callback_query(F.data.in_({"clock_menu","back_clk"}))
async def clock_menu_cb(call: CallbackQuery):
    lang = await get_lang(call.from_user.id)
    await call.message.edit_text(t("clock_menu",lang),reply_markup=clock_inline(lang),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="nick_menu")
async def nick_menu_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    vip = await is_vip(uid)
    coins = await get_coins(uid)
    n_p = 0 if vip else int(await get_s("nick_normal_price","15"))
    p_p = 0 if vip else int(await get_s("nick_premium_price","50"))
    bought = [r[0] for r in (await db("SELECT style_id FROM user_nick_styles WHERE user_id=?",(uid,),fa=True) or [])]
    btns=[]
    for sid,s in NICK_STYLES.items():
        if s["cat"]!="normal": continue
        ex = fmt_nick_time(sid)
        tag = "✅" if sid in bought else (f"🆓" if n_p==0 else f"💰{n_p}")
        btns.append([InlineKeyboardButton(text=f"{s['name']} {ex} — {tag}",callback_data=f"nstyle_{sid}")])
    for sid,s in NICK_STYLES.items():
        if s["cat"]!="premium": continue
        ex = fmt_nick_time(sid)
        tag = "✅" if sid in bought else (f"👑 FREE" if vip else f"💰{p_p}")
        btns.append([InlineKeyboardButton(text=f"{s['name']} {ex} — {tag}",callback_data=f"nstyle_{sid}")])
    btns.append([InlineKeyboardButton(text=t("btn_back",lang),callback_data="back_clk")])
    await call.message.edit_text(t("nick_title",lang,n_price=n_p if n_p else "FREE",p_price=p_p if p_p else "VIP/FREE",coins=coins),
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("nstyle_"))
async def pick_nstyle(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    sid=int(call.data.split("_")[1]); s=NICK_STYLES.get(sid)
    if not s: await call.answer("❌"); return
    sess = await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if not sess or not sess[0]:
        await call.answer(t("need_login",lang),show_alert=True); return
    vip = await is_vip(uid)
    b = await db("SELECT 1 FROM user_nick_styles WHERE user_id=? AND style_id=?",(uid,sid),fo=True)
    price = 0
    if not b and not vip:
        price = int(await get_s("nick_normal_price" if s["cat"]=="normal" else "nick_premium_price","15"))
        coins = await get_coins(uid)
        if coins<price: await call.answer(t("no_coins",lang),show_alert=True); return
        if price>0:
            await add_coins(uid, -price)
            await db("INSERT INTO user_nick_styles VALUES(?,?)",(uid,sid),c=True)
            await call.message.answer(t("style_bought",lang,name=s["name"],price=price))
    elif not b and vip:
        await db("INSERT INTO user_nick_styles VALUES(?,?)",(uid,sid),c=True)
    await db("UPDATE users SET nick_status='active',nick_style=? WHERE user_id=?",(sid,uid),c=True)
    start_worker(uid,sess[0])
    await call.message.answer(t("nick_started",lang,name=s["name"]),reply_markup=menu_kb(lang))
    await call.answer()

@router.callback_query(F.data=="prefix_menu")
async def prefix_menu_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    r = await db("SELECT nick_prefix FROM users WHERE user_id=?",(uid,),fo=True)
    cur = (r[0] if r and r[0] else "❌ Yo'q")
    btns=[]
    row=[]
    for i,e in enumerate(PREFIX_OPTIONS):
        lbl = t("prefix_none",lang) if e=="" else e
        row.append(InlineKeyboardButton(text=lbl,callback_data=f"pref_{i}"))
        if len(row)>=3:
            btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(text=t("btn_back",lang),callback_data="back_clk")])
    await call.message.edit_text(t("prefix_menu",lang,cur=cur),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("pref_"))
async def set_pref(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    idx = int(call.data.split("_")[1])
    if not (0<=idx<len(PREFIX_OPTIONS)): await call.answer("❌"); return
    p = PREFIX_OPTIONS[idx]
    await db("UPDATE users SET nick_prefix=? WHERE user_id=?",(p,uid),c=True)
    await call.answer(t("prefix_set",lang,p=(p if p else "❌")),show_alert=True)
    restart_worker(uid)
    await prefix_menu_cb(call)

@router.callback_query(F.data=="tf_menu")
async def tf_menu_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    r = await db("SELECT time_format FROM users WHERE user_id=?",(uid,),fo=True)
    cur = r[0] if r else "24"
    cur_lbl = {"24": t("tf_24",lang), "12": t("tf_12",lang), "date": t("tf_date",lang)}.get(cur, cur)
    btns=[
        [InlineKeyboardButton(text=t("tf_24",lang),callback_data="tf_24")],
        [InlineKeyboardButton(text=t("tf_12",lang),callback_data="tf_12")],
        [InlineKeyboardButton(text=t("tf_date",lang),callback_data="tf_date")],
        [InlineKeyboardButton(text=t("btn_back",lang),callback_data="back_clk")],
    ]
    await call.message.edit_text(t("tf_menu",lang,cur=cur_lbl),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.startswith("tf_"))
async def set_tf(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    v = call.data.split("_")[1]
    await db("UPDATE users SET time_format=? WHERE user_id=?",(v,uid),c=True)
    await call.answer(t("tf_set",lang),show_alert=False)
    restart_worker(uid)
    await tf_menu_cb(call)

@router.callback_query(F.data=="stop_nick")
async def stop_nick(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    await db("UPDATE users SET nick_status='stopped' WHERE user_id=?",(uid,),c=True)
    u = await db("SELECT photo_status,bio_status,session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if u and u[0]=='stopped' and u[1]=='stopped': stop_worker(uid)
    elif u and u[2]: start_worker(uid,u[2])
    await call.message.answer(t("nick_stopped",lang),reply_markup=menu_kb(lang))
    await call.answer()

# ═══════════════════════════════════════════════
# RASM SOAT
# ═══════════════════════════════════════════════
@router.callback_query(F.data=="photo_menu")
async def photo_menu_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    s = await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if not s or not s[0]:
        await call.answer(t("need_login",lang),show_alert=True); return
    ps = load_user_photos(uid)
    mx = await max_photos(uid)
    await call.message.edit_text(t("photo_menu",lang,count=len(ps),vip_max=mx),
                                 reply_markup=photo_menu_kb(lang,len(ps),mx),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="photo_add")
async def photo_add_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    ps = load_user_photos(uid); mx = await max_photos(uid)
    if len(ps)>=mx:
        await call.answer(t("photo_max",lang),show_alert=True); return
    await call.message.answer(t("photo_send",lang))
    await state.set_state(St.add_photo)
    await call.answer()

@router.message(St.add_photo, F.photo)
async def photo_recv(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    ps = load_user_photos(uid); mx = await max_photos(uid)
    if len(ps)>=mx: await msg.answer(t("photo_max",lang)); await state.clear(); return
    f = await msg.bot.get_file(msg.photo[-1].file_id)
    bio = await msg.bot.download_file(f.file_path)
    add_user_photo(uid, bio.read())
    nc = len(load_user_photos(uid))
    vip = await is_vip(uid)
    n_p = 0 if vip else int(await get_s("photo_normal_price","30"))
    p_p = 0 if vip else int(await get_s("photo_premium_price","70"))
    bought = [r[0] for r in (await db("SELECT style_id FROM user_photo_styles WHERE user_id=?",(uid,),fa=True) or [])]
    btns=[]
    for sid,st in PHOTO_STYLES.items():
        price = n_p if st["cat"]=="normal" else p_p
        tag = "✅" if sid in bought else ("🆓" if price==0 else f"💰{price}")
        pre = "🆓" if st["cat"]=="normal" else "💎"
        btns.append([InlineKeyboardButton(text=f"{pre} {st['name']} — {tag}",callback_data=f"pst_{sid}")])
    await msg.answer(t("photo_added",lang,count=nc,mx=mx),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_style)

@router.callback_query(St.photo_style, F.data.startswith("pst_"))
async def photo_style_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    sid=int(call.data.split("_")[1]); st=PHOTO_STYLES.get(sid)
    if not st: await call.answer("❌"); return
    vip=await is_vip(uid)
    n_p=0 if vip else int(await get_s("photo_normal_price","30"))
    p_p=0 if vip else int(await get_s("photo_premium_price","70"))
    price=n_p if st["cat"]=="normal" else p_p
    b=await db("SELECT 1 FROM user_photo_styles WHERE user_id=? AND style_id=?",(uid,sid),fo=True)
    if not b and price>0:
        coins=await get_coins(uid)
        if coins<price: await call.answer(t("no_coins",lang),show_alert=True); return
        await add_coins(uid,-price)
        await db("INSERT INTO user_photo_styles VALUES(?,?)",(uid,sid),c=True)
        await call.answer(f"🎉 {st['name']} sotib olindi!",show_alert=False)
    elif not b and price==0 and vip:
        await db("INSERT INTO user_photo_styles VALUES(?,?)",(uid,sid),c=True)
    await state.update_data(ps=sid)
    btns=[[InlineKeyboardButton(text=v["n"],callback_data=f"pc_{k}")] for k,v in COLORS.items()]
    await call.message.answer(t("photo_color",lang),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_color)
    await call.answer()

@router.callback_query(St.photo_color, F.data.startswith("pc_"))
async def photo_color_cb(call: CallbackQuery, state: FSMContext):
    lang=await get_lang(call.from_user.id)
    cid=int(call.data.split("_")[1])
    await state.update_data(pc=cid)
    btns=[
        [InlineKeyboardButton(text=t("pos_tm",lang),callback_data="pp_1"),
         InlineKeyboardButton(text=t("pos_tl",lang),callback_data="pp_2"),
         InlineKeyboardButton(text=t("pos_tr",lang),callback_data="pp_3")],
        [InlineKeyboardButton(text=t("pos_bl",lang),callback_data="pp_4"),
         InlineKeyboardButton(text=t("pos_br",lang),callback_data="pp_5")],
    ]
    await call.message.answer(t("photo_pos",lang),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_pos)
    await call.answer()

@router.callback_query(St.photo_pos, F.data.startswith("pp_"))
async def photo_pos_cb(call: CallbackQuery, state: FSMContext):
    lang=await get_lang(call.from_user.id)
    pid=int(call.data.split("_")[1])
    await state.update_data(pp=pid)
    # Shrift tanlash
    btns=[[InlineKeyboardButton(text=v["name"],callback_data=f"pf_{k}")] for k,v in PHOTO_FONTS.items()]
    await call.message.answer("🔤 Shrift tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_font)
    await call.answer()

@router.callback_query(St.photo_font, F.data.startswith("pf_"))
async def photo_font_cb(call: CallbackQuery, state: FSMContext):
    lang=await get_lang(call.from_user.id)
    fid=int(call.data.split("_")[1])
    await state.update_data(pf=fid)
    btns=[[InlineKeyboardButton(text=v["name"],callback_data=f"pe_{k}")] for k,v in EFFECTS.items()]
    await call.message.answer("✨ Effekt tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_effect)
    await call.answer()

@router.callback_query(St.photo_effect, F.data.startswith("pe_"))
async def photo_effect_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    eid=int(call.data.split("_")[1])
    d=await state.get_data()
    ps=d.get("ps",1); pc=d.get("pc",1); pp=d.get("pp",1); pf=d.get("pf",1)
    sess=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if not sess or not sess[0]: await state.clear(); return
    await db("UPDATE users SET photo_status='active',photo_style=?,photo_color=?,photo_position=?,photo_font=?,photo_effect=? WHERE user_id=?",
             (ps,pc,pp,pf,eid,uid),c=True)
    start_worker(uid,sess[0])
    await call.message.answer(t("photo_started",lang),reply_markup=menu_kb(lang))
    await state.clear()
    await call.answer()

@router.callback_query(F.data=="stop_photo")
async def stop_photo_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    await db("UPDATE users SET photo_status='stopped' WHERE user_id=?",(uid,),c=True)
    u=await db("SELECT nick_status,bio_status,session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if u and u[0]=='stopped' and u[1]=='stopped': stop_worker(uid)
    elif u and u[2]: start_worker(uid,u[2])
    await call.message.answer(t("photo_stopped",lang),reply_markup=menu_kb(lang))
    await call.answer()

@router.callback_query(F.data=="photo_list")
async def photo_list_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    ps=load_user_photos(uid)
    if not ps: await call.answer(t("my_photos_empty",lang),show_alert=True); return
    media=[]
    for i,p in enumerate(ps[:10],1):
        cap = f"📸 Rasm #{i}" if i==1 else None
        media.append(InputMediaPhoto(media=io.BytesIO(p),caption=cap))
    try: await call.message.answer_media_group(media=media)
    except: await call.message.answer(f"📸 Jami {len(ps)} ta rasm")
    await call.answer()

@router.callback_query(F.data=="photo_del")
async def photo_del_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    ps=load_user_photos(uid)
    if not ps: await call.answer(t("my_photos_empty",lang),show_alert=True); return
    await call.message.answer(t("ask_del_photo",lang,count=len(ps)))
    await state.set_state(St.del_photo)
    await call.answer()

@router.message(St.del_photo)
async def photo_del_proc(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if not msg.text or not msg.text.isdigit(): await msg.answer(t("photo_bad_num",lang)); return
    n=int(msg.text); ps=load_user_photos(uid)
    if not(1<=n<=len(ps)): await msg.answer(t("photo_bad_num",lang)); return
    del_user_photo(uid,n); left=len(load_user_photos(uid))
    await msg.answer(t("photo_deleted",lang,num=n,left=left),reply_markup=menu_kb(lang))
    await state.clear()

# ═══════════════════════════════════════════════
# BIO
# ═══════════════════════════════════════════════
@router.message(F.text.in_(all_variants("btn_bio")))
async def btn_bio(msg: Message):
    uid=msg.from_user.id
    if await is_banned(uid): await msg.answer(t("admin_banned","uz")); return
    lang=await get_lang(uid)
    s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if not s or not s[0]: await msg.answer(t("need_login",lang)); return
    coins=await get_coins(uid); vb=await vip_badge(uid)
    up=await get_s("umr_price","100"); bp=await get_s("birthday_price","80")
    await msg.answer(t("bio_menu",lang,coins=coins,vip=vb),reply_markup=bio_kb(lang,up,bp),parse_mode="HTML")

@router.callback_query(F.data=="bio_add")
async def bio_add_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    tx=load_bio_texts(uid)
    if len(tx)>=10: await call.answer(t("bio_text_max",lang),show_alert=True); return
    await call.message.answer(t("ask_bio_text",lang))
    await state.set_state(St.bio_add)
    await call.answer()

@router.message(St.bio_add)
async def bio_add_proc(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    tx=(msg.text or "").strip()
    if not tx: await msg.answer(t("ask_bio_text",lang)); return
    if len(tx)>70: await msg.answer(t("bio_text_long",lang)); return
    txx=load_bio_texts(uid)
    if len(txx)>=10: await msg.answer(t("bio_text_max",lang)); await state.clear(); return
    save_bio_text(uid,tx); c=len(load_bio_texts(uid))
    await db("UPDATE users SET bio_status='active',bio_mode='text' WHERE user_id=?",(uid,),c=True)
    s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if s and s[0]: start_worker(uid,s[0])
    coins=await get_coins(uid); vb=await vip_badge(uid)
    await msg.answer(t("bio_text_ok",lang,c=c),reply_markup=menu_kb(lang))
    await state.clear()

@router.callback_query(F.data=="bio_list")
async def bio_list_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    tx=load_bio_texts(uid)
    if not tx: await call.answer(t("bio_list_empty",lang),show_alert=True); return
    out="📋 <b>Matnlar:</b>\n\n"
    for i,x in enumerate(tx,1): out += f"{i}. {x}\n"
    await call.message.answer(out,parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="bio_del")
async def bio_del_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    tx=load_bio_texts(uid)
    if not tx: await call.answer(t("bio_list_empty",lang),show_alert=True); return
    await call.message.answer(t("ask_del_bio",lang,c=len(tx)))
    await state.set_state(St.bio_del)
    await call.answer()

@router.message(St.bio_del)
async def bio_del_proc(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if not msg.text or not msg.text.isdigit(): await msg.answer(t("photo_bad_num",lang)); return
    n=int(msg.text)
    if del_bio_text(uid,n): await msg.answer(t("bio_deleted",lang),reply_markup=menu_kb(lang))
    else: await msg.answer(t("photo_bad_num",lang))
    await state.clear()

@router.callback_query(F.data=="bio_umr")
async def bio_umr_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    price=int(await get_s("umr_price","100"))
    u=await db("SELECT birth_date FROM users WHERE user_id=?",(uid,),fo=True)
    if u and u[0]:
        await db("UPDATE users SET bio_status='active',bio_mode='umr' WHERE user_id=?",(uid,),c=True)
        s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
        if s and s[0]: start_worker(uid,s[0])
        await call.message.answer(t("umr_started",lang),reply_markup=menu_kb(lang))
        await call.answer(); return
    coins=await get_coins(uid)
    if coins<price: await call.answer(t("no_coins",lang),show_alert=True); return
    await call.message.answer(t("ask_birth_date",lang),parse_mode="HTML")
    await state.set_state(St.bio_umr)
    await call.answer()

@router.message(St.bio_umr)
async def bio_umr_proc(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    m=re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$",(msg.text or "").strip())
    if not m: await msg.answer(t("bad_date",lang),parse_mode="HTML"); return
    d,mo,y=map(int,m.groups())
    try: datetime(y,mo,d)
    except: await msg.answer(t("bad_date",lang)); return
    price=int(await get_s("umr_price","100")); coins=await get_coins(uid)
    if coins<price: await msg.answer(t("no_coins",lang)); await state.clear(); return
    await add_coins(uid,-price)
    await db("UPDATE users SET birth_date=?,bio_status='active',bio_mode='umr' WHERE user_id=?",
             (f"{d:02d}.{mo:02d}.{y}",uid),c=True)
    s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if s and s[0]: start_worker(uid,s[0])
    await msg.answer(t("umr_started",lang),reply_markup=menu_kb(lang))
    await state.clear()

@router.callback_query(F.data=="bio_bd")
async def bio_bd_cb(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    price=int(await get_s("birthday_price","80"))
    u=await db("SELECT birthday_date FROM users WHERE user_id=?",(uid,),fo=True)
    if u and u[0]:
        await db("UPDATE users SET bio_status='active',bio_mode='birthday' WHERE user_id=?",(uid,),c=True)
        s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
        if s and s[0]: start_worker(uid,s[0])
        await call.message.answer(t("bd_started",lang),reply_markup=menu_kb(lang))
        await call.answer(); return
    coins=await get_coins(uid)
    if coins<price: await call.answer(t("no_coins",lang),show_alert=True); return
    await call.message.answer(t("ask_bd_date",lang),parse_mode="HTML")
    await state.set_state(St.bio_bd)
    await call.answer()

@router.message(St.bio_bd)
async def bio_bd_proc(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    m=re.match(r"^(\d{1,2})\.(\d{1,2})$",(msg.text or "").strip())
    if not m: await msg.answer(t("bad_date",lang)); return
    d,mo=map(int,m.groups())
    if not(1<=mo<=12 and 1<=d<=31): await msg.answer(t("bad_date",lang)); return
    price=int(await get_s("birthday_price","80")); coins=await get_coins(uid)
    if coins<price: await msg.answer(t("no_coins",lang)); await state.clear(); return
    await add_coins(uid,-price)
    await db("UPDATE users SET birthday_date=?,bio_status='active',bio_mode='birthday' WHERE user_id=?",
             (f"{d:02d}.{mo:02d}",uid),c=True)
    s=await db("SELECT session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if s and s[0]: start_worker(uid,s[0])
    await msg.answer(t("bd_started",lang),reply_markup=menu_kb(lang))
    await state.clear()

@router.callback_query(F.data=="stop_bio")
async def stop_bio_cb(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    await db("UPDATE users SET bio_status='stopped' WHERE user_id=?",(uid,),c=True)
    u=await db("SELECT nick_status,photo_status,session_string FROM users WHERE user_id=?",(uid,),fo=True)
    if u and u[0]=='stopped' and u[1]=='stopped': stop_worker(uid)
    elif u and u[2]: start_worker(uid,u[2])
    await call.message.answer(t("bio_stopped",lang),reply_markup=menu_kb(lang))
    await call.answer()

# ═══════════════════════════════════════════════
# DO'KON / VIP
# ═══════════════════════════════════════════════
@router.message(F.text.in_(all_variants("btn_shop")))
async def btn_shop(msg: Message):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if await is_banned(uid): await msg.answer(t("admin_banned",lang)); return
    coins=await get_coins(uid); vb=await vip_badge(uid)
    vp=await get_s("vip_price","500")
    await msg.answer(t("shop_menu",lang,coins=coins,vip=vb,vprice=vp),
                     reply_markup=shop_kb(lang,vp),parse_mode="HTML")

@router.callback_query(F.data=="buy_vip")
async def buy_vip(call: CallbackQuery):
    uid=call.from_user.id; lang=await get_lang(uid)
    if await is_vip(uid):
        r = await db("SELECT vip_until FROM users WHERE user_id=?",(uid,),fo=True)
        if r and r[0]:
            try:
                d = datetime.fromisoformat(r[0])
                days = (d - datetime.now(TZ)).days
                await call.answer(t("vip_already",lang,d=max(days,0)),show_alert=True); return
            except: pass
    price=int(await get_s("vip_price","500"))
    coins=await get_coins(uid)
    if coins<price:
        await call.answer(t("vip_no_coins",lang,p=price),show_alert=True); return
    days=int(await get_s("vip_days","30"))
    until = datetime.now(TZ) + timedelta(days=days)
    await add_coins(uid,-price)
    await db("UPDATE users SET is_vip=1,vip_until=? WHERE user_id=?",(until.isoformat(),uid),c=True)
    await call.message.answer(t("vip_bought",lang),reply_markup=menu_kb(lang))
    await call.answer()

@router.callback_query(F.data=="buy_coins")
async def buy_coins(call: CallbackQuery):
    lang=await get_lang(call.from_user.id)
    adm=await get_s("admin_contact","@admin")
    await call.message.answer(t("buy_coins_text",lang,admin=adm))
    await call.answer()

# ═══════════════════════════════════════════════
# O'YINLAR
# ═══════════════════════════════════════════════
SLOT_EMOJIS = ["🍒","🍋","🍊","🍇","🔔","💎","7️⃣"]

@router.message(F.text.in_(all_variants("btn_games")))
async def btn_games(msg: Message):
    uid=msg.from_user.id; lang=await get_lang(uid)
    if await is_banned(uid): await msg.answer(t("admin_banned",lang)); return
    coins=await get_coins(uid)
    smn=int(await get_s("slot_min","5")); smx=int(await get_s("slot_max","50"))
    dmn=int(await get_s("dice_min","5")); dmx=int(await get_s("dice_max","30"))
    cmn=int(await get_s("cf_min","5")); cmx=int(await get_s("cf_max","100"))
    await msg.answer(t("games_menu",lang,coins=coins),reply_markup=games_kb(lang,smn,smx,dmn,dmx,cmn,cmx),parse_mode="HTML")

@router.callback_query(F.data.in_({"game_slot","game_dice","game_cf"}))
async def game_select(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    g = call.data.split("_")[1]
    await state.update_data(game=g)
    if g=="slot":
        mn=int(await get_s("slot_min","5")); mx=int(await get_s("slot_max","50"))
    elif g=="dice":
        mn=int(await get_s("dice_min","5")); mx=int(await get_s("dice_max","30"))
    else:
        mn=int(await get_s("cf_min","5")); mx=int(await get_s("cf_max","100"))
    await state.update_data(mn=mn,mx=mx)
    await call.message.answer(t("ask_bet",lang,mn=mn,mx=mx))
    await state.set_state(St.bet)
    await call.answer()

@router.message(St.bet)
async def proc_bet(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    d=await state.get_data(); g=d.get("game"); mn=d.get("mn",5); mx=d.get("mx",50)
    try: bet=int((msg.text or "").strip())
    except: await msg.answer(t("bad_bet",lang,mn=mn,mx=mx)); return
    if not(mn<=bet<=mx): await msg.answer(t("bad_bet",lang,mn=mn,mx=mx)); return
    coins=await get_coins(uid)
    if coins<bet: await msg.answer(t("bet_not_enough",lang)); await state.clear(); return
    await state.update_data(bet=bet)
    if g=="slot":
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("slot_spin",lang),callback_data="slot_go")]])
        await msg.answer(t("slot_title",lang,bet=bet),reply_markup=kb,parse_mode="HTML")
    elif g=="dice":
        btns=[[InlineKeyboardButton(text=str(i),callback_data=f"dice_{i}") for i in range(1,4)],
              [InlineKeyboardButton(text=str(i),callback_data=f"dice_{i}") for i in range(4,7)]]
        await msg.answer(t("dice_title",lang,bet=bet),reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),parse_mode="HTML")
    elif g=="cf":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("cf_heads",lang),callback_data="cf_h"),
             InlineKeyboardButton(text=t("cf_tails",lang),callback_data="cf_t")]])
        await msg.answer(t("cf_title",lang,bet=bet),reply_markup=kb,parse_mode="HTML")

@router.callback_query(F.data=="slot_go", St.bet)
async def slot_go(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    d=await state.get_data(); bet=d.get("bet",10)
    coins=await get_coins(uid)
    if coins<bet: await call.answer(t("bet_not_enough",lang),show_alert=True); return
    r1,r2,r3 = [random.choice(SLOT_EMOJIS) for _ in range(3)]
    m2 = int(await get_s("slot_mult2","2")); m5 = int(await get_s("slot_mult5","5"))
    msg_txt = f"🎰 {r1} {r2} {r3}\n\n"
    if r1==r2==r3:
        w = bet*m5; await add_coins(uid,w); msg_txt += t("slot_win5",lang,w=w)
    elif r1==r2 or r2==r3 or r1==r3:
        w = bet*m2; await add_coins(uid,w); msg_txt += t("slot_win2",lang,w=w)
    else:
        await add_coins(uid,-bet); msg_txt += t("slot_lose",lang,bet=bet)
    await call.message.edit_text(msg_txt)
    await state.clear(); await call.answer()

@router.callback_query(F.data.startswith("dice_"), St.bet)
async def dice_go(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    ch = int(call.data.split("_")[1])
    d=await state.get_data(); bet=d.get("bet",10)
    coins=await get_coins(uid)
    if coins<bet: await call.answer(t("bet_not_enough",lang),show_alert=True); return
    r = random.randint(1,6); dm = int(await get_s("dice_mult","5"))
    if r==ch:
        w=bet*dm; await add_coins(uid,w); txt=t("dice_win",lang,r=r,w=w)
    else:
        await add_coins(uid,-bet); txt=t("dice_lose",lang,r=r,c=ch,bet=bet)
    await call.message.edit_text(txt)
    await state.clear(); await call.answer()

@router.callback_query(F.data.startswith("cf_"), St.bet)
async def cf_go(call: CallbackQuery, state: FSMContext):
    uid=call.from_user.id; lang=await get_lang(uid)
    ch = call.data.split("_")[1]
    d=await state.get_data(); bet=d.get("bet",10)
    coins=await get_coins(uid)
    if coins<bet: await call.answer(t("bet_not_enough",lang),show_alert=True); return
    r = random.choice(["h","t"]); cm = int(await get_s("cf_mult","2"))
    rn = t("cf_heads",lang) if r=="h" else t("cf_tails",lang)
    if r==ch:
        w=bet*cm; await add_coins(uid,w); txt=t("cf_win",lang,w=w)
    else:
        await add_coins(uid,-bet); txt=t("cf_lose",lang,r=rn,bet=bet)
    await call.message.edit_text(txt)
    await state.clear(); await call.answer()

# ═══════════════════════════════════════════════
# ADMIN PANEL (chiroyli, o'zbek tilida)
# ═══════════════════════════════════════════════
def adm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika",callback_data="as")],
        [InlineKeyboardButton(text="💰 Narxlar sozlamalari",callback_data="ap_prices")],
        [InlineKeyboardButton(text="🎁 Bonuslar",callback_data="ap_bonus")],
        [InlineKeyboardButton(text="🎮 O'yin sozlamalari",callback_data="ap_games")],
        [InlineKeyboardButton(text="👥 User boshqaruvi",callback_data="ap_users")],
        [InlineKeyboardButton(text="📢 Broadcast",callback_data="ad_bc")],
        [InlineKeyboardButton(text="📞 Kontakt/Support",callback_data="ap_cont")],
        [InlineKeyboardButton(text="🔑 Parol",callback_data="ad_pass"),
         InlineKeyboardButton(text="🚪 Chiqish",callback_data="ad_exit")],
    ])

def adm_prices_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nick Oddiy",callback_data="ad_nn"),
         InlineKeyboardButton(text="✏️ Nick Premium",callback_data="ad_np")],
        [InlineKeyboardButton(text="🖼 Photo Oddiy",callback_data="ad_pn"),
         InlineKeyboardButton(text="🖼 Photo Premium",callback_data="ad_pp")],
        [InlineKeyboardButton(text="⏳ Umr narxi",callback_data="ad_umr"),
         InlineKeyboardButton(text="🎂 Tug.kun narxi",callback_data="ad_bd")],
        [InlineKeyboardButton(text="👑 VIP narxi/kun",callback_data="ad_vip")],
        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad_back")],
    ])

def adm_bonus_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Kunlik bonus",callback_data="ad_daily"),
         InlineKeyboardButton(text="👥 Referal",callback_data="ad_ref")],
        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad_back")],
    ])

def adm_games_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Slot min/max",callback_data="ad_g_slot"),
         InlineKeyboardButton(text="🎰 Slot mult",callback_data="ad_g_slotm")],
        [InlineKeyboardButton(text="🎲 Kubik min/max",callback_data="ad_g_dice"),
         InlineKeyboardButton(text="🎲 Kubik mult",callback_data="ad_g_dicem")],
        [InlineKeyboardButton(text="🪙 CF min/max",callback_data="ad_g_cf"),
         InlineKeyboardButton(text="🪙 CF mult",callback_data="ad_g_cfm")],
        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad_back")],
    ])

def adm_users_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Balans o'zgartirish",callback_data="ad_bal")],
        [InlineKeyboardButton(text="🚫 Ban/Unban user",callback_data="ad_ban")],
        [InlineKeyboardButton(text="🔍 User ma'lumoti",callback_data="ad_uinfo")],
        [InlineKeyboardButton(text="🎁 Hammaga coin tarqatish",callback_data="ad_give")],
        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data="ad_back")],
    ])

@router.message(Command("admin"))
async def adm_cmd(msg: Message, state: FSMContext):
    uid=msg.from_user.id
    if uid in _admins:
        await msg.answer("⚙️ <b>ADMIN PANEL</b>",reply_markup=adm_kb(),parse_mode="HTML")
    else:
        lang=await get_lang(uid)
        await msg.answer(t("admin_enter",lang)); await state.set_state(St.adm_code)

@router.message(St.adm_code)
async def adm_login(msg: Message, state: FSMContext):
    uid=msg.from_user.id; lang=await get_lang(uid)
    real=await get_s("admin_code","")
    if msg.text.strip()==real and real:
        _admins.add(uid); await state.clear()
        await msg.answer(t("admin_ok",lang),reply_markup=adm_kb(),parse_mode="HTML")
    else:
        await msg.answer(t("admin_wrong",lang))

@router.callback_query(F.data=="ad_back")
async def adm_back(call: CallbackQuery):
    if call.from_user.id not in _admins: return
    await call.message.edit_text("⚙️ <b>ADMIN PANEL</b>",reply_markup=adm_kb(),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="as")
async def adm_stats(call: CallbackQuery):
    if call.from_user.id not in _admins: return
    tot=(await db("SELECT COUNT(*) FROM users",fo=True))[0]
    na=(await db("SELECT COUNT(*) FROM users WHERE nick_status='active'",fo=True))[0]
    pa=(await db("SELECT COUNT(*) FROM users WHERE photo_status='active'",fo=True))[0]
    ba=(await db("SELECT COUNT(*) FROM users WHERE bio_status='active'",fo=True))[0]
    co=(await db("SELECT SUM(coins) FROM users",fo=True))[0] or 0
    vipc=(await db("SELECT COUNT(*) FROM users WHERE is_vip=1",fo=True))[0]
    banned=(await db("SELECT COUNT(*) FROM users WHERE banned=1",fo=True))[0]
    txt = (f"📊 <b>STATISTIKA</b>\n\n"
           f"👤 Jami userlar: {tot}\n"
           f"🚫 Bloklangan: {banned}\n"
           f"👑 VIP lar: {vipc}\n\n"
           f"⏰ Aktiv nik soat: {na}\n"
           f"🖼 Aktiv rasm soat: {pa}\n"
           f"📝 Aktiv bio: {ba}\n\n"
           f"💰 Jami coin: {co}")
    await call.message.edit_text(txt,reply_markup=adm_kb(),parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data=="ap_prices")
async def _(c):
    if c.from_user.id not in _admins: return
    await c.message.edit_text("💰 <b>NARXLAR</b>",reply_markup=adm_prices_kb(),parse_mode="HTML"); await c.answer()
@router.callback_query(F.data=="ap_bonus")
async def _(c):
    if c.from_user.id not in _admins: return
    await c.message.edit_text("🎁 <b>BONUSLAR</b>",reply_markup=adm_bonus_kb(),parse_mode="HTML"); await c.answer()
@router.callback_query(F.data=="ap_games")
async def _(c):
    if c.from_user.id not in _admins: return
    await c.message.edit_text("🎮 <b>O'YINLAR</b>",reply_markup=adm_games_kb(),parse_mode="HTML"); await c.answer()
@router.callback_query(F.data=="ap_users")
async def _(c):
    if c.from_user.id not in _admins: return
    await c.message.edit_text("👥 <b>USERLAR</b>",reply_markup=adm_users_kb(),parse_mode="HTML"); await c.answer()
@router.callback_query(F.data=="ap_cont")
async def _(c, state: FSMContext):
    if c.from_user.id not in _admins: return
    await c.message.answer("Admin kontakt yozing:"); await state.set_state(St.adm_val); await state.update_data(key="admin_contact"); await c.answer()

# Admin value handlers - generik
def adm_btn(key, ask_txt, is_vip=False):
    async def _cb(call, state: FSMContext):
        if call.from_user.id not in _admins: return
        await call.message.answer(ask_txt)
        await state.update_data(key=key)
        await state.set_state(St.adm_val); await call.answer()
    return _cb

router.callback_query(F.data=="ad_nn")(adm_btn("nick_normal_price","Nick oddiy narxi (Coin):"))
router.callback_query(F.data=="ad_np")(adm_btn("nick_premium_price","Nick premium narxi:"))
router.callback_query(F.data=="ad_pn")(adm_btn("photo_normal_price","Photo oddiy narxi:"))
router.callback_query(F.data=="ad_pp")(adm_btn("photo_premium_price","Photo premium narxi:"))
router.callback_query(F.data=="ad_umr")(adm_btn("umr_price","Umr narxi:"))
router.callback_query(F.data=="ad_bd")(adm_btn("birthday_price","Tug'ilgan kun narxi:"))
router.callback_query(F.data=="ad_daily")(adm_btn("daily_bonus","Kunlik bonus:"))
router.callback_query(F.data=="ad_ref")(adm_btn("ref_bonus","Referal bonus:"))


# O'yin sozlamalari uchun alohida handler (ikki qiymat, min/max)
@router.callback_query(F.data.startswith("ad_g_"))
async def adm_games_set(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    g = call.data.split("_",2)[2]
    await state.update_data(game_set=g)
    if g=="slot":
        await call.message.answer("Slot min,max (masalan: 5 50):")
    elif g=="slotm":
        await call.message.answer("Slot mult 2x va 5x (masalan: 2 5):")
    elif g=="dice":
        await call.message.answer("Kubik min,max (5 30):")
    elif g=="dicem":
        await call.message.answer("Kubik multiplikator (5):")
    elif g=="cf":
        await call.message.answer("CF min,max (5 100):")
    elif g=="cfm":
        await call.message.answer("CF multiplikator (2):")
    await state.set_state(St.adm_val)
    await state.update_data(key="__game__")
    await call.answer()

# VIP narxi/kuni
@router.callback_query(F.data=="ad_vip")
async def adm_vip(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("VIP narxi va kunlari (masalan: 500 30):")
    await state.update_data(key="__vip__")
    await state.set_state(St.adm_val); await call.answer()

# Balans o'zgartirish
@router.callback_query(F.data=="ad_bal")
async def adm_bal(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("User ID kiriting:"); await state.set_state(St.adm_bal_who); await call.answer()

@router.message(St.adm_bal_who)
async def _(msg, state: FSMContext):
    if msg.from_user.id not in _admins: return
    if not msg.text.isdigit(): await msg.answer("Faqat raqam!"); return
    tid=int(msg.text)
    u=await db("SELECT user_id FROM users WHERE user_id=?",(tid,),fo=True)
    if not u: await msg.answer("User topilmadi!"); return
    await state.update_data(tid=tid); await msg.answer("Miqdor (+ yoki -):"); await state.set_state(St.adm_bal_amt)

# Ban/Unban
@router.callback_query(F.data=="ad_ban")
async def adm_ban(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("Ban/Unban uchun User ID kiriting (agar ban bo'lsa unban, aksincha):"); await state.set_state(St.adm_ban); await call.answer()

@router.message(St.adm_ban)
async def _(msg, state: FSMContext):
    if msg.from_user.id not in _admins: return
    if not msg.text.isdigit(): await msg.answer("Raqam!"); return
    tid=int(msg.text)
    u=await db("SELECT banned FROM users WHERE user_id=?",(tid,),fo=True)
    if not u: await msg.answer("User yo'q!"); return
    new = 0 if u[0] else 1
    await db("UPDATE users SET banned=? WHERE user_id=?",(new,tid),c=True)
    await msg.answer(f"✅ User {tid} {'BAN' if new else 'UNBAN'} qilindi!"); await state.clear()
    if new: stop_worker(tid)

# User info
@router.callback_query(F.data=="ad_uinfo")
async def adm_uinfo(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("User ID kiriting:"); await state.set_state(St.adm_bal_who); await state.update_data(info_mode=True); await call.answer()

# Hammaga coin tarqatish
@router.callback_query(F.data=="ad_give")
async def adm_give(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("Har bir userga qancha coin beraman?"); await state.set_state(St.adm_bal_amt); await state.update_data(tid="__all__"); await call.answer()

# Broadcast
@router.callback_query(F.data=="ad_bc")
async def _(call, state: FSMContext):
    if call.from_user.id not in _admins: return
    await call.message.answer("Broadcast xabarini yozing:"); await state.set_state(St.adm_bc); await call.answer()

@router.message(St.adm_bc)
async def _(msg, state: FSMContext):
    if msg.from_user.id not in _admins: return
    users=await db("SELECT user_id FROM users WHERE banned=0",fa=True); ok=fail=0; total=len(users) if users else 0
    st=await msg.answer("📢 Yuborilmoqda... 0%")
    for i,(uid,) in enumerate(users or [],1):
        try: await msg.copy_to(uid); ok+=1
        except: fail+=1
        if i%20==0 and total>0:
            try: await st.edit_text(f"📢 {i*100//total}% ({i}/{total})")
            except: pass
        await asyncio.sleep(0.04)
    await msg.answer(f"✅ Yuborildi: {ok} | ❌ Xato: {fail}"); await state.clear()

# Parol
@router.callback_query(F.data=="ad_pass")
async def _(c, state: FSMContext):
    if c.from_user.id not in _admins: return
    await c.message.answer("Yangi parol (4+ belgi):"); await state.set_state(St.adm_val); await state.update_data(key="admin_code"); await c.answer()

@router.callback_query(F.data=="ad_exit")
async def _(call, state: FSMContext):
    _admins.discard(call.from_user.id); await state.clear()
    try: await call.message.delete()
    except: pass
    lang=await get_lang(call.from_user.id)
    await call.message.answer("🚪 Chqildi."); await call.answer()

# Admin qiymat saqlash — narx/bonus/o'yin/VIP/kontakt sozlamalari shu yerda saqlanadi
@router.message(St.adm_val)
async def adm_val_save(msg: Message, state: FSMContext):
    if msg.from_user.id not in _admins: return
    d=await state.get_data(); key=d.get("key","")
    val = msg.text.strip()
    if key=="__game__":
        gs = d.get("game_set","")
        parts = val.split()
        try:
            if gs=="slot":
                await set_s("slot_min",parts[0]); await set_s("slot_max",parts[1])
            elif gs=="slotm":
                await set_s("slot_mult2",parts[0]); await set_s("slot_mult5",parts[1])
            elif gs=="dice":
                await set_s("dice_min",parts[0]); await set_s("dice_max",parts[1])
            elif gs=="dicem":
                await set_s("dice_mult",parts[0])
            elif gs=="cf":
                await set_s("cf_min",parts[0]); await set_s("cf_max",parts[1])
            elif gs=="cfm":
                await set_s("cf_mult",parts[0])
            await msg.answer("✅ Saqlandi!")
        except Exception as e:
            await msg.answer(f"❌ Xato: {e}")
    elif key=="__vip__":
        parts=val.split()
        try:
            await set_s("vip_price",parts[0]); await set_s("vip_days",parts[1])
            await msg.answer("✅ VIP narx/kun saqlandi!")
        except: await msg.answer("❌ Format: 500 30")
    elif key and not key.startswith("__"):
        await set_s(key,val); await msg.answer("✅ Saqlandi!")
    else:
        await msg.answer("❌"); return
    await state.clear()

# Balans miqdorini saqlash — bitta userga ham, "Hammaga tarqatish" (__all__) uchun ham ishlaydi
@router.message(St.adm_bal_amt)
async def bal_amt_handler(msg: Message, state: FSMContext):
    if msg.from_user.id not in _admins: return
    d=await state.get_data(); tid=d.get("tid")
    try: amt=int(msg.text.strip())
    except: await msg.answer("Raqam!"); return
    if tid=="__all__":
        users=await db("SELECT user_id FROM users WHERE banned=0",fa=True)
        for (uid,) in (users or []):
            await add_coins(uid,amt)
        await msg.answer(f"✅ Barchaga {amt} Coin berildi! ({len(users)} user)")
        await state.clear(); return
    # oddiy bitta user
    await add_coins(tid,amt); nc=await get_coins(tid)
    await msg.answer(f"✅ Balans: {nc}"); await state.clear()

# ═══════════════════════════════════════════════
# RESUME VA MAIN
# ═══════════════════════════════════════════════
async def resume_tasks():
    rows = await db("SELECT DISTINCT user_id FROM user_photos",fa=True)
    for (uid,) in (rows or []):
        try: load_user_photos(uid)
        except: pass
    rows = await db("SELECT DISTINCT user_id FROM user_bio_texts",fa=True)
    for (uid,) in (rows or []):
        try: load_bio_texts(uid)
        except: pass
    act = await db("SELECT user_id,session_string FROM users WHERE (nick_status='active' OR photo_status='active' OR bio_status='active') AND session_string IS NOT NULL AND banned=0",fa=True)
    if act:
        for uid,sess in act:
            try: start_worker(uid,sess)
            except Exception as e: logger.error(f"resume {uid}: {e}")
        logger.info(f"Resumed {len(act)} workers")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.startup.register(lambda *a: resume_tasks())
    logger.info("🚀 Bot v3.0 ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi!")
 
