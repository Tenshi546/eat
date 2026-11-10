import asyncio
import os
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==== НАСТРОЙКИ ====
BOT_TOKEN = "9259003904:AAGO259i8dQHPKln3PQbzDaj0iwkTAHTdt4"
ADMIN_IDS = [5486573835]

LOGINS = [
    "ivanov", "petrov", "sidorov", "kuznetsov", "smirnov",
    "popov", "vasiliev", "sokolov", "mikhailov", "novikov",
    "fedorov", "morozov", "volkov", "alekseev", "lebedev",
    "semenov", "egorov", "pavlov", "kozlov", "stepanov",
    "nikolaev", "orlov", "andreev", "makarov", "nikitin",
    "zakharov", "zaitsev", "soloviev", "borisov", "yakovlev",
]

users = {} 

class Order(StatesGroup):
    waiting_login = State()
    choosing_date = State()
    choosing_meal = State()
    confirming = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==== ВЕБ-СЕРВЕР ДЛЯ RENDER ====
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==== ЛОГИКА БОТА ====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Сделать заказ", callback_data="new_order")]
    ])

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    chat_id = message.chat.id
    if chat_id in users:
        await message.answer(f"Ты уже вошёл как {users[chat_id]}.", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("Привет! Введи свой логин (фамилию латиницей, например ivanov):")
        await state.set_state(Order.waiting_login)

@dp.message(Order.waiting_login)
async def check_login(message: Message, state: FSMContext):
    login = message.text.strip().lower()
    if login in LOGINS:
        users[message.chat.id] = login
        await message.answer(f"Отлично, {login}! Можешь заказывать еду.", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("Такого логина нет. Проверь и введи снова:")

@dp.callback_query(F.data == "new_order")
async def new_order(call: CallbackQuery, state: FSMContext):
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Сегодня ({today.strftime('%d.%m')})", callback_data=f"date_{today}")],
        [InlineKeyboardButton(text=f"Завтра ({tomorrow.strftime('%d.%m')})", callback_data=f"date_{tomorrow}")],
    ])
    await call.message.edit_text("На какую дату заказ?", reply_markup=kb)
    await state.set_state(Order.choosing_date)

@dp.callback_query(F.data.startswith("date_"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split("_", 1)[1]
    await state.update_data(date=date_str)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завтрак", callback_data="meal_Завтрак")],
        [InlineKeyboardButton(text="Обед", callback_data="meal_Обед")],
        [InlineKeyboardButton(text="Полдник", callback_data="meal_Полдник")],
        [InlineKeyboardButton(text="Всё сразу", callback_data="meal_Всё сразу")],
    ])
    await call.message.edit_text("Что будешь кушать?", reply_markup=kb)
    await state.set_state(Order.choosing_meal)

@dp.callback_query(F.data.startswith("meal_"))
async def choose_meal(call: CallbackQuery, state: FSMContext):
    meal = call.data.split("_", 1)[1]
    await state.update_data(meal=meal)
    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])
    await call.message.edit_text(
        f"Проверь заказ:\nДата: {data['date']}\nПриём пищи: {meal}\n\nПодтверждаем?",
        reply_markup=kb
    )
    await state.set_state(Order.confirming)

@dp.callback_query(F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    login = users.get(call.message.chat.id, "неизвестно")
    text = f"🍽 Новая заявка\nУченик: {login}\nДата: {data['date']}\nЗаказ: {data['meal']}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Не смог отправить {admin_id}: {e}")
    await call.message.edit_text("Заявка отправлена ответственным ✅")
    await state.clear()

@dp.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Отменено.")
    await state.clear()

async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())