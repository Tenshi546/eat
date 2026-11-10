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
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==== НАСТРОЙКИ ====
BOT_TOKEN = "9259003904:AAGO259i8dQHPKln3PQbzDaj0iwkTAHTdt4"
NORILSK_TZ = timezone(timedelta(hours=7))
SECRET_CODES = ["ADMIN77", "BOSS999", "CHEF555", "GURU123"]

# Официальный список учеников (Фамилия Имя Отчество)
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

# Создаем базу "правильных" имен и фамилий для быстрой проверки
# Берем только первое и второе слово (Фамилия и Имя)
VALID_NAMES = set()
for student in STUDENTS:
    parts = student.split()
    if len(parts) >= 2:
        VALID_NAMES.add((parts[0].lower(), parts[1].lower()))

MENU_DATA = {
    0: {"Завтрак": "Каша молочная, сыр, чай, хлеб", "Обед": "Салат, борщ, говядина, тефтели, гречка, компот", "Полдник": "Печенье, компот, чай"},
    1: {"Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин", "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот", "Полдник": "Булочка, кофейный напиток"},
    2: {"Завтрак": "Фрикадельки, овощи, чай с лимоном, пюре фруктовое", "Обед": "Салат из свеклы, суп крестьянский, говядина, рыба запеченная, компот", "Полдник": "Пирожки, молоко"},
    3: {"Завтрак": "Каша молочная, сыр, чай, хлеб", "Обед": "Салат, борщ, говядина, тефтели, гречка, компот", "Полдник": "Печенье, компот, чай"},
    4: {"Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин", "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот", "Полдник": "Булочка, кофейный напиток"}
}

