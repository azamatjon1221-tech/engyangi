
# Soat bot tuzatilgan · PY
import asyncio
import sqlite3
import logging
import re
import io
import os
from datetime import datetime, timedelta
from typing import Dict, Any
 
import pytz
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
 
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, FloodWaitError,
    PhoneCodeInvalidError, AuthKeyDuplicatedError,
    PhoneNumberInvalidError, PhoneNumberBannedError,
    ApiIdInvalidError,
)
from PIL import Image, ImageDraw, ImageFont
 
# ═══════════════════════════════════════════════════
# SOZLAMALAR — O'ZINGIZNIKINI YOZING!
# ═══════════════════════════════════════════════════
BOT_TOKEN = "8518801019:AAEh_xguZ01w_LcAam_GRagHbs987TiEruY"
API_ID = 2691229
API_HASH = "b90611f46f1a08fe9584828ff1425bc4"
DB_PATH = "soatbot.db"
DEVICE_KWARGS = dict(
    device_model="Samsung Galaxy S23",
    system_version="4.16.30-vxCUSTOM",
    app_version="10.5.4",
    lang_code="uz",
)
 
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
router = Router()
 
_pending: Dict[int, Dict[str, Any]] = {}
_tasks: Dict[int, asyncio.Task] = {}
_photos: Dict[int, list] = {}
_admins: set = set()
 
