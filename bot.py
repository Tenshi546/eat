import asyncio
import os
import aiosqlite
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
ADMIN_IDS = [5486573835]
NORILSK_TZ = timezone(timedelta(hours=7))

LOGINS = [
    "ivanov", "petrov", "sidorov", "kuznetsov", "smirnov",
    "popov", "vasiliev", "sokolov", "mikhailov", "novikov",
    "fedorov", "morozov", "volkov", "alekseev", "lebedev",
    "semenov", "egorov", "pavlov", "kozlov", "stepanov",
    "nikolaev", "orlov", "andreev", "makarov", "nikitin",
    "zakharov", "zaitsev", "soloviev", "borisov", "yakovlev",
]

# Меню по дням недели (0 - Понедельник, 1 - Вторник и т.д.)
# В четверг и пятницу повторяются блюда из Пн и Вт.
MENU_DATA = {
    0: { # Понедельник
        "Завтрак": "Каша молочная, сыр, чай, хлеб",
        "Обед": "Салат, борщ, говядина, тефтели, гречка, компот",
        "Полдник": "Печенье, компот, чай"
    },
    1: { # Вторник
        "Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин",
        "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот",
        "Полдник": "Булочка, кофейный напиток"
    },
    2: { # Среда
        "Завтрак": "Фрикадельки, овощи, чай с лимоном, пюре фруктовое",
        "Обед": "Салат из свеклы, суп крестьянский, говядина, рыба запеченная, компот",
        "Полдник": "Пирожки, молоко"
    },
    3: { # Четверг (повтор Понедельника)
        "Завтрак": "Каша молочная, сыр, чай, хлеб",
        "Обед": "Салат, борщ, говядина, тефтели, гречка, компот",
        "Полдник": "Печенье, компот, чай"
    },
    4: { # Пятница (повтор Вторника)
        "Завтрак": "Горошек, тефтели рыбные, пюре, чай, апельсин",
        "Обед": "Салат морковный, рассольник, птица отварная и жареная, макароны, компот",
        "Полдник": "Булочка, кофейный напиток"
    }
}

users = {}

class Order(StatesGroup):
    waiting_login = State()
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
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER,
                login TEXT, order_date TEXT, meals TEXT, created_at TEXT
            )
        """)
        await db.commit()

async def save_order(chat_id, login, order_date, meals):
    async with aiosqlite.connect("orders.db") as db:
        now = datetime.now(NORILSK_TZ).strftime("%Y-%m-%d %H:%M")
        await db.execute(
            "INSERT INTO orders (chat_id, login, order_date, meals, created_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, login, order_date, meals, now)
        )
        await db.commit()

async def get_user_orders(chat_id):
    async with aiosqlite.connect("orders.db") as db:
        cursor = await db.execute(
            "SELECT order_date, meals FROM orders WHERE chat_id = ? ORDER BY id DESC LIMIT 10",
            (chat_id,)
        )
        return await cursor.fetchall()

def get_main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🍽 Сделать заказ")], [KeyboardButton(text="📋 Мои заказы")]],
        resize_keyboard=True
    )

def get_meal_keyboard(selected_meals: list):
    meals = ["Завтрак", "Обед", "Полдник"]
    keyboard = []
    for meal in meals:
        text = f"✅ {meal}" if meal in selected_meals else f"⬜ {meal}"
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"toggle_{meal}")])
    if selected_meals:
        keyboard.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="proceed")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if message.chat.id in users:
        await message.answer(f"С возвращением, {users[message.chat.id]}!", reply_markup=get_main_reply_keyboard())
        await state.clear()
    else:
        await message.answer("Привет! Введи свой логин:")
        await state.set_state(Order.waiting_login)

@dp.message(Order.waiting_login)
async def check_login(message: Message, state: FSMContext):
    login = message.text.strip().lower()
    if login in LOGINS:
        users[message.chat.id] = login
        await message.answer(f"Отлично, {login}!", reply_markup=get_main_reply_keyboard())
        await state.clear()
    else:
        await message.answer("Логин не найден. Попробуй снова:")

@dp.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    if message.chat.id not in users:
        await message.answer("Сначала авторизуйся через /start")
        return
    orders = await get_user_orders(message.chat.id)
    if not orders:
        await message.answer("У тебя пока нет заказов.")
        return
    text = "📋 **Твои последние заказы:**\n\n"
    for o_date, meals in orders:
        text += f"📅 {o_date}: {meals}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🍽 Сделать заказ")
async def new_order_msg(message: Message, state: FSMContext):
    if message.chat.id not in users:
        await message.answer("Сначала авторизуйся через /start")
        return

    now = datetime.now(NORILSK_TZ)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    
    can_order_today = now.hour < 8 or (now.hour == 8 and now.minute < 30)
    
    kb_buttons = []
    if can_order_today:
        kb_buttons.append([InlineKeyboardButton(text=f"Сегодня ({today.strftime('%d.%m')})", callback_data=f"date_{today}")])
    
    kb_buttons.append([InlineKeyboardButton(text=f"Завтра ({tomorrow.strftime('%d.%m')})", callback_data=f"date_{tomorrow}")])
    kb_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    
    await message.answer("На какую дату заказ?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))
    await state.set_state(Order.choosing_date)

@dp.callback_query(F.data.startswith("date_"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split("_", 1)[1]
    order_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = order_date.weekday()
    
    if weekday > 4: # 5 - Сб, 6 - Вс
        await call.answer("На выходные заказы не принимаются (нет учебы)!", show_alert=True)
        return

    await state.update_data(date=date_str, selected_meals=[], weekday=weekday)
    menu = MENU_DATA[weekday]
    
    menu_text = (
        f"📅 **Меню на {date_str}:**\n\n"
        f"🍳 **Завтрак:** {menu['Завтрак']}\n\n"
        f"🍲 **Обед:** {menu['Обед']}\n\n"
        f"🥐 **Полдник:** {menu['Полдник']}\n\n"
        f"Что будешь заказывать?"
    )
    await call.message.edit_text(menu_text, reply_markup=get_meal_keyboard([]), parse_mode="Markdown")
    await state.set_state(Order.choosing_meal)

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_meal(call: CallbackQuery, state: FSMContext):
    meal = call.data.split("_", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_meals", [])
    
    if meal in selected: selected.remove(meal)
    else: selected.append(meal)
        
    await state.update_data(selected_meals=selected)
    await call.message.edit_reply_markup(reply_markup=get_meal_keyboard(selected))
    await call.answer()

@dp.callback_query(F.data == "proceed")
async def proceed_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_meals", [])
    
    if not selected:
        await call.answer("Выбери хотя бы одно блюдо!", show_alert=True)
        return

    meals_text = ", ".join(selected)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ])
    await call.message.edit_text(
        f"📝 **Проверь заказ:**\n\n📅 Дата: {data['date']}\n🍽 Блюда: {meals_text}\n\nВсё верно?",
        reply_markup=kb, parse_mode="Markdown"
    )
    await state.set_state(Order.confirming)

@dp.callback_query(F.data == "confirm")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    login = users.get(call.message.chat.id, "неизвестно")
    meals_text = ", ".join(data.get("selected_meals", []))
    
    await save_order(call.message.chat.id, login, data['date'], meals_text)
    
    text = f"🔔 **Новая заявка!**\n\n👤 Ученик: `{login}`\n📅 Дата: {data['date']}\n🍽 Заказ: {meals_text}"
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception: pass
            
    await call.message.edit_text("✅ Заявка отправлена! Посмотреть её можно в кнопке «Мои заказы».")
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("❌ Отменено.")
    await state.clear()

async def main():
    await init_db()
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
