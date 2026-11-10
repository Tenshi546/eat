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

# Список логинов (потом заменишь на свои)
LOGINS = [
    "ivanov", "petrov", "sidorov", "kuznetsov", "smirnov",
    "popov", "vasiliev", "sokolov", "mikhailov", "novikov",
    "fedorov", "morozov", "volkov", "alekseev", "lebedev",
    "semenov", "egorov", "pavlov", "kozlov", "stepanov",
    "nikolaev", "orlov", "andreev", "makarov", "nikitin",
    "zakharov", "zaitsev", "soloviev", "borisov", "yakovlev",
]

users = {} # chat_id -> логин

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

# ==== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====
def get_meal_keyboard(selected_meals: list):
    """Генерирует клавиатуру с галочками в зависимости от выбора"""
    meals = ["Завтрак", "Обед", "Полдник"]
    keyboard = []
    
    # Создаем кнопки с галочками
    for meal in meals:
        if meal in selected_meals:
            text = f"✅ {meal}"
        else:
            text = f"⬜ {meal}"
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"toggle_{meal}")])
    
    # Добавляем кнопку "Продолжить", только если что-то выбрано
    if selected_meals:
        keyboard.append([InlineKeyboardButton(text="➡️ Продолжить", callback_data="proceed")])
        
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==== ЛОГИКА БОТА ====
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    chat_id = message.chat.id
    if chat_id in users:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍽 Сделать заказ", callback_data="new_order")]
        ])
        await message.answer(f"С возвращением, {users[chat_id]}! Готов сделать заказ?", reply_markup=kb)
        await state.clear()
    else:
        await message.answer("Привет! Введи свой логин (фамилию латиницей, например ivanov):")
        await state.set_state(Order.waiting_login)

@dp.message(Order.waiting_login)
async def check_login(message: Message, state: FSMContext):
    login = message.text.strip().lower()
    if login in LOGINS:
        users[message.chat.id] = login
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍽 Сделать заказ", callback_data="new_order")]
        ])
        await message.answer(f"Отлично, {login}! Можешь заказывать еду.", reply_markup=kb)
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
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ])
    await call.message.edit_text("На какую дату заказ?", reply_markup=kb)
    await state.set_state(Order.choosing_date)

@dp.callback_query(F.data.startswith("date_"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split("_", 1)[1]
    await state.update_data(date=date_str, selected_meals=[])
    
    kb = get_meal_keyboard([])
    await call.message.edit_text("Что будешь кушать? (Нажимай на блюда, чтобы выбрать)\nПосле выбора нажми «Продолжить».", reply_markup=kb)
    await state.set_state(Order.choosing_meal)

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_meal(call: CallbackQuery, state: FSMContext):
    meal = call.data.split("_", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_meals", [])
    
    # Добавляем или убираем из списка
    if meal in selected:
        selected.remove(meal)
    else:
        selected.append(meal)
        
    await state.update_data(selected_meals=selected)
    
    # Обновляем клавиатуру
    kb = get_meal_keyboard(selected)
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()

@dp.callback_query(F.data == "proceed")
async def proceed_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_meals", [])
    
    # Двойная защита: если список пуст, ничего не делаем
    if not selected:
        await call.answer("Сначала выбери хотя бы одно блюдо!", show_alert=True)
        return

    meals_text = ", ".join(selected)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
    ])
    
    await call.message.edit_text(
        f"📝 **Проверь заказ:**\n\n"
        f"📅 Дата: {data['date']}\n"
        f"🍽 Приёмы пищи: {meals_text}\n\n"
        f"Всё верно?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(Order.confirming)

@dp.callback_query(F.data == "confirm")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    login = users.get(call.message.chat.id, "неизвестно")
    selected = data.get("selected_meals", [])
    meals_text = ", ".join(selected)
    
    text = (
        f"🔔 **Новая заявка!**\n\n"
        f"👤 Ученик: `{login}`\n"
        f"📅 Дата: {data['date']}\n"
        f"🍽 Заказ: {meals_text}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка отправки {admin_id}: {e}")
            
    await call.message.edit_text("✅ Заявка успешно отправлена ответственным!")
    await state.clear()

@dp.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("❌ Заказ отменён. Возвращайся, когда захочешь поесть!")
    await state.clear()

async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
