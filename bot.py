import asyncio
import os
import aiosqlite
import hashlib
import random
import string
from datetime import datetime, timedelta, timezone, date
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==== НАСТРОЙКИ ====
BOT_TOKEN = "9259003904:AAGO259i8dQHPKln3PQbzDaj0iwkTAHTdt4"
NORILSK_TZ = timezone(timedelta(hours=7))
SECRET_CODES = ["ADMIN77", "BOSS999", "CHEF555", "GURU123"]
OWNER = "@wertowoi"
ADMIN_COMMAND = "flvadminpanelArseniy011289serch"

STUDENTS = [
    "Агаев Элим Висалович", "Бабаян Каролина Гамлетовна", "Бадалова Чахлик Халил кызы",
    "Баронина Анастасия Олеговна", "Березина Алина Сергеевна", "Бочарова Ксения Максимовна",
    "Григорьева Полина Сергеевна", "Денисенков Арсений Антонович", "Елизарьева Лукерия АЛЕКС",
    "Ерастова Елизавета СЕРГ", "Еремичева Александра Евген", "Ишкильдин Камил Денисович",
    "Кондрачук Александра Ден", "Кызычакова Дарья Алексе", "Магомедова Аида Рагимовна",
    "Мельникова Полина Алекса", "Овечкина Мария Александ", "Орманжи Вадим",
    "Папко Захар Сергеевич", "Савчук Камила Игоревна", "Самошкина Арина Алекс",
    "Сеничева Алена Дмитриевна", "Солдатченкова Майя Владис", "Станкова Ксения Юрьевна",
    "Степанюк Софья Алексан", "Сюксяева Дарина Андреевна", "ТАУШЕВ САДАМ КРЫМ",
    "Хубежов Ларсан Михайлович", "Юдина Софья Игоревна", "Ягелло Анжела Игоревна"
]

VALID_NAMES = set()
for student in STUDENTS:
    parts = student.split()
    if len(parts) >= 2:
        VALID_NAMES.add((parts[0].lower(), parts[1].lower()))

DEFAULT_MENU = {
    "0": {"Завтрак": "Каша молочная, сыр, чай, хлеб", "Обед": "Салат, борщ, говядина, тефтели, гречка, компот", "Полдник": "Печенье, компот, чай"},
    "1": {"Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин", "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот", "Полдник": "Булочка, кофейный напиток"},
    "2": {"Завтрак": "Фрикадельки, овощи, чай с лимоном, пюре фруктовое", "Обед": "Салат из свеклы, суп крестьянский, говядина, рыба запеченная, компот", "Полдник": "Пирожки, молоко"},
    "3": {"Завтрак": "Каша молочная, сыр, чай, хлеб", "Обед": "Салат, борщ, говядина, тефтели, гречка, компот", "Полдник": "Печенье, компот, чай"},
    "4": {"Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин", "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот", "Полдник": "Булочка, кофейный напиток"}
}

RANKS_DATA = [
    ("🦗 Голодный кузнечик", 5), ("🦴 Скелетон", 10), ("🍞 Крошка хлеба", 20), ("🥚 Яйцо всмятку", 30),
    ("🍗 Цыпленок табака", 40), ("🍟 Любитель картошки", 50), ("🌭 Хот-дог критик", 60), ("🍔 Бургер-стажер", 70),
    ("🥪 Сэндвич-мастер", 85), ("🍕 Пицца-пацан", 100), ("🌮 Такос-воин", 120), ("🍣 Суши-ниндзя", 140),
    ("🍜 Рамен-сенсей", 160), ("🥩 Стейк-самурай", 180), ("🍖 Мясной магнат", 200), ("👑 Куриный король", 230),
    ("🔥 Повелитель гриля", 260), ("🍗 Генерал Гриль", 300), ("🌟 Легенда KFC", 350), ("👑 KFC BOSS", 400)
]

class Reg(StatesGroup):
    waiting_fio = State()
    waiting_password = State()
    waiting_secret = State()

class Auth(StatesGroup):
    waiting_password = State()

class Recovery(StatesGroup):
    waiting_code = State()
    waiting_new_password = State()

class Order(StatesGroup):
    choosing_date = State()
    choosing_meal = State()
    confirming = State()

class AdminDuty(StatesGroup):
    waiting_confirm = State()

class AdminMenuEdit(StatesGroup):
    waiting_text = State()

class AdminBtnAdd(StatesGroup):
    waiting_title = State()
    waiting_text = State()
    waiting_photo = State()

class AdminBroadcast(StatesGroup):
    waiting_text = State()

class AdminSettings(StatesGroup):
    waiting_help_text = State()
    waiting_deadline = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running"
def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

