import asyncio
import os
import aiosqlite
import hashlib
from datetime import datetime, timedelta, timezone
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

LOGINS = [
    "ivanov", "petrov", "sidorov", "kuznetsov", "smirnov",
    "popov", "vasiliev", "sokolov", "mikhailov", "novikov",
    "fedorov", "morozov", "volkov", "alekseev", "lebedev",
    "semenov", "egorov", "pavlov", "kozlov", "stepanov",
    "nikolaev", "orlov", "andreev", "makarov", "nikitin",
    "zakharov", "zaitsev", "soloviev", "borisov", "yakovlev",
]

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
    waiting_login = State()
    waiting_fio = State()
    waiting_password = State()
    waiting_secret = State()

class Auth(StatesGroup):
    waiting_login = State()
    waiting_password = State()

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
                login TEXT PRIMARY KEY, fio TEXT, password TEXT, chat_id INTEGER, is_logged_in INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, order_date TEXT, meals TEXT, created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS used_codes (
                code TEXT PRIMARY KEY
            )
        """)
        await db.commit()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def get_main_menu(is_admin=False):
    kb = [
        [KeyboardButton(text="🍽 Сделать заказ"), KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🚪 Выйти")]
    ]
    if is_admin:
        kb.insert(1, [KeyboardButton(text="📥 Панель ответственного")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_auth_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔑 Войти"), KeyboardButton(text="📝 Регистрация"), KeyboardButton(text="🛡 Я ответственный")]],
        resize_keyboard=True
    )

def get_meal_kb(selected):
    kb = []
    for meal in ["Завтрак", "Обед", "Полдник"]:
        text = f"✅ {meal}" if meal in selected else f"⬜ {meal}"
        kb.append([InlineKeyboardButton(text=text, callback_data=f"toggle_{meal}")])
    if selected: kb.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="proceed")])
    kb.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_logged_in, is_admin FROM users WHERE chat_id = ?", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if res and res[0] == 1:
                await message.answer("Ты уже в системе.", reply_markup=get_main_menu(is_admin=bool(res[1])))
                return
    await message.answer("Привет! Выбери действие:", reply_markup=get_auth_menu())

# ==== РЕГИСТРАЦИЯ ====
@dp.message(F.text == "📝 Регистрация")
async def reg_start(message: Message, state: FSMContext):
    await message.answer("Введи свой логин (фамилию латиницей):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True))
    await state.set_state(Reg.waiting_login)

@dp.message(F.text == "🛡 Я ответственный")
async def reg_admin_start(message: Message, state: FSMContext):
    await message.answer("Введи свой логин:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True))
    await state.set_state(Reg.waiting_login)
    await state.update_data(is_admin=True)

@dp.message(Reg.waiting_login)
async def reg_login(message: Message, state: FSMContext):
    if message.text == "Отмена": return await start(message, state)
    login = message.text.strip().lower()
    if login not in LOGINS:
        return await message.answer("Такого логина нет в списке. Попробуй другой:")
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT login FROM users WHERE login = ?", (login,)) as cursor:
            if await cursor.fetchone():
                return await message.answer("Этот логин уже занят! Нажми 'Войти'.")
    await state.update_data(login=login)
    await message.answer("Введи свои ФИО (например: ИВАНОВ ИВАН ИВАНОВИЧ):")
    await state.set_state(Reg.waiting_fio)

@dp.message(Reg.waiting_fio)
async def reg_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text.strip().upper())
    await message.answer("Придумай пароль:")
    await state.set_state(Reg.waiting_password)

@dp.message(Reg.waiting_password)
async def reg_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    if len(pwd) < 3: return await message.answer("Пароль слишком короткий!")
    await state.update_data(password=hash_password(pwd))
    
    data = await state.get_data()
    if data.get("is_admin"):
        await message.answer("Введи секретный код ответственного:")
        await state.set_state(Reg.waiting_secret)
    else:
        await save_user(message, data, is_admin=False)

@dp.message(Reg.waiting_secret)
async def reg_secret(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with aiosqlite.connect("orders.db") as db:
        if code not in SECRET_CODES:
            return await message.answer("Неверный код! Попробуй снова:")
        async with db.execute("SELECT code FROM used_codes WHERE code = ?", (code,)) as cursor:
            if await cursor.fetchone():
                return await message.answer("Этот код уже использован кем-то! Введи другой:")
        await db.execute("INSERT INTO used_codes (code) VALUES (?)", (code,))
        await db.commit()
    
    data = await state.get_data()
    await save_user(message, data, is_admin=True)

async def save_user(message: Message, data: dict, is_admin: bool):
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("INSERT INTO users (login, fio, password, chat_id, is_logged_in, is_admin) VALUES (?, ?, ?, ?, 1, ?)",
                         (data['login'], data['fio'], data['password'], message.chat.id, int(is_admin)))
        await db.commit()
    role = "ОТВЕТСТВЕННОГО" if is_admin else "УЧЕНИКА"
    await message.answer(f"Успешная регистрация {role}!\nФИО: {data['fio']}", reply_markup=get_main_menu(is_admin=is_admin))

# ==== ВХОД ====
@dp.message(F.text == "🔑 Войти")
async def auth_start(message: Message, state: FSMContext):
    await message.answer("Введи свой логин:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отмена")]], resize_keyboard=True))
    await state.set_state(Auth.waiting_login)

@dp.message(Auth.waiting_login)
async def auth_login(message: Message, state: FSMContext):
    if message.text == "Отмена": return await start(message, state)
    login = message.text.strip().lower()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_logged_in FROM users WHERE login = ?", (login,)) as cursor:
            res = await cursor.fetchone()
            if not res: return await message.answer("Логин не найден. Зарегистрируйся.")
            if res[0] == 1: return await message.answer("Аккаунт уже в сети с другого устройства!")
    await state.update_data(login=login)
    await message.answer("Введи пароль:")
    await state.set_state(Auth.waiting_password)

@dp.message(Auth.waiting_password)
async def auth_pass(message: Message, state: FSMContext):
    pwd = message.text.strip()
    data = await state.get_data()
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT password, is_admin FROM users WHERE login = ?", (data['login'],)) as cursor:
            res = await cursor.fetchone()
            if res and res[0] == hash_password(pwd):
                await db.execute("UPDATE users SET chat_id = ?, is_logged_in = 1 WHERE login = ?", (message.chat.id, data['login']))
                await db.commit()
                await message.answer("Успешный вход!", reply_markup=get_main_menu(is_admin=bool(res[1])))
                await state.clear()
            else:
                await message.answer("Неверный пароль!")

@dp.message(F.text == "🚪 Выйти")
async def logout(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        await db.execute("UPDATE users SET is_logged_in = 0 WHERE chat_id = ?", (message.chat.id,))
        await db.commit()
    await message.answer("Вы вышли из аккаунта.", reply_markup=get_auth_menu())
    await state.clear()

# ==== ПРОФИЛЬ ====
@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT login, fio FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            user = await cursor.fetchone()
            if not user: return await message.answer("Войди в аккаунт.")
            login, fio = user
            async with db.execute("SELECT meals FROM orders WHERE login = ?", (login,)) as cursor:
                orders = await cursor.fetchall()
    b, l, p = 0, 0, 0
    for (meals,) in orders:
        if "Завтрак" in meals: b += 1
        if "Обед" in meals: l += 1
        if "Полдник" in meals: p += 1
    total = b + l + p
    rank_idx = min(total // 3, len(RANKS) - 1)
    text = (f"👤 **Профиль**\n\n📛 ФИО: {fio}\n🔑 Логин: {login}\n\n"
            f"🍳 Завтраков: {b}\n🍲 Обедов: {l}\n🥐 Полдников: {p}\n\n"
            f"🏅 Твое звание: **{RANKS[rank_idx]}**")
    await message.answer(text, parse_mode="Markdown")

# ==== ПАНЕЛЬ ОТВЕТСТВЕННОГО ====
@dp.message(F.text == "📥 Панель ответственного")
async def admin_panel(message: Message):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res or res[0] == 0: return await message.answer("У тебя нет прав.")
            
        async with db.execute("""
            SELECT o.order_date, u.fio, o.meals 
            FROM orders o JOIN users u ON o.login = u.login 
            ORDER BY o.order_date ASC, o.id ASC
        """) as cursor:
            orders = await cursor.fetchall()
            
    if not orders:
        return await message.answer("Заявок пока нет.")
        
    text = "📥 **Все заявки на питание:**\n\n"
    current_date = None
    for o_date, fio, meals in orders:
        if o_date != current_date:
            text += f"📅 **{o_date}**\n"
            current_date = o_date
        text += f"👤 {fio}: {meals}\n"
    text += "\n*(Нажми на кнопку ниже, чтобы удалить все старые заявки)*"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑 Очистить все заявки", callback_data="clear_orders")]])
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data == "clear_orders")
async def clear_orders(call: CallbackQuery):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT is_admin FROM users WHERE chat_id = ?", (call.message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res or res[0] == 0: return await call.answer("Нет прав!")
        await db.execute("DELETE FROM orders")
        await db.commit()
    await call.message.edit_text("🗑 Все заявки удалены!")
    await call.answer()

# ==== ЗАКАЗ ЕДЫ ====
@dp.message(F.text == "🍽 Сделать заказ")
async def new_order(message: Message, state: FSMContext):
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT login FROM users WHERE chat_id = ? AND is_logged_in = 1", (message.chat.id,)) as cursor:
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
    if order_date.weekday() > 4: return await call.answer("На выходные заказы не принимаются!", show_alert=True)
    async with aiosqlite.connect("orders.db") as db:
        async with db.execute("SELECT login FROM users WHERE chat_id = ?", (call.message.chat.id,)) as cursor:
            login = (await cursor.fetchone())[0]
        async with db.execute("SELECT id FROM orders WHERE login = ? AND order_date = ?", (login, date_str)) as cursor:
            if await cursor.fetchone(): return await call.answer("Ты уже сделал заказ на эту дату!", show_alert=True)
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
        async with db.execute("SELECT login, fio FROM users WHERE chat_id = ?", (call.message.chat.id,)) as cursor:
            login, fio = await cursor.fetchone()
        meals_text = ", ".join(data['meals'])
        now = datetime.now(NORILSK_TZ).strftime("%Y-%m-%d %H:%M")
        await db.execute("INSERT INTO orders (login, order_date, meals, created_at) VALUES (?, ?, ?, ?)", (login, data['date'], meals_text, now))
        await db.commit()
        
        # Рассылка всем ответственным
        async with db.execute("SELECT chat_id FROM users WHERE is_admin = 1") as cursor:
            admins = await cursor.fetchall()
            
    for (admin_id,) in admins:
        try:
            await bot.send_message(admin_id, "🔔 **У вас новая заявка!** Проверьте в кнопке «Панель ответственного».", parse_mode="Markdown")
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
        async with db.execute("SELECT login FROM users WHERE chat_id = ?", (message.chat.id,)) as cursor:
            res = await cursor.fetchone()
            if not res: return await message.answer("Войди в аккаунт.")
            login = res[0]
        async with db.execute("SELECT order_date, meals FROM orders WHERE login = ? ORDER BY id DESC LIMIT 10", (login,)) as cursor:
            orders = await cursor.fetchall()
    if not orders: return await message.answer("У тебя нет заказов.")
    text = "📋 **Твои последние заказы:**\n\n" + "\n".join([f"📅 {d}: {m}" for d, m in orders])
    await message.answer(text, parse_mode="Markdown")

async def main():
    await init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