RANKS = [
    "🦗 Голодный кузнечик", "🦴 Скелетон", "🍞 Крошка хлеба", "🥚 Яйцо всмятку",
    "🍗 Цыпленок табака", "🍟 Любитель картошки", "🌭 Хот-дог критик", "🍔 Бургер-стажер",
    "🥪 Сэндвич-мастер", "🍕 Пицца-пацан", "🌮 Такос-воин", "🍣 Суши-ниндзя",
    "🍜 Рамен-сенсей", "🥩 Стейк-самурай", "🍖 Мясной магнат", "👑 Куриный король",
    "🔥 Повелитель гриля", "🍗 Генерал Гриль", "🌟 Легенда KFC", "👑 KFC BOSS"
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
                is_admin INTEGER DEFAULT 0, recovery_code TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, order_date TEXT, meals TEXT, created_at TEXT
            )
        """)
        await db.execute("CREATE TABLE IF NOT EXISTS used_codes (username TEXT, code TEXT)")
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

def get_main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🍽 Сделать заказ"), KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🚪 Выйти")]
    ]
    if is_admin:
        kb.insert(1, [KeyboardButton(text="📥 Панель ответственного")])
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

# ==== ОБРАБОТКА НАЗАД ====
@dp.message(F.text == "🔙 Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_logged_in, is_admin FROM users WHERE username = ?", (f"@{message.from_user.username}",)) as cursor:
            res = await cursor.fetchone()
            if res and res[0] == 1:
                return await message.answer("Главное меню:", reply_markup=get_main_menu(is_admin=bool(res[1])))
    await message.answer("Привет! Выбери действие:", reply_markup=get_start_kb())

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_logged_in, is_admin FROM users WHERE username = ?", (f"@{message.from_user.username}",)) as cursor:
            res = await cursor.fetchone()
            if res and res[0] == 1:
                return await message.answer("Ты уже в системе.", reply_markup=get_main_menu(is_admin=bool(res[1])))
    await message.answer("Привет! Выбери действие:", reply_markup=get_start_kb())

# ==== РЕГИСТРАЦИЯ ====
@dp.callback_query(F.data == "reg_start")
async def reg_start(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    if not username: return await call.message.answer("Ошибка: У тебя не установлен юзернейм!")
    await state.update_data(username=f"@{username}", is_admin=False)
    await call.message.edit_text("Введи свои ФИО русскими буквами (Фамилия Имя):", reply_markup=get_cancel_kb())
    await state.set_state(Reg.waiting_fio)

@dp.callback_query(F.data == "reg_admin")
async def reg_admin_start(call: CallbackQuery, state: FSMContext):
    username = call.from_user.username
    if not username: return await call.message.answer("Ошибка: У тебя не установлен юзернейм!")
    await state.update_data(username=f"@{username}", is_admin=True)
    await call.message.edit_text("Введи свои ФИО русскими буквами (Фамилия Имя):", reply_markup=get_cancel_kb())
    await state.set_state(Reg.waiting_fio)

@dp.message(Reg.waiting_fio)
async def reg_fio(message: Message, state: FSMContext):
    text = message.text.strip()
    parts = text.split()
    
    # Проверка ФИО
    if len(parts) < 2:
        return await message.answer("Ошибка! Введи хотя бы Фамилию и Имя. Попробуй еще раз:")
    
    fam, name = parts[0].lower(), parts[1].lower()
    if (fam, name) not in VALID_NAMES:
        return await message.answer("Ошибка! Такого ученика нет в списке (или есть опечатка). Проверь Фамилию и Имя и напиши снова:")

    await state.update_data(fio=text.upper())
    await message.answer("Придумай пароль:")
    await state.set_state(Reg.waiting_password)

@dp.message(Reg.waiting_password)
async def reg_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    if len(pwd) < 3: return await message.answer("Слишком короткий пароль!")
    await state.update_data(password=hash_password(pwd))
    data = await state.get_data()
    if data.get("is_admin"):
        await message.answer("Введи секретный код ответственного:")
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
    await message.answer(f"✅ Успешная регистрация {role}!\nФИО: {data['fio']}\n\n⚠️ **Код восстановления:** `{rec_code}`", reply_markup=get_main_menu(is_admin=is_admin), parse_mode="Markdown")
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
                await message.answer("Успешный вход!", reply_markup=get_main_menu(is_admin=bool(res[1])))
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
    await message.answer("Код верный! Придумай новый пароль:")
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

@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username, fio FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return await message.answer("Войди в аккаунт.")
            username, fio = user
            async with db.execute("SELECT meals FROM orders WHERE username = ?", (username,)) as cursor:
                orders = await cursor.fetchall()
    b, l, p = 0, 0, 0
    for (meals,) in orders:
        if "Завтрак" in meals: b += 1
        if "Обед" in meals: l += 1
        if "Полдник" in meals: p += 1
    total = b + l + p
    rank_idx = min(total // 3, len(RANKS) - 1)
    text = f"👤 **Профиль**\n\n📛 ФИО: {fio}\n🔗 {username}\n\n🍳 Завтраков: {b}\n🍲 Обедов: {l}\n🥐 Полдников: {p}\n\n🏅 Звание: **{RANKS[rank_idx]}**"
    await message.answer(text, parse_mode="Markdown")

# ==== ПАНЕЛЬ ОТВЕТСТВЕННОГО ====
def get_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Актуальные заявки", callback_data="admin_current")],
        [InlineKeyboardButton(text="📜 История (7 дней)", callback_data="admin_history")]
    ])

@dp.message(F.text == "📥 Панель ответственного")
async def admin_panel(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res or res[0] == 0: return await message.answer("Нет прав.")
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
async def admin_back(call: CallbackQuery):
    await call.message.edit_text("Выбери раздел:", reply_markup=get_admin_kb())

# ==== ЗАКАЗ ЕДЫ ====
@dp.message(F.text == "🍽 Сделать заказ")
async def new_order(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT username FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            if not await cursor.fetchone(): return await message.answer("Сначала войди.")
    now = datetime.now(NORILSK_TZ)
    today, tomorrow = now.date(), now.date() + timedelta(days=1)
    can_today = now.hour < 8 or (now.hour == 8 and now.minute < 30)
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
    menu = MENU_DATA[order_date.weekday()]
    text = f"📅 **Меню на {date_str}:**\n\n🍳 **Завтрак:** {menu['Завтрак']}\n\n🍲 **Обед:** {menu['Обед']}\n\n🥐 **Полдник:** {menu['Полдник']}\n\nЧто будешь заказывать?"
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

# ==== ФОНОВАЯ ОЧИСТКА ====
async def weekly_cleanup():
    while True:
        now = datetime.now(NORILSK_TZ)
        if now.weekday() == 6 and now.hour == 0 and now.minute < 5:
            async with aiosqlite.connect("orders.db") as db:
                await db.execute("DELETE FROM orders WHERE order_date < ?", (str(now.date()),))
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