async def init_db():
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, fio TEXT, password TEXT, chat_id INTEGER, is_logged_in INTEGER DEFAULT 0, 
                is_admin INTEGER DEFAULT 0, recovery_code TEXT, is_banned INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, order_date TEXT, meals TEXT, created_at TEXT
            )
        """)
        await db.execute("CREATE TABLE IF NOT EXISTS used_codes (username TEXT, code TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS duty (date TEXT PRIMARY KEY, fio TEXT, username TEXT, answered INTEGER DEFAULT 0)")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                day TEXT, meal TEXT, text TEXT, PRIMARY KEY (day, meal)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, text TEXT, photo_id TEXT, pos INTEGER, parent_id INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        """)
        
        async with db.execute("SELECT COUNT(*) FROM settings") as cursor:
            if (await cursor.fetchone())[0] == 0:
                await db.execute("INSERT INTO settings (key, value) VALUES ('help_text', '👑 Владелец бота: @wertowoi\n🛡 Ответственные: ...')")
                await db.execute("INSERT INTO settings (key, value) VALUES ('deadline', '8:30')")
                await db.execute("INSERT INTO settings (key, value) VALUES ('orders_enabled', '1')")
        
        async with db.execute("SELECT COUNT(*) FROM menu") as cursor:
            if (await cursor.fetchone())[0] == 0:
                for day, meals in DEFAULT_MENU.items():
                    for meal, text in meals.items():
                        await db.execute("INSERT INTO menu (day, meal, text) VALUES (?, ?, ?)", (day, meal, text))
        await db.commit()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def gen_recovery_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(random.randint(6, 10)))

def get_start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Регистрация", callback_data="reg_start")],
        [InlineKeyboardButton(text="🔑 Войти", callback_data="auth_start")],
        [InlineKeyboardButton(text="🛡 Регистрация как ответственный", callback_data="reg_admin")]
    ])

async def get_main_menu(chat_id):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ? AND is_logged_in = 1", (chat_id,)) as cursor:
            res = await cursor.fetchone()
            is_admin = bool(res[0]) if res else False
            
        async with db.execute("SELECT id, title FROM custom_buttons WHERE parent_id = 0 ORDER BY pos ASC") as cursor:
            custom_btns = await cursor.fetchall()

    kb = [
        [KeyboardButton(text="🍽 Сделать заказ"), KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🏆 Лидеры")],
        [KeyboardButton(text="🆘 Помощь"), KeyboardButton(text="🚪 Выйти")]
    ]
    if is_admin:
        kb.insert(1, [KeyboardButton(text="📥 Панель ответственного")])
        
    for btn_id, title in custom_btns:
        kb.append([KeyboardButton(text=f"{title}")])

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)

def get_meal_kb(selected):
    kb = []
    for meal in ["Завтрак", "Обед", "Полдник"]:
        text = f"✅ {meal}" if meal in selected else f"⬜ {meal}"
        kb.append([InlineKeyboardButton(text=text, callback_data=f"toggle_{meal}")])
    if selected: kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="proceed")])
    kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==== РЕГИСТРАЦИЯ ====
@dp.callback_query(F.data == "reg_start")
async def reg_start(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    if not username: return await call.message.answer("Ошибка: У тебя не установлен юзернейм!")
    await state.update_data(username=f"@{username}", is_admin=False)
    await call.message.answer("Введи свои ФИО русскими буквами (Фамилия Имя):", reply_markup=get_cancel_kb())
    await state.set_state(Reg.waiting_fio)

@dp.callback_query(F.data == "reg_admin")
async def reg_admin_start(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    if not username: return await call.message.answer("Ошибка: У тебя не установлен юзернейм!")
    await state.update_data(username=f"@{username}", is_admin=True)
    await call.message.answer("Введи свои ФИО русскими буквами (Фамилия Имя):", reply_markup=get_cancel_kb())
    await state.set_state(Reg.waiting_fio)

@dp.message(Reg.waiting_fio)
async def reg_fio(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        return await message.answer("Ошибка! Введи хотя бы Фамилию и Имя. Попробуй еще раз:")
    fam, name = parts[0].lower(), parts[1].lower()
    if (fam, name) not in VALID_NAMES:
        return await message.answer("Ошибка! Такого ученика нет в списке (или опечатка). Проверь Фамилию и Имя и напиши снова:")
    await state.update_data(fio=text.upper())
    await message.answer("Придумай пароль:", reply_markup=get_cancel_kb())
    await state.set_state(Reg.waiting_password)

@dp.message(Reg.waiting_password)
async def reg_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    if len(pwd) < 3: return await message.answer("Слишком короткий пароль!")
    await state.update_data(password=hash_password(pwd))
    data = await state.get_data()
    if data.get("is_admin"):
        await message.answer("Введи секретный код ответственного:", reply_markup=get_cancel_kb())
        await state.set_state(Reg.waiting_secret)
    else:
        await save_user(message, state, is_admin=False)

@dp.message(Reg.waiting_secret)
async def reg_secret(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        if code not in SECRET_CODES:
            return await message.answer("Неверный код! Попробуй снова:")
        async with db.execute("SELECT code FROM used_codes WHERE username = ? AND code = ?", (data['username'], code)) as cursor:
            if await cursor.fetchone():
                return await message.answer("Ты уже использовал этот код!")
        await db.execute("INSERT INTO used_codes (username, code) VALUES (?, ?)", (data['username'], code))
        await db.commit()
    await save_user(message, state, is_admin=True)

async def save_user(message: Message, state: FSMContext, is_admin: bool):
    data = await state.get_data()
    rec_code = gen_recovery_code()
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("INSERT INTO users (username, fio, password, chat_id, is_logged_in, is_admin, recovery_code) VALUES (?, ?, ?, ?, 1, ?, ?)",
                         (data['username'], data['fio'], data['password'], message.chat.id, int(is_admin), rec_code))
        await db.commit()
    role = "ОТВЕТСТВЕННОГО" if is_admin else "УЧЕНИКА"
    await message.answer(f"✅ Успешная регистрация {role}!\nФИО: {data['fio']}\n\n⚠️ **Код восстановления:** `{rec_code}`", reply_markup=await get_main_menu(message.chat.id), parse_mode="Markdown")
    await state.clear()

# ==== ВХОД ====
@dp.callback_query(F.data == "auth_start")
async def auth_start(call: CallbackQuery, state: FSMContext):
    username = f"@{call.from_user.username}"
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_logged_in FROM users WHERE username = ?", (username,)) as cursor:
            res = await cursor.fetchone()
            if not res: return await call.message.answer("Ты не зарегистрирован!")
            if res[0] == 1: return await call.message.answer("Аккаунт уже в сети!")
    await state.update_data(username=username)
    await call.message.edit_text("Введи пароль:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🤔 Забыл пароль", callback_data="forgot_pass")]]))
    await state.set_state(Auth.waiting_password)