# ═══════════════════════════════════════════════════
# 3 TILLI LUG'AT
# ═══════════════════════════════════════════════════
T = {
    "welcome": {
        "uz": "Assalomu alaykum! 👋\n«@cloc_qoy_bot» ga Xush kelibsiz.\n\nBot orqali quyidagilarni amalga oshirishingiz mumkin:\n\n⏰ Profilga jonli soat o'rnatish\n🖼 Profil rasmiga soat qo'yish\n🎁 Coin yig'ish va do'stlarni taklif qilish\n\n━━━━━━━━━━━━━━━━",
        "ru": "Ассаламу алейкум! 👋\nДобро пожаловать в «@cloc_qoy_bot».\n\nС помощью бота вы можете:\n\n⏰ Установить живые часы в профиль\n🖼 Добавить часы на фото профиля\n🎁 Собирать монеты и приглашать друзей\n\n━━━━━━━━━━━━━━━━",
        "en": "Assalomu alaykum! 👋\nWelcome to «@cloc_qoy_bot».\n\nWith this bot you can:\n\n⏰ Set live clock on your profile\n🖼 Add clock to your profile photo\n🎁 Collect coins and invite friends\n\n━━━━━━━━━━━━━━━━",
    },
    "choose_lang": {"uz": "Tilni tanlang 👇", "ru": "Выберите язык 👇", "en": "Choose language 👇"},
    "lang_done": {"uz": "✅ O'zbek tili tanlandi!", "ru": "✅ Выбран русский язык!", "en": "✅ English selected!"},
    "main_menu": {
        "uz": "🤖 <b>JONLI SOAT BOTI</b>\n━━━━━━━━━━━━━━━━\n✨ Profilingizga jonli vaqt o'rnating!\n\n👇 Bo'limni tanlang:",
        "ru": "🤖 <b>БОТ ЖИВЫХ ЧАСОВ</b>\n━━━━━━━━━━━━━━━━\n✨ Установите живое время в профиль!\n\n👇 Выберите раздел:",
        "en": "🤖 <b>LIVE CLOCK BOT</b>\n━━━━━━━━━━━━━━━━\n✨ Set live time on your profile!\n\n👇 Choose section:",
    },
    "btn_login": {"uz": "🔐 Telegram ulanish", "ru": "🔐 Подключить Telegram", "en": "🔐 Connect Telegram"},
    "btn_clock": {"uz": "⚙️ Soat Sozlamalari", "ru": "⚙️ Настройки часов", "en": "⚙️ Clock Settings"},
    "btn_coins": {"uz": "🎁 Coin & Referal", "ru": "🎁 Монеты & Реферал", "en": "🎁 Coins & Referral"},
    "btn_balance": {"uz": "💰 Balans & Do'kon", "ru": "💰 Баланс & Магазин", "en": "💰 Balance & Shop"},
    "btn_top": {"uz": "🏆 Top Foydalanuvchilar", "ru": "🏆 Топ пользователей", "en": "🏆 Top Users"},
    "btn_lang": {"uz": "🌐 Til o'zgartirish", "ru": "🌐 Сменить язык", "en": "🌐 Change Language"},
    "clock_menu": {
        "uz": "⚙️ <b>SOAT SOZLAMALARI</b>\n\nQaysi turni tanlaysiz?",
        "ru": "⚙️ <b>НАСТРОЙКИ ЧАСОВ</b>\n\nВыберите тип:",
        "en": "⚙️ <b>CLOCK SETTINGS</b>\n\nChoose type:",
    },
    "btn_nick": {"uz": "✏️ Nik soati", "ru": "✏️ Часы в нике", "en": "✏️ Nick clock"},
    "btn_photo": {"uz": "🖼 Rasm soati", "ru": "🖼 Фото часы", "en": "🖼 Photo clock"},
    "btn_stop": {"uz": "⏹ Soatni o'chirish", "ru": "⏹ Остановить часы", "en": "⏹ Stop clock"},
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад", "en": "⬅️ Back"},
    "send_phone": {
        "uz": "🔐 <b>TELEGRAM ULANISH</b>\n\n📱 Telefon raqamingizni yuboring:\n\n<i>Masalan: +998901234567</i>",
        "ru": "🔐 <b>ПОДКЛЮЧЕНИЕ TELEGRAM</b>\n\n📱 Отправьте номер телефона:\n\n<i>Например: +998901234567</i>",
        "en": "🔐 <b>CONNECT TELEGRAM</b>\n\n📱 Send your phone number:\n\n<i>Example: +998901234567</i>",
    },
    "phone_btn": {"uz": "📱 Raqam yuborish", "ru": "📱 Отправить номер", "en": "📱 Send number"},
    "code_sending": {"uz": "🔄 Kod yuborilmoqda...", "ru": "🔄 Отправка кода...", "en": "🔄 Sending code..."},
    "code_sent_app": {
        "uz": "📩 <b>Kod Telegram ilovangizga yuborildi!</b>\n\n⚠️ <b>MUHIM:</b> Sizga kelgan kodga <b>bir harf qo'shib</b> yozing!\n\nMasalan kod <code>12345</code> bo'lsa:\n➡️ <code>a12345</code> yoki <code>12345x</code> deb yozing\n\n<i>Bu Telegram bloklashdan himoya qiladi.</i>",
        "ru": "📩 <b>Код отправлен в приложение Telegram!</b>\n\n⚠️ <b>ВАЖНО:</b> Добавьте <b>одну букву</b> к коду!\n\nНапример если код <code>12345</code>:\n➡️ Напишите <code>a12345</code> или <code>12345x</code>\n\n<i>Это защищает от блокировки Telegram.</i>",
        "en": "📩 <b>Code sent to your Telegram app!</b>\n\n⚠️ <b>IMPORTANT:</b> Add <b>one letter</b> to the code!\n\nFor example if code is <code>12345</code>:\n➡️ Write <code>a12345</code> or <code>12345x</code>\n\n<i>This protects from Telegram blocking.</i>",
    },
    "code_sent_sms": {
        "uz": "📲 <b>Kod SMS orqali yuborildi!</b>\n\n⚠️ <b>MUHIM:</b> Kodga <b>bir harf qo'shib</b> yozing!\n\nMasalan kod <code>12345</code> bo'lsa:\n➡️ <code>a12345</code> deb yozing",
        "ru": "📲 <b>Код отправлен по SMS!</b>\n\n⚠️ <b>ВАЖНО:</b> Добавьте <b>одну букву</b> к коду!\n\nНапример если код <code>12345</code>:\n➡️ Напишите <code>a12345</code>",
        "en": "📲 <b>Code sent via SMS!</b>\n\n⚠️ <b>IMPORTANT:</b> Add <b>one letter</b> to the code!\n\nFor example if code is <code>12345</code>:\n➡️ Write <code>a12345</code>",
    },
    "resend_sms": {"uz": "📲 SMS orqali qayta yuborish", "ru": "📲 Повторить по SMS", "en": "📲 Resend via SMS"},
    "enter_2fa": {"uz": "🔐 2FA parolni kiriting:", "ru": "🔐 Введите 2FA пароль:", "en": "🔐 Enter 2FA password:"},
    "login_ok": {
        "uz": "🎉 <b>Muvaffaqiyatli ulandi!</b>\n\nEndi ⚙️ Soat Sozlamalari orqali soatni yoqishingiz mumkin.",
        "ru": "🎉 <b>Успешно подключено!</b>\n\nТеперь включите часы через ⚙️ Настройки часов.",
        "en": "🎉 <b>Successfully connected!</b>\n\nNow enable clock via ⚙️ Clock Settings.",
    },
    "login_err": {"uz": "❌ Xatolik: ", "ru": "❌ Ошибка: ", "en": "❌ Error: "},
    "code_wrong": {"uz": "❌ Kod noto'g'ri! Qayta kiriting (harf qo'shib):", "ru": "❌ Неверный код! Повторите (с буквой):", "en": "❌ Wrong code! Try again (with letter):"},
    "need_login": {"uz": "⚠️ Avval 🔐 Telegram ulanish kerak!", "ru": "⚠️ Сначала подключите 🔐 Telegram!", "en": "⚠️ Connect 🔐 Telegram first!"},
    "phone_invalid": {"uz": "❌ Raqam noto'g'ri! Qayta kiriting:", "ru": "❌ Неверный номер! Повторите:", "en": "❌ Invalid number! Try again:"},
    "phone_banned": {"uz": "❌ Bu raqam Telegram'da bloklangan!", "ru": "❌ Этот номер заблокирован в Telegram!", "en": "❌ This number is banned in Telegram!"},
    "flood_wait": {"uz": "⏳ Telegram cheklovi! {sec} soniya kuting.", "ru": "⏳ Ограничение Telegram! Подождите {sec} сек.", "en": "⏳ Telegram limit! Wait {sec} seconds."},
    "timeout_err": {"uz": "⏳ Ulanish vaqti tugadi. Qayta urinib ko'ring.", "ru": "⏳ Время подключения истекло. Попробуйте снова.", "en": "⏳ Connection timeout. Try again."},
    "already_logged": {"uz": "✅ Siz allaqachon ulangansiz!", "ru": "✅ Вы уже подключены!", "en": "✅ You are already connected!"},
    # Coin
    "coin_menu": {
        "uz": "🎁 <b>COIN YIG'ISH</b>\n\n📅 Kunlik bonus: {daily} Coin\n👥 Referal: {ref} Coin",
        "ru": "🎁 <b>СБОР МОНЕТ</b>\n\n📅 Ежедневный бонус: {daily} Coin\n👥 Реферал: {ref} Coin",
        "en": "🎁 <b>EARN COINS</b>\n\n📅 Daily bonus: {daily} Coin\n👥 Referral: {ref} Coin",
    },
    "btn_daily": {"uz": "🎁 Kunlik bonus", "ru": "🎁 Ежедневный бонус", "en": "🎁 Daily bonus"},
    "btn_ref": {"uz": "🔗 Referal havola", "ru": "🔗 Реф. ссылка", "en": "🔗 Referral link"},
    "daily_ok": {"uz": "🎉 {amount} Coin olindi!", "ru": "🎉 Получено {amount} Coin!", "en": "🎉 Got {amount} Coins!"},
    "daily_wait": {"uz": "⏳ {h} soat {m} daqiqa kuting!", "ru": "⏳ Подождите {h}ч {m}мин!", "en": "⏳ Wait {h}h {m}min!"},
    "ref_text": {
        "uz": "🔗 <b>REFERAL HAVOLA</b>\n\n<code>{link}</code>\n\n👥 Do'stlar: {count} ta\n🎁 Har biri: {bonus} Coin",
        "ru": "🔗 <b>РЕФ. ССЫЛКА</b>\n\n<code>{link}</code>\n\n👥 Друзья: {count}\n🎁 За каждого: {bonus} Coin",
        "en": "🔗 <b>REFERRAL LINK</b>\n\n<code>{link}</code>\n\n👥 Friends: {count}\n🎁 Each: {bonus} Coin",
    },
    "balance_text": {
        "uz": "💰 <b>Balans:</b> {coins} Coin\n\n💳 Coin sotib olish:\n{support}\n\n👨‍💻 Admin: {admin}",
        "ru": "💰 <b>Баланс:</b> {coins} Coin\n\n💳 Купить монеты:\n{support}\n\n👨‍💻 Админ: {admin}",
        "en": "💰 <b>Balance:</b> {coins} Coin\n\n💳 Buy coins:\n{support}\n\n👨‍💻 Admin: {admin}",
    },
    "top_title": {"uz": "🏆 <b>TOP FOYDALANUVCHILAR</b>\n\n", "ru": "🏆 <b>ТОП ПОЛЬЗОВАТЕЛЕЙ</b>\n\n", "en": "🏆 <b>TOP USERS</b>\n\n"},
    "top_empty": {"uz": "Hali hech kim yo'q.", "ru": "Пока никого нет.", "en": "No users yet."},
    "nick_title": {"uz": "✏️ <b>Stil tanlang:</b>\n💰 Balans: {coins} Coin", "ru": "✏️ <b>Выберите стиль:</b>\n💰 Баланс: {coins} Coin", "en": "✏️ <b>Choose style:</b>\n💰 Balance: {coins} Coin"},
    "nick_bought": {"uz": "✅ Olingan", "ru": "✅ Куплено", "en": "✅ Owned"},
    "nick_started": {"uz": "✅ Soat ({name}) ishga tushdi! Har daqiqa yangilanadi.", "ru": "✅ Часы ({name}) запущены! Обновление каждую минуту.", "en": "✅ Clock ({name}) started! Updates every minute."},
    "no_coins": {"uz": "❌ Coin yetarli emas!", "ru": "❌ Недостаточно монет!", "en": "❌ Not enough coins!"},
    "style_bought": {"uz": "🎉 {name} — {price} Coin'ga xarid qilindi!", "ru": "🎉 {name} — куплен за {price} Coin!", "en": "🎉 {name} — bought for {price} Coins!"},
    "photo_send": {"uz": "🖼 Rasmingizni yuboring (💰 {price} Coin):", "ru": "🖼 Отправьте фото (💰 {price} Coin):", "en": "🖼 Send photo (💰 {price} Coin):"},
    "photo_got": {"uz": "✅ Rasm qabul qilindi! Stil tanlang:", "ru": "✅ Фото принято! Выберите стиль:", "en": "✅ Photo received! Choose style:"},
    "photo_color": {"uz": "🎨 Rang tanlang:", "ru": "🎨 Выберите цвет:", "en": "🎨 Choose color:"},
    "photo_started": {"uz": "🎉 Rasm soati ishga tushdi! {price} Coin yechildi.", "ru": "🎉 Фото-часы запущены! Списано {price} Coin.", "en": "🎉 Photo clock started! {price} Coins deducted."},
    "photo_need": {"uz": "❌ Rasm yuboring!", "ru": "❌ Отправьте фото!", "en": "❌ Send a photo!"},
    "clock_stopped": {"uz": "⏹ Soat o'chirildi!", "ru": "⏹ Часы остановлены!", "en": "⏹ Clock stopped!"},
    "admin_enter": {"uz": "🔑 Parolni kiriting:", "ru": "🔑 Введите пароль:", "en": "🔑 Enter password:"},
    "admin_ok": {"uz": "✅ Admin paneliga kirildi!", "ru": "✅ Вход в админ-панель!", "en": "✅ Admin panel access!"},
    "admin_wrong": {"uz": "❌ Noto'g'ri parol!", "ru": "❌ Неверный пароль!", "en": "❌ Wrong password!"},
    "admin_stats": {
        "uz": "📊 <b>STATISTIKA</b>\n\n👤 Jami: {total}\n⏰ Faol soatlar: {active}\n🖼 Rasm soatlar: {photo}\n💰 Jami coin: {coins}",
        "ru": "📊 <b>СТАТИСТИКА</b>\n\n👤 Всего: {total}\n⏰ Активных часов: {active}\n🖼 Фото часов: {photo}\n💰 Всего монет: {coins}",
        "en": "📊 <b>STATISTICS</b>\n\n👤 Total: {total}\n⏰ Active clocks: {active}\n🖼 Photo clocks: {photo}\n💰 Total coins: {coins}",
    },
    "admin_bonus_ask": {"uz": "Yangi kunlik bonus miqdori:", "ru": "Новый размер бонуса:", "en": "New bonus amount:"},
    "admin_ref_ask": {"uz": "Yangi referal bonus:", "ru": "Новый реф. бонус:", "en": "New referral bonus:"},
    "admin_photo_ask": {"uz": "Yangi rasm soat narxi:", "ru": "Новая цена фото-часов:", "en": "New photo clock price:"},
    "admin_contact_ask": {"uz": "Yangi admin kontakt:", "ru": "Новый контакт админа:", "en": "New admin contact:"},
    "admin_support_ask": {"uz": "Yangi support matni:", "ru": "Новый текст поддержки:", "en": "New support text:"},
    "admin_pass_ask": {"uz": "Yangi parol (4+ belgi):", "ru": "Новый пароль (4+ символов):", "en": "New password (4+ chars):"},
    "admin_balance_who": {"uz": "User ID kiriting:", "ru": "Введите User ID:", "en": "Enter User ID:"},
    "admin_balance_how": {"uz": "Miqdorni kiriting (+100 yoki -50):", "ru": "Введите сумму (+100 или -50):", "en": "Enter amount (+100 or -50):"},
    "admin_balance_done": {"uz": "✅ O'zgartirildi! Yangi: {coins} Coin", "ru": "✅ Изменено! Новый: {coins} Coin", "en": "✅ Changed! New: {coins} Coin"},
    "admin_broadcast_ask": {"uz": "📢 Xabarni yozing:", "ru": "📢 Напишите сообщение:", "en": "📢 Write message:"},
    "admin_broadcast_done": {"uz": "✅ Yuborildi: {ok} | ❌ Xato: {fail}", "ru": "✅ Отправлено: {ok} | ❌ Ошибка: {fail}", "en": "✅ Sent: {ok} | ❌ Failed: {fail}"},
    "admin_saved": {"uz": "✅ Saqlandi!", "ru": "✅ Сохранено!", "en": "✅ Saved!"},
    "admin_num_err": {"uz": "❌ Faqat raqam kiriting!", "ru": "❌ Только число!", "en": "❌ Numbers only!"},
    "admin_short": {"uz": "❌ Kamida 4 belgi!", "ru": "❌ Минимум 4 символа!", "en": "❌ Min 4 characters!"},
    "admin_no_user": {"uz": "❌ Bunday user topilmadi!", "ru": "❌ Пользователь не найден!", "en": "❌ User not found!"},
}
 
 
def t(key, lang="uz"):
    e = T.get(key, {})
    return e.get(lang, e.get("uz", f"[{key}]"))
 
 
