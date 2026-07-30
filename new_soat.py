# ═══════════════════════════════════════════════════════════════
# SOAT BOT — BITTA FAYLDA TO'LIQ KOD
# Faqat shu faylni ishga tushiring: python main.py
# ═══════════════════════════════════════════════════════════════

import asyncio
import sqlite3
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ═══════════════════════════════════════════════════════════════
# SOZLAMALAR
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = "BOTINGIZ_TOKENINI_SHU_YERGA_YOZING"
DB_PATH = "soatbot.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = Router()

# ═══════════════════════════════════════════════════════════════
# 3 TILLI LUG'AT
# ═══════════════════════════════════════════════════════════════

TEXTS = {
    "welcome": {
        "uz": (
            "Assalomu alaykum! 👋\n"
            "«@cloc_qoy_bot» ga Xush kelibsiz.\n\n"
            "Bot orqali quyidagilarni amalga oshirishingiz mumkin:\n\n"
            "⏰ Profilga jonli soat o'rnatish\n"
            "🖼 Profil rasmiga soat qo'yish\n"
            "🎁 Coin yig'ish va do'stlarni taklif qilish\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "ru": (
            "Ассаламу алейкум! 👋\n"
            "Добро пожаловать в «@cloc_qoy_bot».\n\n"
            "С помощью бота вы можете:\n\n"
            "⏰ Установить живые часы в профиль\n"
            "🖼 Добавить часы на фото профиля\n"
            "🎁 Собирать монеты и приглашать друзей\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "en": (
            "Assalomu alaykum! 👋\n"
            "Welcome to «@cloc_qoy_bot».\n\n"
            "With this bot you can:\n\n"
            "⏰ Set live clock on your profile\n"
            "🖼 Add clock to your profile photo\n"
            "🎁 Collect coins and invite friends\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
    },
    "choose_lang": {
        "uz": "Tilni tanlang 👇",
        "ru": "Выберите язык 👇",
        "en": "Choose language 👇",
    },
    "lang_done": {
        "uz": "✅ Til o'zbek tiliga o'zgartirildi!",
        "ru": "✅ Язык изменён на русский!",
        "en": "✅ Language changed to English!",
    },
    "main_menu": {
        "uz": (
            "🤖 <b>JONLI SOAT BOTI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ Profilingizga jonli Toshkent vaqtini o'rnating!\n\n"
            "👇 Bo'limni tanlang:"
        ),
        "ru": (
            "🤖 <b>БОТ ЖИВЫХ ЧАСОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ Установите живое время Ташкента в профиль!\n\n"
            "👇 Выберите раздел:"
        ),
        "en": (
            "🤖 <b>LIVE CLOCK BOT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ Set live Tashkent time on your profile!\n\n"
            "👇 Choose a section:"
        ),
    },
    "btn_login": {
        "uz": "🔐 Telegram ulanish",
        "ru": "🔐 Подключить Telegram",
        "en": "🔐 Connect Telegram",
    },
    "btn_clock": {
        "uz": "⚙️ Soat Sozlamalari",
        "ru": "⚙️ Настройки часов",
        "en": "⚙️ Clock Settings",
    },
    "btn_coins": {
        "uz": "🎁 Coin Yig'ish & Referal",
        "ru": "🎁 Монеты & Реферал",
        "en": "🎁 Coins & Referral",
    },
    "btn_balance": {
        "uz": "💰 Balans & Do'kon",
        "ru": "💰 Баланс & Магазин",
        "en": "💰 Balance & Shop",
    },
    "btn_top": {
        "uz": "🏆 Top Foydalanuvchilar",
        "ru": "🏆 Топ пользователей",
        "en": "🏆 Top Users",
    },
    "btn_lang": {
        "uz": "🌐 Tilni o'zgartirish",
        "ru": "🌐 Сменить язык",
        "en": "🌐 Change Language",
    },
    "btn_back": {
        "uz": "⬅️ Orqaga",
        "ru": "⬅️ Назад",
        "en": "⬅️ Back",
    },
    "wrong_lang": {
        "uz": "❌ Iltimos, quyidagi tugmalardan birini bosing!",
        "ru": "❌ Пожалуйста, нажмите одну из кнопок!",
        "en": "❌ Please press one of the buttons!",
    },
    "coming_soon": {
        "uz": "⏳ Bu funksiya keyingi bosqichda qo'shiladi...",
        "ru": "⏳ Эта функция будет добавлена позже...",
        "en": "⏳ This feature will be added later...",
    },
}


def t(key, lang="uz"):
    """Tarjima olish"""
    entry = TEXTS.get(key, {})
    return entry.get(lang, entry.get("uz", f"[{key}]"))


# ═══════════════════════════════════════════════════════════════
# DATABASE (MA'LUMOTLAR BAZASI)
# ═══════════════════════════════════════════════════════════════

def _db(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        cur = conn.cursor()
        cur.execute(query, params)
        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()
        if commit:
            conn.commit()
        return result
    except sqlite3.Error as e:
        logger.error(f"DB xato: {e}")
        if commit and conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


async def db(query, params=(), fetchone=False, fetchall=False, commit=False):
    return await asyncio.to_thread(_db, query, params, fetchone, fetchall, commit)


def init_db():
    """Bazani yaratish"""
    _db("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            full_name  TEXT,
            language   TEXT DEFAULT NULL,
            phone      TEXT,
            session_string TEXT,
            coins      INTEGER DEFAULT 0,
            clock_status   TEXT DEFAULT 'stopped',
            clock_style    INTEGER DEFAULT 1,
            photo_clock_active INTEGER DEFAULT 0,
            photo_style    INTEGER DEFAULT 1,
            photo_color    INTEGER DEFAULT 1,
            referrer_id    INTEGER,
            last_bonus     TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """, commit=True)

    _db("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """, commit=True)

    _db("""
        CREATE TABLE IF NOT EXISTS user_styles (
            user_id  INTEGER,
            style_id INTEGER,
            PRIMARY KEY (user_id, style_id)
        )
    """, commit=True)

    # Standart sozlamalar
    defaults = {
        "admin_code": "AzA1221",
        "daily_bonus": "10",
        "ref_bonus": "20",
        "photo_clock_price": "25",
        "admin_contact": "@admin",
        "support_text": "Adminga yozing.",
    }
    for k, v in defaults.items():
        _db("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (k, v), commit=True)


init_db()


# ═══════════════════════════════════════════════════════════════
# DATABASE YORDAMCHI FUNKSIYALAR
# ═══════════════════════════════════════════════════════════════

async def get_user_lang(user_id):
    """Foydalanuvchi tilini olish"""
    r = await db("SELECT language FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return r[0] if r and r[0] else None


async def set_user_lang(user_id, lang):
    """Foydalanuvchi tilini saqlash"""
    await db("UPDATE users SET language=? WHERE user_id=?", (lang, user_id), commit=True)



async def register_user(user_id, username, full_name, ref_id=None):
    """Foydalanuvchini ro'yxatdan o'tkazish"""
    existing = await db("SELECT user_id FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not existing:
        ref = ref_id if ref_id and ref_id != user_id else None
        await db(
            "INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, ref),
            commit=True,
        )
        # Referal bonus
        if ref:
            r = await db("SELECT value FROM system_settings WHERE key='ref_bonus'", fetchone=True)
            bonus = int(r[0]) if r else 20
            await db("UPDATE users SET coins = coins + ? WHERE user_id=?", (bonus, ref), commit=True)
    else:
        await db(
            "UPDATE users SET username=?, full_name=? WHERE user_id=?",
            (username, full_name, user_id),
            commit=True,
        )


async def get_setting(key, default=""):
    r = await db("SELECT value FROM system_settings WHERE key=?", (key,), fetchone=True)
    return r[0] if r and r[0] else default


async def get_user_coins(user_id):
    r = await db("SELECT coins FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return r[0] if r and r[0] is not None else 0


# ═══════════════════════════════════════════════════════════════
# FSM HOLATLARI
# ═══════════════════════════════════════════════════════════════

class LangState(StatesGroup):
    choosing = State()


# ═══════════════════════════════════════════════════════════════
# KLAVIATURALAR (TUGMALAR)
# ═══════════════════════════════════════════════════════════════

LANG_MAP = {
    "🇺🇿 O'zbekcha": "uz",
    "🇷🇺 Русский": "ru",
    "🇺🇸 English": "en",
}


def lang_keyboard():
    """Til tanlash tugmalari (Reply Keyboard)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha")],
            [KeyboardButton(text="🇷🇺 Русский")],
            [KeyboardButton(text="🇺🇸 English")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(lang="uz"):
    """Asosiy menyu tugmalari (Inline Keyboard)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_login", lang), callback_data="login")],
        [InlineKeyboardButton(text=t("btn_clock", lang), callback_data="main_clock_menu")],
        [InlineKeyboardButton(text=t("btn_coins", lang), callback_data="earn_coins_menu")],
        [InlineKeyboardButton(text=t("btn_balance", lang), callback_data="user_balance_menu")],
        [InlineKeyboardButton(text=t("btn_top", lang), callback_data="show_leaderboard")],
        [InlineKeyboardButton(text=t("btn_lang", lang), callback_data="change_language")],
    ])


# ═══════════════════════════════════════════════════════════════
# BOSQICH 1: /start — WELCOME XABARI
# ═══════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Oldingi holatni tozalash
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "User"

    # Referal tekshirish
    args = message.text.split()
    ref_id = None
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])

    # Bazaga yozish
    await register_user(user_id, username, full_name, ref_id)

    # Agar oldin til tanlagan bo'lsa — to'g'ridan-to'g'ri menyuga
    saved_lang = await get_user_lang(user_id)
    if saved_lang:
        await message.answer(
            t("main_menu", saved_lang),
            reply_markup=main_menu_keyboard(saved_lang),
            parse_mode="HTML",
        )
        return

    # ━━━ BIRINCHI MARTA KIRGAN ━━━
    # 1. Welcome xabari
    welcome = (
        f"Assalomu alaykum! 👋\n"
        f"«@cloc_qoy_bot» ga Xush kelibsiz.\n\n"
        f"Bot orqali quyidagilarni amalga oshirishingiz mumkin:\n\n"
        f"⏰ Profilga jonli soat o'rnatish\n"
        f"🖼 Profil rasmiga soat qo'yish\n"
        f"🎁 Coin yig'ish va do'stlarni taklif qilish\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(welcome)

    # 2. Til tanlash
    await message.answer(
        "Tilni tanlang 👇\nВыберите язык 👇\nChoose language 👇",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(LangState.choosing)


# ═══════════════════════════════════════════════════════════════
# BOSQICH 2: TIL TANLASH
# ═══════════════════════════════════════════════════════════════

@router.message(LangState.choosing)
async def process_lang(message: Message, state: FSMContext):
    text = message.text.strip()
    lang_code = LANG_MAP.get(text)

    # Noto'g'ri tugma bosilsa
    if not lang_code:
        await message.answer(
            "❌ Iltimos, quyidagi tugmalardan birini bosing!\n"
            "❌ Пожалуйста, нажмите одну из кнопок!\n"
            "❌ Please press one of the buttons!",
            reply_markup=lang_keyboard(),
        )
        return

    user_id = message.from_user.id

    # Tilni bazaga saqlash
    await set_user_lang(user_id, lang_code)

    # Holatni tozalash
    await state.clear()

    # Tasdiqlash xabari
    await message.answer(
        t("lang_done", lang_code),
        reply_markup=ReplyKeyboardRemove(),
    )

    # ━━━ ASOSIY MENYUNI KO'RSATISH ━━━
    await message.answer(
        t("main_menu", lang_code),
        reply_markup=main_menu_keyboard(lang_code),
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════════
# BOSQICH 3: ASOSIY MENYUGA QAYTISH
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "main_menu")
async def back_to_menu(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.message.edit_text(
        t("main_menu", lang),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════
# BOSQICH 4: TIL O'ZGARTIRISH (MENYUDAN)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "change_language")
async def change_lang(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Tilni tanlang 👇\nВыберите язык 👇\nChoose language 👇",
        reply_markup=lang_keyboard(),
    )
    await state.set_state(LangState.choosing)
    await call.answer()


# ═══════════════════════════════════════════════════════════════
# PLACEHOLDER TUGMALAR (Keyingi bosqichda to'ldiramiz)
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "login")
async def pl_login(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.answer(t("coming_soon", lang), show_alert=True)


@router.callback_query(F.data == "main_clock_menu")
async def pl_clock(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.answer(t("coming_soon", lang), show_alert=True)


@router.callback_query(F.data == "earn_coins_menu")
async def pl_coins(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.answer(t("coming_soon", lang), show_alert=True)


@router.callback_query(F.data == "user_balance_menu")
async def pl_balance(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.answer(t("coming_soon", lang), show_alert=True)


@router.callback_query(F.data == "show_leaderboard")
async def pl_top(call: CallbackQuery):
    lang = await get_user_lang(call.from_user.id) or "uz"
    await call.answer(t("coming_soon", lang), show_alert=True)


# ═══════════════════════════════════════════════════════════════
# BOTNI ISHGA TUSHIRISH
# ═══════════════════════════════════════════════════════════════

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)



    logger.info("🚀 Bot ishga tushdi!")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi!")