@dp.callback_query(F.data == "forgot_pass")
async def forgot_pass(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи свой код восстановления:", reply_markup=get_cancel_kb())
    await state.set_state(Recovery.waiting_code)

@dp.message(Auth.waiting_password)
async def auth_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT password, is_admin FROM users WHERE username = ?", (data['username'],)) as cursor:
            res = await cursor.fetchone()
            if res and res[0] == hash_password(pwd):
                await db.execute("UPDATE users SET chat_id = ?, is_logged_in = 1 WHERE username = ?", (message.chat.id, data['username']))
                await db.commit()
                await message.answer("Успешный вход!", reply_markup=await get_main_menu(message.chat.id))
                await state.clear()
            else:
                await message.answer("Неверный пароль!")

@dp.message(Recovery.waiting_code)
async def rec_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username FROM users WHERE username = ? AND recovery_code = ?", (data['username'], code)) as cursor:
            if not await cursor.fetchone(): return await message.answer("Неверный код!")
    await message.answer("Код верный! Придумай новый пароль:", reply_markup=get_cancel_kb())
    await state.set_state(Recovery.waiting_new_password)

@dp.message(Recovery.waiting_new_password)
async def rec_new_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    if len(pwd) < 3: return await message.answer("Слишком короткий пароль!")
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(pwd), data['username']))
        await db.commit()
    await message.answer("✅ Пароль изменен!", reply_markup=get_start_kb())
    await state.clear()