# ═══════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════
def _db(q, p=(), fo=False, fa=False, c=False):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cur = conn.cursor()
        cur.execute(q, p)
        r = None
        if fo:
            r = cur.fetchone()
        elif fa:
            r = cur.fetchall()
        if c:
            conn.commit()
        return r
    except Exception as e:
        logger.error(f"DB: {e}")
        if c and conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
 
 
async def db(q, p=(), fo=False, fa=False, c=False):
    return await asyncio.to_thread(_db, q, p, fo, fa, c)
 
 
def init_db():
    _db("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        language TEXT, phone TEXT, session_string TEXT,
        coins INTEGER DEFAULT 0, clock_status TEXT DEFAULT 'stopped',
        clock_style INTEGER DEFAULT 1, photo_clock_active INTEGER DEFAULT 0,
        photo_style INTEGER DEFAULT 1, photo_color INTEGER DEFAULT 1,
        referrer_id INTEGER, last_bonus TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""", c=True)
    _db("CREATE TABLE IF NOT EXISTS system_settings (key TEXT PRIMARY KEY, value TEXT)", c=True)
    _db("CREATE TABLE IF NOT EXISTS user_styles (user_id INTEGER, style_id INTEGER, PRIMARY KEY(user_id,style_id))", c=True)
    for k, v in {"admin_code": "AzA1221", "daily_bonus": "10", "ref_bonus": "20",
                  "photo_clock_price": "25", "admin_contact": "@admin",
                  "support_text": "Adminga yozing."}.items():
        _db("INSERT OR IGNORE INTO system_settings VALUES(?,?)", (k, v), c=True)
 
 
init_db()
 
 
async def get_s(k, d=""):
    r = await db("SELECT value FROM system_settings WHERE key=?", (k,), fo=True)
    return r[0] if r and r[0] else d
 
 
async def set_s(k, v):
    await db("INSERT INTO system_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v), c=True)
 
 
async def get_lang(uid):
    r = await db("SELECT language FROM users WHERE user_id=?", (uid,), fo=True)
    return r[0] if r and r[0] else "uz"
 
 
async def set_lang(uid, lang):
    await db("UPDATE users SET language=? WHERE user_id=?", (lang, uid), c=True)
 
 
async def get_coins(uid):
    r = await db("SELECT coins FROM users WHERE user_id=?", (uid,), fo=True)
    return r[0] if r and r[0] is not None else 0
 
 
async def reg_user(uid, uname, fname, ref=None):
    ex = await db("SELECT user_id FROM users WHERE user_id=?", (uid,), fo=True)
    if not ex:
        rf = ref if ref and ref != uid else None
        await db("INSERT INTO users(user_id,username,full_name,referrer_id) VALUES(?,?,?,?)", (uid, uname, fname, rf), c=True)
        if rf:
            b = int(await get_s("ref_bonus", "20"))
            await db("UPDATE users SET coins=coins+? WHERE user_id=?", (b, rf), c=True)
    else:
        await db("UPDATE users SET username=?,full_name=? WHERE user_id=?", (uname, fname, uid), c=True)
 
 
# ═══════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════
TIME_STYLES = {
    1: {"name": "Klassik", "price": 0, "premium": False,
        "digits": {str(i): str(i) for i in range(10)}},
    2: {"name": "Kichik", "price": 12, "premium": False,
        "digits": {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}},
    3: {"name": "Tepada", "price": 12, "premium": False,
        "digits": {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}},
    4: {"name": "[Qavsli]", "price": 15, "premium": False, "pre": "[", "suf": "]",
        "digits": {str(i): str(i) for i in range(10)}},
    5: {"name": "💎 Doxira", "price": 40, "premium": True,
        "digits": {"0": "⓿", "1": "❶", "2": "❷", "3": "❸", "4": "❹", "5": "❺", "6": "❻", "7": "❼", "8": "❽", "9": "❾"}},
    6: {"name": "💎 Qalin", "price": 45, "premium": True,
        "digits": {"0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰", "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵"}},
    7: {"name": "💎 Aylanali", "price": 40, "premium": True,
        "digits": {"0": "⓪", "1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤", "6": "⑥", "7": "⑦", "8": "⑧", "9": "⑨"}},
    8: {"name": "💎 Kvadrat", "price": 50, "premium": True,
        "digits": {"0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣"}},
}
 
PHOTO_STYLES = {1: "Oddiy (HH:MM)", 2: "• Nuqtali •", 3: "[Qavsli]"}
COLORS = {
    1: {"n": "⚪️ Oq", "c": (255, 255, 255)},
    2: {"n": "🟡 Oltin", "c": (255, 215, 0)},
    3: {"n": "🔵 Moviy", "c": (0, 255, 255)},
    4: {"n": "🌸 Pushti", "c": (255, 105, 180)},
}
 
 
def fmt_time(sid):
    now = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%H:%M")
    s = TIME_STYLES.get(sid, TIME_STYLES[1])
    d = s.get("digits", {})
    r = "".join(d.get(c, c) for c in now)
    return f"{s.get('pre', '')}{r}{s.get('suf', '')}"
 
 
def draw_clock(img_bytes, fstyle, cid):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        draw = ImageDraw.Draw(img)
        now = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%H:%M")
        w, h = img.size
        fs = int(min(w, h) * 0.15)
        font = None
        for p in ["arial.ttf", "DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
            try:
                font = ImageFont.truetype(p, fs)
                break
            except:
                continue
        if not font:
            font = ImageFont.load_default()
        txt = now
        if fstyle == 2:
            txt = f"• {now} •"
        elif fstyle == 3:
            txt = f"[{now}]"
        col = COLORS.get(cid, COLORS[1])["c"]
        bb = draw.textbbox((0, 0), txt, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x, y = (w - tw) / 2, (h - th) / 2
        pad = int(fs * 0.3)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rectangle([x - pad, y - pad, x + tw + pad, y + th + pad], fill=(0, 0, 0, 160))
        img = Image.alpha_composite(img, ov)
        ImageDraw.Draw(img).text((x, y), txt, font=font, fill=col)
        out = io.BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=90)
        return out.getvalue()
    except Exception as e:
        logger.error(f"Draw: {e}")
        return None
 
 
# ═══════════════════════════════════════════════════
# CLOCK SERVICE
# ═══════════════════════════════════════════════════
async def clock_worker(uid, sess):
    client = None
    try:
        client = TelegramClient(StringSession(sess), API_ID, API_HASH, **DEVICE_KWARGS)
        await client.connect()
        if not await client.is_user_authorized():
            await db("UPDATE users SET clock_status='stopped',session_string=NULL WHERE user_id=?", (uid,), c=True)
            return
        me = await client.get_me()
        base = me.first_name.split()[0] if me.first_name else "User"
        while True:
            u = await db(
                "SELECT clock_status,clock_style,photo_clock_active,photo_style,photo_color FROM users WHERE user_id=?",
                (uid,), fo=True)
            if not u or u[0] != 'active':
                break
            try:
                nn = f"{base} {fmt_time(u[1] or 1)}"
                if me.first_name != nn:
                    await client(functions.account.UpdateProfileRequest(first_name=nn))
                    me.first_name = nn
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except:
                pass
            if u[2] and uid in _photos and _photos[uid]:
                try:
                    ed = await asyncio.to_thread(draw_clock, _photos[uid][0], u[3] or 1, u[4] or 1)
                    if ed:
                        f = await client.upload_file(ed, file_name="c.jpg")
                        await client(functions.photos.UploadProfilePhotoRequest(file=f))
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except:
                    pass
            now = datetime.now(pytz.timezone("Asia/Tashkent"))
            await asyncio.sleep(max(60 - now.second, 1))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Worker {uid}: {e}")
    finally:
        if client and client.is_connected():
            await client.disconnect()
 
 
def start_clock(uid, sess):
    old = _tasks.pop(uid, None)
    if old and not old.done():
        old.cancel()
    _tasks[uid] = asyncio.create_task(clock_worker(uid, sess))
 
 
def stop_clock(uid):
    tk = _tasks.pop(uid, None)
    if tk and not tk.done():
        tk.cancel()
    _photos.pop(uid, None)
 
 
# ═══════════════════════════════════════════════════
# FSM STATES
# ═══════════════════════════════════════════════════
class St(StatesGroup):
    lang = State()
    phone = State()
    code = State()
    passw = State()
    photo = State()
    photo_style = State()
    photo_color = State()
    adm_code = State()
    adm_daily = State()
    adm_ref = State()
    adm_photo = State()
    adm_contact = State()
    adm_support = State()
    adm_pass = State()
    adm_bal_who = State()
    adm_bal_amt = State()
    adm_broadcast = State()
 
 
# ═══════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════
def menu_kb(lang="uz"):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t("btn_login", lang)), KeyboardButton(text=t("btn_clock", lang))],
        [KeyboardButton(text=t("btn_coins", lang)), KeyboardButton(text=t("btn_balance", lang))],
        [KeyboardButton(text=t("btn_top", lang)), KeyboardButton(text=t("btn_lang", lang))],
    ], resize_keyboard=True)
 
 
def lang_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🇺🇿 O'zbekcha")],
        [KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇺🇸 English")],
    ], resize_keyboard=True, one_time_keyboard=True)
 
 
LANG_MAP = {"🇺🇿 O'zbekcha": "uz", "🇷🇺 Русский": "ru", "🇺🇸 English": "en"}
 
 
# ═══════════════════════════════════════════════════
# TELETHON — KOD YUBORISH FUNKSIYASI (TO'LIQ LOGLANADIGAN VERSIYA)
# ═══════════════════════════════════════════════════
from telethon.errors import (
    SessionPasswordNeededError, FloodWaitError,
    PhoneCodeInvalidError, PhoneCodeExpiredError, AuthKeyDuplicatedError,
    PhoneNumberInvalidError, PhoneNumberBannedError, PhoneNumberUnoccupiedError,
    ApiIdInvalidError, SendCodeUnavailableError,
)
from telethon.errors.rpcerrorlist import RPCError
 
 
async def send_code_safely(phone: str, force_sms: bool = False):
    """
    Xavfsiz kod yuborish.
    MUHIM: endi har qanday xatolik logger.exception() orqali serveringiz
    konsoliga (yoki log fayliga) TO'LIQ yoziladi. Agar kod hali ham
    kelmasa, konsoldagi "SEND_CODE XATO" satrini toping va shu matnni
    yuboring — aniq sababni shundan bilib olamiz.
    """
    client = TelegramClient(StringSession(), API_ID, API_HASH, **DEVICE_KWARGS)
 
    # 1-bosqich: ulanish (agar server Telegram'ga chiqa olmasa, aynan shu yerda ko'rinadi)
    try:
        await asyncio.wait_for(client.connect(), timeout=30)
    except asyncio.TimeoutError:
        logger.error(f"[LOGIN] Telegram serverlariga ulanib bo'lmadi (timeout). Server tarmog'ini tekshiring.")
        return None, None, None, "timeout"
    except Exception as e:
        logger.exception(f"[LOGIN] connect() bosqichida xato: {e}")
        return None, None, None, str(e)
 
    if not client.is_connected():
        logger.error("[LOGIN] client ulanmadi (is_connected=False), lekin xato ham chiqmadi.")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "not_connected"
 
    # 2-bosqich: kodni yuborish
    try:
        result = await asyncio.wait_for(
            client.send_code_request(phone, force_sms=force_sms),
            timeout=30
        )
 
        type_name = type(result.type).__name__.lower()
        if "sms" in type_name:
            sent_via = "sms"
        elif "call" in type_name:
            sent_via = "call"
        elif "app" in type_name:
            sent_via = "app"
        else:
            sent_via = "app"
 
        logger.info(f"[LOGIN] Kod yuborildi -> phone={phone} orqali={sent_via} (type={type_name})")
        return client, result.phone_code_hash, sent_via, None
 
    except FloodWaitError as e:
        logger.warning(f"[LOGIN] FloodWait: {e.seconds} soniya kutish kerak (phone={phone})")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, f"flood:{e.seconds}"
 
    except PhoneNumberInvalidError:
        logger.warning(f"[LOGIN] Telefon raqam noto'g'ri: {phone}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "invalid_phone"
 
    except PhoneNumberBannedError:
        logger.warning(f"[LOGIN] Telefon raqam bloklangan: {phone}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "banned_phone"
 
    except PhoneNumberUnoccupiedError:
        logger.warning(f"[LOGIN] Bu raqamda Telegram akkaunti ro'yxatdan o'tmagan: {phone}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "not_registered"
 
    except SendCodeUnavailableError:
        logger.error(f"[LOGIN] Telegram bu raqamga kod yuborishni vaqtincha rad etdi: {phone}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "send_unavailable"
 
    except ApiIdInvalidError:
        logger.error("[LOGIN] API_ID / API_HASH NOTO'G'RI! my.telegram.org dan tekshiring.")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "api_invalid"
 
    except asyncio.TimeoutError:
        logger.error(f"[LOGIN] send_code_request timeout (phone={phone})")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, "timeout"
 
    except RPCError as e:
        # Telegram serverining o'zi qaytargan xato — nomi va kodi bilan to'liq log qilinadi
        logger.exception(f"[LOGIN] Telegram RPC xatosi: code={getattr(e, 'code', '?')} message={e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, f"rpc:{e}"
 
    except Exception as e:
        logger.exception(f"[LOGIN] Kutilmagan xato (send_code_request): {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None, None, None, str(e)
 
 
def extract_code(raw_text: str) -> str:
    """Foydalanuvchi yuborgan matndan faqat raqamlarni ajratib olish"""
    return "".join(filter(str.isdigit, raw_text or ""))
 
 
def normalize_phone(raw: str) -> str:
    """Telefon raqamni standart formatga keltirish"""
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned
 
 
# ═══════════════════════════════════════════════════
# LOGIN: TELEFON → KOD → 2FA (TO'LIQ LOGLANADIGAN VERSIYA)
# ═══════════════════════════════════════════════════
@router.message(St.phone)
async def proc_phone(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    lang = await get_lang(uid)
 
    # Orqaga tugmasi
    if msg.text and msg.text.strip() == t("btn_back", lang):
        await state.clear()
        await msg.answer(t("main_menu", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
        return
 
    # Telefon raqamni olish
    if msg.contact:
        raw_phone = msg.contact.phone_number
    elif msg.text:
        raw_phone = msg.text
    else:
        await msg.answer(t("phone_invalid", lang))
        return
 
    phone = normalize_phone(raw_phone)
 
    # Raqam formatini tekshirish
    if len(phone) < 10:
        await msg.answer(t("phone_invalid", lang))
        return
 
    logger.info(f"[LOGIN] Foydalanuvchi {uid} raqami bilan urindi: {phone}")
 
    # Yuborilmoqda...
    wait_msg = await msg.answer(t("code_sending", lang), reply_markup=ReplyKeyboardRemove())
 
    # Eski clientni tozalash
    old = _pending.pop(uid, None)
    if old and old.get("client"):
        try:
            await old["client"].disconnect()
        except Exception:
            pass
 
    # Kod yuborish
    client, phone_hash, sent_via, error = await send_code_safely(phone)
 
    if error:
        logger.error(f"[LOGIN] Foydalanuvchi {uid} uchun kod yuborilmadi. Sabab: {error}")
        # Xatolikni tarjima qilish
        if error.startswith("flood:"):
            sec = error.split(":")[1]
            err_text = t("flood_wait", lang).format(sec=sec)
        elif error == "invalid_phone":
            err_text = t("phone_invalid", lang)
        elif error == "banned_phone":
            err_text = t("phone_banned", lang)
        elif error == "not_registered":
            err_text = t("login_err", lang) + "Bu raqamda Telegram akkaunti yo'q."
        elif error == "send_unavailable":
            err_text = t("login_err", lang) + "Telegram bu raqamga hozircha kod yubora olmayapti, birozdan so'ng qayta urining."
        elif error == "not_connected":
            err_text = t("login_err", lang) + "Serverdan Telegram'ga ulanib bo'lmadi. Admin bilan bog'laning."
        elif error == "timeout":
            err_text = t("timeout_err", lang)
        elif error == "api_invalid":
            err_text = "❌ API_ID yoki API_HASH noto'g'ri!"
        else:
            err_text = t("login_err", lang) + error
 
        await wait_msg.edit_text(err_text)
        await msg.answer(t("main_menu", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
        await state.clear()
        return
 
    # Muvaffaqiyatli — saqlash
    _pending[uid] = {
        "client": client,
        "phone": phone,
        "hash": phone_hash,
    }
    await state.update_data(phone=phone)
    await state.set_state(St.code)
 
    # Kod qayerga yuborildi
    if sent_via == "sms":
        code_text = t("code_sent_sms", lang)
    else:
        code_text = t("code_sent_app", lang)
 
    # SMS qayta yuborish tugmasi (faqat app/call orqali kelganda)
    kb = None
    if sent_via != "sms":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("resend_sms", lang), callback_data="resend_sms")]
        ])
 
    await wait_msg.edit_text(code_text, reply_markup=kb, parse_mode="HTML")
 
 
# ═══════════════════════════════════════════════════
# SMS QAYTA YUBORISH
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "resend_sms")
async def resend_sms(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    lang = await get_lang(uid)
    info = _pending.get(uid)
 
    if not info:
        await call.answer("❌ Session expired. /start", show_alert=True)
        return
 
    await call.answer("🔄 SMS yuborilmoqda...")
 
    # Eski clientni uzish
    if info.get("client"):
        try:
            await info["client"].disconnect()
        except Exception:
            pass
 
    phone = info["phone"]
 
    # Yangi client bilan majburiy SMS orqali yuborish
    client, phone_hash, sent_via, error = await send_code_safely(phone, force_sms=True)
 
    if error:
        logger.error(f"[LOGIN] Foydalanuvchi {uid} uchun SMS qayta yuborilmadi. Sabab: {error}")
        if error.startswith("flood:"):
            sec = error.split(":")[1]
            await call.message.answer(t("flood_wait", lang).format(sec=sec))
        else:
            await call.message.answer(t("login_err", lang) + str(error))
        return
 
    _pending[uid] = {"client": client, "phone": phone, "hash": phone_hash}
    await call.message.answer(t("code_sent_sms", lang), parse_mode="HTML")
 
 
# ═══════════════════════════════════════════════════
# KOD KIRITISH (TO'LIQ LOGLANADIGAN VERSIYA)
# ═══════════════════════════════════════════════════
@router.message(St.code)
async def proc_code(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    lang = await get_lang(uid)
    info = _pending.get(uid)
 
    if not info:
        await msg.answer("❌ Session expired. /start bosing.", reply_markup=menu_kb(lang))
        await state.clear()
        return
 
    # Foydalanuvchi yuborgan matndan FAQAT raqamlarni olish
    code = extract_code(msg.text)
 
    if not code or len(code) < 3:
        await msg.answer(t("code_wrong", lang))
        return
 
    client = info["client"]
    phone = info["phone"]
    phone_hash = info["hash"]
 
    try:
        await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=phone_hash
        )
    except SessionPasswordNeededError:
        await state.set_state(St.passw)
        await msg.answer(t("enter_2fa", lang))
        return
    except PhoneCodeInvalidError:
        logger.warning(f"[LOGIN] {uid} noto'g'ri kod kiritdi.")
        await msg.answer(t("code_wrong", lang))
        return
    except PhoneCodeExpiredError:
        logger.warning(f"[LOGIN] {uid} uchun kod muddati tugagan.")
        await msg.answer(t("login_err", lang) + "Kod muddati tugagan, qaytadan /start bosing.")
        await state.clear()
        try:
            await client.disconnect()
        except Exception:
            pass
        _pending.pop(uid, None)
        return
    except FloodWaitError as e:
        logger.warning(f"[LOGIN] {uid} FloodWait: {e.seconds}s")
        await msg.answer(t("flood_wait", lang).format(sec=e.seconds))
        return
    except Exception as e:
        logger.exception(f"[LOGIN] {uid} sign_in bosqichida xato: {e}")
        await msg.answer(t("login_err", lang) + str(e))
        await state.clear()
        try:
            await client.disconnect()
        except Exception:
            pass
        _pending.pop(uid, None)
        await msg.answer(t("main_menu", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
        return
 
    # Muvaffaqiyatli login!
    session_string = client.session.save()
    await db("UPDATE users SET phone=?,session_string=? WHERE user_id=?",
             (phone, session_string, uid), c=True)
 
    logger.info(f"[LOGIN] {uid} muvaffaqiyatli ulandi (phone={phone}).")
 
    try:
        await client.disconnect()
    except Exception:
        pass
    _pending.pop(uid, None)
    await state.clear()
 
    await msg.answer(t("login_ok", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
 
 
# ═══════════════════════════════════════════════════
# 2FA PAROL
# ═══════════════════════════════════════════════════
@router.message(St.passw)
async def proc_2fa(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    lang = await get_lang(uid)
    info = _pending.get(uid)
 
    if not info:
        await msg.answer("❌ Session expired. /start", reply_markup=menu_kb(lang))
        await state.clear()
        return
 
    client = info["client"]
 
    try:
        await client.sign_in(password=msg.text.strip())
    except Exception as e:
        logger.exception(f"[LOGIN] {uid} 2FA bosqichida xato: {e}")
        await msg.answer(t("login_err", lang) + str(e))
        return
 
    session_string = client.session.save()
    await db("UPDATE users SET phone=?,session_string=? WHERE user_id=?",
             (info["phone"], session_string, uid), c=True)
 
    logger.info(f"[LOGIN] {uid} 2FA orqali muvaffaqiyatli ulandi.")
 
    try:
        await client.disconnect()
    except Exception:
        pass
    _pending.pop(uid, None)
    await state.clear()
 
    await msg.answer(t("login_ok", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
 
 
# ═══════════════════════════════════════════════════
# NIK SOATI
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "nick_clock")
async def nick_menu(call: CallbackQuery):
    uid = call.from_user.id
    lang = await get_lang(uid)
    coins = await get_coins(uid)
    bought = [r[0] for r in (await db("SELECT style_id FROM user_styles WHERE user_id=?", (uid,), fa=True) or [])]
    btns = []
    for sid, s in TIME_STYLES.items():
        ex = fmt_time(sid)
        tag = t("nick_bought", lang) if sid in bought or s["price"] == 0 else f"💰{s['price']}"
        btns.append([InlineKeyboardButton(text=f"{s['name']} ({ex}) — {tag}", callback_data=f"style_{sid}")])
    await call.message.edit_text(
        t("nick_title", lang).format(coins=coins),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML"
    )
    await call.answer()
 
 
@router.callback_query(F.data.startswith("style_"))
async def pick_style(call: CallbackQuery):
    uid = call.from_user.id
    lang = await get_lang(uid)
    sid = int(call.data.split("_")[1])
    s = TIME_STYLES.get(sid)
    if not s:
        return await call.answer("❌", show_alert=True)
 
    sess = await db("SELECT session_string FROM users WHERE user_id=?", (uid,), fo=True)
    if not sess or not sess[0]:
        await call.answer(t("need_login", lang), show_alert=True)
        return
 
    bought = await db("SELECT 1 FROM user_styles WHERE user_id=? AND style_id=?", (uid, sid), fo=True)
    if not bought and s["price"] > 0:
        coins = await get_coins(uid)
        if coins < s["price"]:
            await call.answer(t("no_coins", lang), show_alert=True)
            return
        await db("UPDATE users SET coins=coins-? WHERE user_id=?", (s["price"], uid), c=True)
        await db("INSERT INTO user_styles VALUES(?,?)", (uid, sid), c=True)
        await call.message.answer(t("style_bought", lang).format(name=s["name"], price=s["price"]))
 
    await db("UPDATE users SET clock_status='active',clock_style=? WHERE user_id=?", (sid, uid), c=True)
    start_clock(uid, sess[0])
    await call.message.answer(t("nick_started", lang).format(name=s["name"]), reply_markup=menu_kb(lang))
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# RASM SOATI
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "photo_clock")
async def photo_start(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    lang = await get_lang(uid)
    sess = await db("SELECT session_string FROM users WHERE user_id=?", (uid,), fo=True)
    if not sess or not sess[0]:
        await call.answer(t("need_login", lang), show_alert=True)
        return
    price = int(await get_s("photo_clock_price", "25"))
    coins = await get_coins(uid)
    if coins < price:
        await call.answer(t("no_coins", lang), show_alert=True)
        return
    await call.message.answer(t("photo_send", lang).format(price=price))
    await state.set_state(St.photo)
    await call.answer()
 
 
@router.message(St.photo)
async def photo_recv(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if not msg.photo:
        await msg.answer(t("photo_need", lang))
        return
    f = await msg.bot.get_file(msg.photo[-1].file_id)
    bio = await msg.bot.download_file(f.file_path)
    _photos[msg.from_user.id] = [bio.read()]
    btns = [[InlineKeyboardButton(text=v, callback_data=f"pstyle_{k}")] for k, v in PHOTO_STYLES.items()]
    await msg.answer(t("photo_got", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_style)
 
 
@router.callback_query(St.photo_style, F.data.startswith("pstyle_"))
async def photo_style_pick(call: CallbackQuery, state: FSMContext):
    lang = await get_lang(call.from_user.id)
    await state.update_data(ps=int(call.data.split("_")[1]))
    btns = [[InlineKeyboardButton(text=v["n"], callback_data=f"pcol_{k}")] for k, v in COLORS.items()]
    await call.message.answer(t("photo_color", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await state.set_state(St.photo_color)
    await call.answer()
 
 
@router.callback_query(St.photo_color, F.data.startswith("pcol_"))
async def photo_color_pick(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    lang = await get_lang(uid)
    cid = int(call.data.split("_")[1])
    data = await state.get_data()
    ps = data.get("ps", 1)
    price = int(await get_s("photo_clock_price", "25"))
    coins = await get_coins(uid)
    if coins < price:
        await call.answer(t("no_coins", lang), show_alert=True)
        await state.clear()
        return
    sess = await db("SELECT session_string FROM users WHERE user_id=?", (uid,), fo=True)
    if not sess or not sess[0]:
        await state.clear()
        return
    await db("UPDATE users SET coins=coins-?,clock_status='active',photo_clock_active=1,photo_style=?,photo_color=? WHERE user_id=?",
             (price, ps, cid, uid), c=True)
    start_clock(uid, sess[0])
    await call.message.answer(t("photo_started", lang).format(price=price), reply_markup=menu_kb(lang))
    await state.clear()
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# SOATNI O'CHIRISH
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "stop_clock")
async def stop_c(call: CallbackQuery):
    uid = call.from_user.id
    lang = await get_lang(uid)
    await db("UPDATE users SET clock_status='stopped',photo_clock_active=0 WHERE user_id=?", (uid,), c=True)
    stop_clock(uid)
    await call.message.answer(t("clock_stopped", lang), reply_markup=menu_kb(lang))
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# KUNLIK BONUS
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "daily_bonus")
async def daily(call: CallbackQuery):
    uid = call.from_user.id
    lang = await get_lang(uid)
    tz = pytz.timezone("Asia/Tashkent")
    now = datetime.now(tz)
    r = await db("SELECT last_bonus FROM users WHERE user_id=?", (uid,), fo=True)
    if r and r[0]:
        try:
            last = datetime.fromisoformat(r[0])
            if now - last < timedelta(hours=24):
                nx = last + timedelta(hours=24)
                d = nx - now
                h, rem = divmod(int(d.total_seconds()), 3600)
                m = rem // 60
                await call.answer(t("daily_wait", lang).format(h=h, m=m), show_alert=True)
                return
        except:
            pass
    amt = int(await get_s("daily_bonus", "10"))
    await db("UPDATE users SET coins=coins+?,last_bonus=? WHERE user_id=?", (amt, now.isoformat(), uid), c=True)
    await call.message.answer(t("daily_ok", lang).format(amount=amt))
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# REFERAL
# ═══════════════════════════════════════════════════
@router.callback_query(F.data == "ref_link")
async def ref(call: CallbackQuery):
    uid = call.from_user.id
    lang = await get_lang(uid)
    bot_info = await call.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={uid}"
    cnt = (await db("SELECT COUNT(*) FROM users WHERE referrer_id=?", (uid,), fo=True))[0]
    bonus = await get_s("ref_bonus", "20")
    await call.message.answer(t("ref_text", lang).format(link=link, count=cnt, bonus=bonus), parse_mode="HTML")
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════════════════
def adm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data="adm_stats")],
        [InlineKeyboardButton(text="🎁 Daily", callback_data="adm_daily"),
         InlineKeyboardButton(text="👥 Ref", callback_data="adm_ref")],
        [InlineKeyboardButton(text="🖼 Photo $", callback_data="adm_photo"),
         InlineKeyboardButton(text="💰 Balance", callback_data="adm_bal")],
        [InlineKeyboardButton(text="📞 Contact", callback_data="adm_contact"),
         InlineKeyboardButton(text="📝 Support", callback_data="adm_support")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🔑 Password", callback_data="adm_pass"),
         InlineKeyboardButton(text="🚪 Exit", callback_data="adm_exit")],
    ])
 
 
@router.message(Command("admin"))
async def adm_cmd(msg: Message, state: FSMContext):
    if msg.from_user.id in _admins:
        await msg.answer("⚙️ <b>ADMIN PANEL</b>", reply_markup=adm_kb(), parse_mode="HTML")
    else:
        lang = await get_lang(msg.from_user.id)
        await msg.answer(t("admin_enter", lang))
        await state.set_state(St.adm_code)
 
 
@router.message(St.adm_code)
async def adm_login(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    real = await get_s("admin_code", "")
    if msg.text.strip() == real and real:
        _admins.add(msg.from_user.id)
        await state.clear()
        await msg.answer(t("admin_ok", lang), reply_markup=adm_kb())
    else:
        await msg.answer(t("admin_wrong", lang))
 
 
@router.callback_query(F.data == "adm_stats")
async def adm_stats(call: CallbackQuery):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    total = (await db("SELECT COUNT(*) FROM users", fo=True))[0]
    active = (await db("SELECT COUNT(*) FROM users WHERE clock_status='active'", fo=True))[0]
    photo = (await db("SELECT COUNT(*) FROM users WHERE photo_clock_active=1", fo=True))[0]
    coins = (await db("SELECT SUM(coins) FROM users", fo=True))[0] or 0
    await call.message.edit_text(
        t("admin_stats", lang).format(total=total, active=active, photo=photo, coins=coins),
        reply_markup=adm_kb(), parse_mode="HTML"
    )
    await call.answer()
 
 
@router.callback_query(F.data == "adm_daily")
async def adm_daily(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_bonus_ask", lang))
    await state.set_state(St.adm_daily)
    await call.answer()
 
 
@router.message(St.adm_daily)
async def adm_daily_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if msg.text.isdigit():
        await set_s("daily_bonus", msg.text.strip())
        await msg.answer(t("admin_saved", lang))
        await state.clear()
    else:
        await msg.answer(t("admin_num_err", lang))
 
 
@router.callback_query(F.data == "adm_ref")
async def adm_ref(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_ref_ask", lang))
    await state.set_state(St.adm_ref)
    await call.answer()
 
 
@router.message(St.adm_ref)
async def adm_ref_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if msg.text.isdigit():
        await set_s("ref_bonus", msg.text.strip())
        await msg.answer(t("admin_saved", lang))
        await state.clear()
    else:
        await msg.answer(t("admin_num_err", lang))
 
 
@router.callback_query(F.data == "adm_photo")
async def adm_photo(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_photo_ask", lang))
    await state.set_state(St.adm_photo)
    await call.answer()
 
 
@router.message(St.adm_photo)
async def adm_photo_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if msg.text.isdigit():
        await set_s("photo_clock_price", msg.text.strip())
        await msg.answer(t("admin_saved", lang))
        await state.clear()
    else:
        await msg.answer(t("admin_num_err", lang))
 
 
@router.callback_query(F.data == "adm_contact")
async def adm_contact(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_contact_ask", lang))
    await state.set_state(St.adm_contact)
    await call.answer()
 
 
@router.message(St.adm_contact)
async def adm_contact_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await set_s("admin_contact", msg.text.strip())
    await msg.answer(t("admin_saved", lang))
    await state.clear()
 
 
@router.callback_query(F.data == "adm_support")
async def adm_support(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_support_ask", lang))
    await state.set_state(St.adm_support)
    await call.answer()
 
 
@router.message(St.adm_support)
async def adm_support_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    await set_s("support_text", msg.text.strip())
    await msg.answer(t("admin_saved", lang))
    await state.clear()
 
 
@router.callback_query(F.data == "adm_pass")
async def adm_pass(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_pass_ask", lang))
    await state.set_state(St.adm_pass)
    await call.answer()
 
 
@router.message(St.adm_pass)
async def adm_pass_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if len(msg.text.strip()) < 4:
        await msg.answer(t("admin_short", lang))
        return
    await set_s("admin_code", msg.text.strip())
    await msg.answer(t("admin_saved", lang))
    await state.clear()
 
 
@router.callback_query(F.data == "adm_bal")
async def adm_bal(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_balance_who", lang))
    await state.set_state(St.adm_bal_who)
    await call.answer()
 
 
@router.message(St.adm_bal_who)
async def adm_bal_who(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    if not msg.text.isdigit():
        await msg.answer(t("admin_num_err", lang))
        return
    tid = int(msg.text.strip())
    u = await db("SELECT user_id FROM users WHERE user_id=?", (tid,), fo=True)
    if not u:
        await msg.answer(t("admin_no_user", lang))
        return
    await state.update_data(tid=tid)
    await msg.answer(t("admin_balance_how", lang))
    await state.set_state(St.adm_bal_amt)
 
 
@router.message(St.adm_bal_amt)
async def adm_bal_amt(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    try:
        amt = int(msg.text.strip())
    except:
        await msg.answer(t("admin_num_err", lang))
        return
    data = await state.get_data()
    tid = data["tid"]
    await db("UPDATE users SET coins=coins+? WHERE user_id=?", (amt, tid), c=True)
    nc = await get_coins(tid)
    await msg.answer(t("admin_balance_done", lang).format(coins=nc))
    await state.clear()
 
 
@router.callback_query(F.data == "adm_broadcast")
async def adm_bc(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in _admins:
        return
    lang = await get_lang(call.from_user.id)
    await call.message.answer(t("admin_broadcast_ask", lang))
    await state.set_state(St.adm_broadcast)
    await call.answer()
 
 
@router.message(St.adm_broadcast)
async def adm_bc_s(msg: Message, state: FSMContext):
    lang = await get_lang(msg.from_user.id)
    users = await db("SELECT user_id FROM users", fa=True)
    ok = fail = 0
    for (uid,) in (users or []):
        try:
            await msg.copy_to(uid)
            ok += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    await msg.answer(t("admin_broadcast_done", lang).format(ok=ok, fail=fail))
    await state.clear()
 
 
@router.callback_query(F.data == "adm_exit")
async def adm_exit(call: CallbackQuery, state: FSMContext):
    _admins.discard(call.from_user.id)
    await state.clear()
    lang = await get_lang(call.from_user.id)
    await call.message.delete()
    await call.message.answer(t("main_menu", lang), reply_markup=menu_kb(lang), parse_mode="HTML")
    await call.answer()
 
 
# ═══════════════════════════════════════════════════
# RESUME CLOCKS ON STARTUP
# ═══════════════════════════════════════════════════
async def resume_clocks():
    rows = await db("SELECT user_id,session_string FROM users WHERE clock_status='active' AND session_string IS NOT NULL", fa=True)
    if rows:
        for uid, sess in rows:
            start_clock(uid, sess)
        logger.info(f"Resumed {len(rows)} clocks")
 
 
# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.startup.register(lambda *a: resume_clocks())
    logger.info("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)
 
 
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi!")
 