@dp.message(F.text == "🚪 Выйти")
async def logout(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE users SET is_logged_in = 0 WHERE chat_id = ?", (message.chat.id,))
        await db.commit()
    await message.answer("Вы вышли из аккаунта.", reply_markup=get_start_kb())
    await state.clear()

# ==== ПРОФИЛЬ И ЛИДЕРЫ ====
@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username, fio FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return await message.answer("Войди в аккаунт.")
            username, fio = user
            async with db.execute("SELECT meals FROM orders WHERE username = ?", (username,)) as cursor:
                orders = await cursor.fetchall()
    score = 0.0
    b, l, p = 0, 0, 0
    for (meals,) in orders:
        if "Завтрак" in meals: b += 1; score += 0.5
        if "Обед" in meals: l += 1; score += 1.0
        if "Полдник" in meals: p += 1; score += 0.5

    current_rank = RANKS_DATA[0][0]
    next_threshold = RANKS_DATA[0][1]
    is_max = False
    for i, (rank_name, threshold) in enumerate(RANKS_DATA):
        if score >= threshold:
            current_rank = rank_name
            if i + 1 < len(RANKS_DATA): next_threshold = RANKS_DATA[i+1][1]
            else: next_threshold = threshold; is_max = True
        else: break
    if is_max: progress_text = "МАКСИМУМ"
    else: progress_text = f"({score} / {next_threshold})"

    text = f"👤 **Профиль**\n\n📛 ФИО: {fio}\n🔗 {username}\n\n🍳 Завтраков: {b}\n🍲 Обедов: {l}\n🥐 Полдников: {p}\n\n🏅 Звание: **{current_rank}** {progress_text}"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🏆 Лидеры")
async def leaderboard(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username, fio FROM users WHERE is_admin = 0") as cursor:
            users = await cursor.fetchall()
        async with db.execute("SELECT username, meals, created_at FROM orders ORDER BY created_at ASC") as cursor:
            orders = await cursor.fetchall()
    scores = {u[0]: {"fio": u[1], "score": 0.0, "first_order": "9999-12-31 23:59"} for u in users}
    for uname, meals, created_at in orders:
        if uname in scores:
            if "Завтрак" in meals: scores[uname]["score"] += 0.5
            if "Обед" in meals: scores[uname]["score"] += 1.0
            if "Полдник" in meals: scores[uname]["score"] += 0.5
            if created_at < scores[uname]["first_order"]: scores[uname]["first_order"] = created_at
    sorted_users = sorted(scores.items(), key=lambda item: (-item[1]["score"], item[1]["first_order"]))
    text = "🏆 **Топ-5 лидеров:**\n\n"
    count = 0
    for uname, data in sorted_users:
        if data["score"] == 0: continue
        count += 1
        if count > 5: break
        rank_name = RANKS_DATA[0][0]
        for r_name, threshold in RANKS_DATA:
            if data["score"] >= threshold: rank_name = r_name
            else: break
        text += f"{count}. {data['fio']} — {data['score']} баллов\n   {rank_name}\n\n"
    if count == 0: text += "Пока никто не сделал заказ."
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🆘 Помощь")
async def help_menu(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'help_text'") as cursor:
            help_text = (await cursor.fetchone())[0]
    await message.answer(f"🆘 **Помощь**\n\n{help_text}", parse_mode="Markdown")

# ==== АДМИН ПАНЕЛЬ ====
@dp.message(Command(ADMIN_COMMAND))
async def admin_command(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res or res[0] == 0: return await message.answer("У тебя нет прав для входа в админку.")
    text = (
        "👑 **Добро пожаловать в супер-админку!**\n\n"
        "Тут ты можешь управлять всем ботом, не трогая код.\n\n"
        "🛠 **Возможности:**\n"
        "1. **Меню**: Меняй текст еды на любой день.\n"
        "2. **Кнопки**: Создавай новые кнопки с текстом и фото (из галереи).\n"
        "3. **Вложенные меню**: Кнопки внутри кнопок (папки).\n"
        "4. **Порядок**: Двигай кнопки вверх/вниз стрелками.\n"
        "5. **Удаление**: Удаляй ненужные кнопки.\n"
        "6. **Рассылка**: Отправь сообщение всем ученикам сразу.\n"
        "7. **Настройки**: Время дедлайна, текст помощи, вкл/выкл заказы.\n"
        "8. **Статистика**: Смотри общее число заказов и учеников.\n\n"
        "Выбери действие ниже:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Редактировать меню", callback_data="admin_edit_menu")],
        [InlineKeyboardButton(text="🎛 Управление кнопками", callback_data="admin_manage_btns")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    await call.message.delete()
    await admin_command(call.message, None)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0") as cur: users_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as cur: orders_count = (await cur.fetchone())[0]
    text = f"📊 **Статистика:**\n\n👥 Учеников: {users_count}\n🍽 Всего заказов: {orders_count}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_settings")
async def admin_settings(call: CallbackQuery):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'deadline'") as cur: deadline = (await cur.fetchone())[0]
        async with db.execute("SELECT value FROM settings WHERE key = 'orders_enabled'") as cur: enabled = (await cur.fetchone())[0]
    status = "✅ Включены" if enabled == "1" else "❌ Выключены"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить текст помощи", callback_data="admin_edit_help")],
        [InlineKeyboardButton(text=f"⏰ Дедлайн: {deadline}", callback_data="admin_edit_deadline")],
        [InlineKeyboardButton(text=f"🍽 Заказы: {status}", callback_data="admin_toggle_orders")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    await call.message.edit_text("⚙️ **Настройки:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_edit_help")
async def admin_edit_help(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи новый текст для кнопки «🆘 Помощь»:")
    await state.set_state(AdminSettings.waiting_help_text)

@dp.message(AdminSettings.waiting_help_text)
async def save_help_text(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE settings SET value = ? WHERE key = 'help_text'", (message.text,))
        await db.commit()
    await message.answer("✅ Текст помощи обновлен!", reply_markup=await get_main_menu(message.chat.id))
    await state.clear()

@dp.callback_query(F.data == "admin_edit_deadline")
async def admin_edit_deadline(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи новое время дедлайна (например, 8:30 или 9:00):")
    await state.set_state(AdminSettings.waiting_deadline)

@dp.message(AdminSettings.waiting_deadline)
async def save_deadline(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE settings SET value = ? WHERE key = 'deadline'", (message.text,))
        await db.commit()
    await message.answer(f"✅ Дедлайн изменен на {message.text}", reply_markup=await get_main_menu(message.chat.id))
    await state.clear()

@dp.callback_query(F.data == "admin_toggle_orders")
async def toggle_orders(call: CallbackQuery):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'orders_enabled'") as cur: enabled = (await cur.fetchone())[0]
        new_val = "0" if enabled == "1" else "1"
        await db.execute("UPDATE settings SET value = ? WHERE key = 'orders_enabled'", (new_val,))
        await db.commit()
    await admin_settings(call)

# ==== РЕДАКТИРОВАНИЕ МЕНЮ ====
@dp.callback_query(F.data == "admin_edit_menu")
async def admin_edit_menu(call: CallbackQuery):
    days = ["Пн", "Вт", "Ср", "Чт", "Пт"]
    kb = [[InlineKeyboardButton(text=day, callback_data=f"adm_day_{i}")] for i, day in enumerate(days)]
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")])
    await call.message.edit_text("Выбери день:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("adm_day_"))
async def admin_choose_day(call: CallbackQuery):
    day_idx = int(call.data.split("_")[2])
    kb = [
        [InlineKeyboardButton(text="Завтрак", callback_data=f"adm_meal_{day_idx}_Завтрак")],
        [InlineKeyboardButton(text="Обед", callback_data=f"adm_meal_{day_idx}_Обед")],
        [InlineKeyboardButton(text="Полдник", callback_data=f"adm_meal_{day_idx}_Полдник")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edit_menu")]
    ]
    await call.message.edit_text(f"Что меняем на {['Пн','Вт','Ср','Чт','Пт'][day_idx]}?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("adm_meal_"))
async def admin_choose_meal(call: CallbackQuery, state: FSMContext):
    _, _, day_idx, meal = call.data.split("_")
    await state.update_data(day=day_idx, meal=meal)
    await call.message.edit_text(f"Введи новый текст для **{meal}**:")
    await state.set_state(AdminMenuEdit.waiting_text)

@dp.message(AdminMenuEdit.waiting_text)
async def admin_save_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE menu SET text = ? WHERE day = ? AND meal = ?", (message.text, data['day'], data['meal']))
        await db.commit()
    await message.answer("✅ Меню обновлено!", reply_markup=await get_main_menu(message.chat.id))
    await state.clear()

# ==== УПРАВЛЕНИЕ КНОПКАМИ ====
@dp.callback_query(F.data.startswith("admin_manage_btns"))
async def admin_manage_btns(call: CallbackQuery):
    parent_id = int(call.data.split("_")[3]) if "_" in call.data else 0
    kb = [
        [InlineKeyboardButton(text="➕ Создать кнопку", callback_data=f"btn_add_{parent_id}")],
        [InlineKeyboardButton(text="📝 Изменить/Удалить", callback_data=f"btn_edit_list_{parent_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    await call.message.edit_text("Управление кнопками:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("btn_add_"))
async def btn_add_start(call: CallbackQuery, state: FSMContext):
    parent_id = int(call.data.split("_")[2])
    await state.update_data(parent_id=parent_id)
    await call.message.edit_text("Введи название кнопки:")
    await state.set_state(AdminBtnAdd.waiting_title)

@dp.message(AdminBtnAdd.waiting_title)
async def btn_add_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введи текст при нажатии (или напиши 'НЕТ', если это папка):")
    await state.set_state(AdminBtnAdd.waiting_text)

@dp.message(AdminBtnAdd.waiting_text)
async def btn_add_text(message: Message, state: FSMContext):
    text = message.text
    if text.lower() == "нет": text = None
    await state.update_data(text=text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True)
    await message.answer("Отправь фото (или нажми «Пропустить»):", reply_markup=kb)
    await state.set_state(AdminBtnAdd.waiting_photo)

@dp.message(AdminBtnAdd.waiting_photo)
async def btn_add_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id if message.photo else None
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT MAX(pos) FROM custom_buttons WHERE parent_id = ?", (data['parent_id'],)) as cursor:
            max_pos = (await cursor.fetchone())[0] or 0
        await db.execute("INSERT INTO custom_buttons (title, text, photo_id, pos, parent_id) VALUES (?, ?, ?, ?, ?)", 
                         (data['title'], data['text'], photo_id, max_pos + 1, data['parent_id']))
        await db.commit()
    await message.answer(f"✅ Кнопка «{data['title']}» создана!", reply_markup=await get_main_menu(message.chat.id))
    await state.clear()

@dp.callback_query(F.data.startswith("btn_edit_list_"))
async def btn_edit_list(call: CallbackQuery):
    parent_id = int(call.data.split("_")[3])
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT id, title FROM custom_buttons WHERE parent_id = ? ORDER BY pos", (parent_id,)) as cursor:
            btns = await cursor.fetchall()
    if not btns: return await call.answer("Кнопок пока нет!", show_alert=True)
    kb = []
    for btn_id, title in btns:
        kb.append([InlineKeyboardButton(text=title, callback_data=f"btn_detail_{btn_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_manage_btns_{parent_id}")])
    await call.message.edit_text("Выбери кнопку для редактирования:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("btn_detail_"))
async def btn_detail(call: CallbackQuery):
    btn_id = int(call.data.split("_")[2])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼 Вверх", callback_data=f"move_up_{btn_id}"), InlineKeyboardButton(text="🔽 Вниз", callback_data=f"move_down_{btn_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"btn_delete_{btn_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_btns")]
    ])
    await call.message.edit_text("Что сделать с этой кнопкой?", reply_markup=kb)

@dp.callback_query(F.data.startswith("move_"))
async def btn_move(call: CallbackQuery):
    action, btn_id = call.data.split("_")[0], int(call.data.split("_")[1])
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT parent_id, pos FROM custom_buttons WHERE id = ?", (btn_id,)) as cursor:
            parent_id, pos = await cursor.fetchone()
        if action == "move_up":
            async with db.execute("SELECT id, pos FROM custom_buttons WHERE parent_id = ? AND pos < ? ORDER BY pos DESC LIMIT 1", (parent_id, pos)) as cursor:
                prev_btn = await cursor.fetchone()
            if prev_btn:
                await db.execute("UPDATE custom_buttons SET pos = ? WHERE id = ?", (prev_btn[1], btn_id))
                await db.execute("UPDATE custom_buttons SET pos = ? WHERE id = ?", (pos, prev_btn[0]))
        elif action == "move_down":
            async with db.execute("SELECT id, pos FROM custom_buttons WHERE parent_id = ? AND pos > ? ORDER BY pos ASC LIMIT 1", (parent_id, pos)) as cursor:
                next_btn = await cursor.fetchone()
            if next_btn:
                await db.execute("UPDATE custom_buttons SET pos = ? WHERE id = ?", (next_btn[1], btn_id))
                await db.execute("UPDATE custom_buttons SET pos = ? WHERE id = ?", (pos, next_btn[0]))
        await db.commit()
    await call.answer("Порядок обновлен!")
    await btn_detail(call)

@dp.callback_query(F.data.startswith("btn_delete_"))
async def btn_delete(call: CallbackQuery):
    btn_id = int(call.data.split("_")[2])
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("DELETE FROM custom_buttons WHERE id = ?", (btn_id,))
        await db.commit()
    await call.message.edit_text("🗑 Кнопка удалена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_manage_btns")]]))

# ==== РАССЫЛКА ====
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи текст для рассылки всем ученикам:")
    await state.set_state(AdminBroadcast.waiting_text)

@dp.message(AdminBroadcast.waiting_text)
async def admin_broadcast_send(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT chat_id FROM users WHERE is_logged_in = 1") as cursor:
            users = await cursor.fetchall()
    count = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 **Объявление:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
        except: pass
    await message.answer(f"✅ Рассылка отправлена {count} ученикам.", reply_markup=await get_main_menu(message.chat.id))
    await state.clear()

# ==== ПАНЕЛЬ ОТВЕТСТВЕННОГО ====
@dp.message(F.text == "📥 Панель ответственного")
async def admin_panel(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res or res[0] == 0: return await message.answer("Нет прав.")
        today = str(datetime.now(NORILSK_TZ).date())
        async with db.execute("SELECT answered FROM duty WHERE date = ? AND username = (SELECT username FROM users WHERE chat_id = ?)", (today, message.chat.id)) as cursor:
            answered = await cursor.fetchone()
    if answered:
        return await show_admin_menu(message)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],[KeyboardButton(text="🔙 Назад")]], resize_keyboard=True)
    await message.answer("Вы сегодня занимаетесь питанием?", reply_markup=kb)
    await state.set_state(AdminDuty.waiting_confirm)

@dp.message(AdminDuty.waiting_confirm)
async def admin_duty_confirm(message: Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        return await start(message, state)
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT fio, username FROM users WHERE chat_id = ?", (message.chat.id,)) as cursor:
            fio, uname = await cursor.fetchone()
        today = str(datetime.now(NORILSK_TZ).date())
        if message.text == "✅ Да":
            await db.execute("INSERT OR REPLACE INTO duty (date, fio, username, answered) VALUES (?, ?, ?, 1)", (today, fio, uname))
            await db.commit()
            await message.answer("Отлично! Вы назначены дежурным на сегодня.", reply_markup=await get_main_menu(message.chat.id))
        elif message.text == "❌ Нет":
            await db.execute("INSERT OR REPLACE INTO duty (date, fio, username, answered) VALUES (?, ?, ?, 1)", (today, fio, uname))
            await db.commit()
            await message.answer("Понял, вы не дежурите.", reply_markup=await get_main_menu(message.chat.id))
        else:
            return await message.answer("Пожалуйста, выбери Да или Нет с помощью кнопок.")
    await state.clear()
    await show_admin_menu(message)

def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Актуальные заявки", callback_data="admin_current")],
        [InlineKeyboardButton(text="📜 История (7 дней)", callback_data="admin_history")]
    ])

async def show_admin_menu(message: Message):
    await message.answer("Выбери раздел:", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "admin_current")
async def admin_current(call: CallbackQuery):
    now = datetime.now(NORILSK_TZ).date()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("""
            SELECT o.order_date, u.fio, u.username, o.meals FROM orders o 
            JOIN users u ON o.username = u.username 
            WHERE o.order_date >= ? ORDER BY o.order_date ASC, o.id ASC
        """, (str(now),)) as cursor:
            orders = await cursor.fetchall()
    if not orders: return await call.message.edit_text("Актуальных заявок нет.", reply_markup=get_admin_kb())
    text = "📅 **Актуальные заявки:**\n\n"
    curr_date = None
    for o_date, fio, uname, meals in orders:
        if o_date != curr_date:
            text += f"📌 **{o_date}**\n"
            curr_date = o_date
        text += f"👤 {fio} ({uname}): {meals}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить актуальные", callback_data="confirm_clear_curr")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "admin_history")
async def admin_history(call: CallbackQuery):
    week_ago = datetime.now(NORILSK_TZ).date() - timedelta(days=7)
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("""
            SELECT o.order_date, u.fio, u.username, o.meals FROM orders o 
            JOIN users u ON o.username = u.username 
            WHERE o.order_date >= ? ORDER BY o.order_date DESC, o.id DESC
        """, (str(week_ago),)) as cursor:
            orders = await cursor.fetchall()
    if not orders: return await call.message.edit_text("История пуста.", reply_markup=get_admin_kb())
    text = "📜 **История за 7 дней:**\n\n"
    curr_date = None
    for o_date, fio, uname, meals in orders:
        if o_date != curr_date:
            text += f"📌 **{o_date}**\n"
            curr_date = o_date
        text += f"👤 {fio} ({uname}): {meals}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]])
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "confirm_clear_curr")
async def confirm_clear_curr(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ ДА, ОЧИСТИТЬ", callback_data="do_clear_curr")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_current")]
    ])
    await call.message.edit_text("Вы уверены, что хотите удалить ВСЕ актуальные заявки?", reply_markup=kb)

@dp.callback_query(F.data == "do_clear_curr")
async def do_clear_curr(call: CallbackQuery):
    now = str(datetime.now(NORILSK_TZ).date())
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("DELETE FROM orders WHERE order_date >= ?", (now,))
        await db.commit()
    await call.message.edit_text("🗑 Актуальные заявки удалены.", reply_markup=get_admin_kb())

@dp.callback_query(F.data == "admin_back")
async def admin_back2(call: CallbackQuery):
    await call.message.edit_text("Выбери раздел:", reply_markup=get_admin_kb())

# ==== ЗАКАЗЫ ====
@dp.message(F.text == "🍽 Сделать заказ")
async def new_order(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username FROM users WHERE chat_id = ? AND is_logged_in = 1 AND is_banned = 0", (message.chat.id,)) as cursor:
            if not await cursor.fetchone(): return await message.answer("Сначала войди или ты забанен.")
        async with db.execute("SELECT value FROM settings WHERE key = 'orders_enabled'") as cur: enabled = (await cur.fetchone())[0]
        if enabled == "0": return await message.answer("Прием заказов временно приостановлен.")
        async with db.execute("SELECT value FROM settings WHERE key = 'deadline'") as cur: deadline = (await cur.fetchone())[0]

    now = datetime.now(NORILSK_TZ)
    dl_h, dl_m = map(int, deadline.split(':'))
    can_today = now.hour < dl_h or (now.hour == dl_h and now.minute < dl_m)
    today, tomorrow = now.date(), now.date() + timedelta(days=1)
    kb = []
    if can_today: kb.append([InlineKeyboardButton(text=f"Сегодня ({today.strftime('%d.%m')})", callback_data=f"date_{today}")])
    kb.append([InlineKeyboardButton(text=f"Завтра ({tomorrow.strftime('%d.%m')})", callback_data=f"date_{tomorrow}")])
    kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    await message.answer("На какую дату заказ?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(Order.choosing_date)

@dp.callback_query(F.data.startswith("date_"))
async def order_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split("_", 1)[1]
    order_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if order_date.weekday() > 4: return await call.answer("На выходные не принимаем!", show_alert=True)
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username FROM users WHERE chat_id = ?", (call.message.chat.id,)) as cursor:
            username = (await cursor.fetchone())[0]
        async with db.execute("SELECT id FROM orders WHERE username = ? AND order_date = ?", (username, date_str)) as cursor:
            if await cursor.fetchone(): return await call.answer("Ты уже заказал на эту дату!", show_alert=True)
    await state.update_data(date=date_str, meals=[], weekday=order_date.weekday())
    
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT meal, text FROM menu WHERE day = ?", (str(order_date.weekday()),)) as cursor:
            menu_items = await cursor.fetchall()
    menu_dict = {m: t for m, t in menu_items}
    text = f"📅 **Меню на {date_str}:**\n\n🍳 **Завтрак:** {menu_dict.get('Завтрак', 'Нет')}\n\n🍲 **Обед:** {menu_dict.get('Обед', 'Нет')}\n\n🥐 **Полдник:** {menu_dict.get('Полдник', 'Нет')}\n\nЧто будешь заказывать?"
    await call.message.edit_text(text, reply_markup=get_meal_kb([]), parse_mode="Markdown")
    await state.set_state(Order.choosing_meal)

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_meal(call: CallbackQuery, state: FSMContext):
    meal = call.data.split("_", 1)[1]
    data = await state.get_data()
    selected = data.get("meals", [])
    if meal in selected: selected.remove(meal)
    else: selected.append(meal)
    await state.update_data(meals=selected)
    await call.message.edit_reply_markup(reply_markup=get_meal_kb(selected))
    await call.answer()

@dp.callback_query(F.data == "proceed")
async def proceed(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("meals"): return await call.answer("Выбери блюдо!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")], [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]])
    await call.message.edit_text(f"📝 **Проверь заказ:**\n\n📅 Дата: {data['date']}\n🍽 Блюда: {', '.join(data['meals'])}\n\nВсё верно?", reply_markup=kb, parse_mode="Markdown")
    await state.set_state(Order.confirming)

@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username, fio FROM users WHERE chat_id = ?", (call.message.chat.id,)) as cursor:
            username, fio = await cursor.fetchone()
        meals_text = ", ".join(data['meals'])
        now = datetime.now(NORILSK_TZ).strftime("%Y-%m-%d %H:%M")
        await db.execute("INSERT INTO orders (username, order_date, meals, created_at) VALUES (?, ?, ?, ?)", (username, data['date'], meals_text, now))
        await db.commit()
        async with db.execute("SELECT chat_id FROM users WHERE is_admin = 1") as cursor:
            admins = await cursor.fetchall()
    for (admin_id,) in admins:
        try: await bot.send_message(admin_id, "🔔 **У вас новая заявка!** Проверьте в панели.", parse_mode="Markdown")
        except: pass
    await call.message.edit_text("✅ Заявка отправлена!")
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("❌ Отменено.")
    await state.clear()

@dp.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username FROM users WHERE chat_id = ?", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res: return await message.answer("Войди в аккаунт.")
            username = res[0]
        async with db.execute("SELECT order_date, meals FROM orders WHERE username = ? ORDER BY id DESC LIMIT 10", (username,)) as cursor:
            orders = await cursor.fetchall()
    if not orders: return await message.answer("У тебя нет заказов.")
    text = "📋 **Твои последние заказы:**\n\n" + "\n".join([f"📅 {d}: {m}" for d, m in orders])
    await message.answer(text, parse_mode="Markdown")

# ==== ОБРАБОТЧИК КАСТОМНЫХ КНОПОК (В САМОМ КОНЦЕ) ====
@dp.message(F.text)
async def handle_custom_buttons(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT id, text, photo_id FROM custom_buttons WHERE title = ? AND parent_id = 0", (message.text,)) as cursor:
            btn = await cursor.fetchone()
    if btn:
        btn_id, text, photo_id = btn
        async with aiosqlite.connect("orders.db") as db:
            async with db.execute("SELECT title FROM custom_buttons WHERE parent_id = ?", (btn_id,)) as cursor:
                children = await cursor.fetchall()
        if children:
            kb = [[KeyboardButton(text=c[0])] for c in children]
            kb.append([KeyboardButton(text="🔙 Назад")])
            await message.answer("Выбери раздел:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        elif text:
            if photo_id: await message.answer_photo(photo=photo_id, caption=text)
            else: await message.answer(text)
        else: await message.answer("Эта кнопка пустая.")
        return

async def weekly_cleanup():
    while True:
        now = datetime.now(NORILSK_TZ)
        if now.weekday() == 6 and now.hour == 0 and now.minute < 5:
            async with aiosqlite.connect("orders.db") as db:
                await db.execute("DELETE FROM orders WHERE order_date < ?", (str(now.date()),))
                await db.execute("DELETE FROM duty WHERE date < ?", (str(now.date()),))
                await db.commit()
            await asyncio.sleep(3600)
        await asyncio.sleep(60)

async def main():
    await init_db()
    Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(weekly_cleanup())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                return

async def weekly_cleanup():
    while True:
        now = datetime.now(NORILSK_TZ)
        if now.weekday() == 6 and now.hour == 0 and now.minute < 5:
            async with aiosqlite.connect("orders.db") as db:
                await db.execute("DELETE FROM orders WHERE order_date < ?", (str(now.date()),))
                await db.execute("DELETE FROM duty WHERE date < ?", (str(now.date()),))
                await db.commit()
            await asyncio.sleep(3600)
        await asyncio.sleep(60)

async def main():
    await init_db()
    Thread(target=run_flask, daemon=True).start()
    asyncio.create_task(weekly_cleanup())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
