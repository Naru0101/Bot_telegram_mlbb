import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message, CallbackQuery
)
from liqpay import LiqPay
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import uvicorn
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Логирование ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен и ключи из .env файла
TOKEN = os.getenv("TOKEN")
LIQPAY_PUBLIC_KEY = os.getenv("LIQPAY_PUBLIC_KEY")
LIQPAY_PRIVATE_KEY = os.getenv("LIQPAY_PRIVATE_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# FastAPI приложение
app = FastAPI()

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[  
        [KeyboardButton(text="📈 Заказать буст"), KeyboardButton(text="ℹ️ Помощь")],
        [KeyboardButton(text="Мой заказ")]
    ],
    resize_keyboard=True
)

# Услуги буста
boost_menu = InlineKeyboardMarkup(
    inline_keyboard=[  
        [InlineKeyboardButton(text="Ранги MLBB", callback_data="boost_rank")],
        [InlineKeyboardButton(text="MMR Mobile Legends", callback_data="boost_mmr")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")]
    ]
)

# Меню рангов с ценами
rank_prices = {
    "rank_warrior": 50,
    "rank_elite": 100,
    "rank_master": 150,
    "rank_grandmaster": 200,
    "rank_epic": 300,
    "rank_legend": 400,
    "rank_mythic": 500
}

rank_menu = InlineKeyboardMarkup(
    inline_keyboard=[  
        [InlineKeyboardButton(text=f"Воин (50 грн)", callback_data="rank_warrior"),
         InlineKeyboardButton(text=f"Элитный (100 грн)", callback_data="rank_elite")],
        [InlineKeyboardButton(text=f"Мастер (150 грн)", callback_data="rank_master"),
         InlineKeyboardButton(text=f"Грандмастер (200 грн)", callback_data="rank_grandmaster")],
        [InlineKeyboardButton(text=f"Эпик (300 грн)", callback_data="rank_epic"),
         InlineKeyboardButton(text=f"Легенда (400 грн)", callback_data="rank_legend")],
        [InlineKeyboardButton(text=f"Мифик (500 грн)", callback_data="rank_mythic")],
        [InlineKeyboardButton(text="Назад", callback_data="back_boost")]
    ]
)

# Команда /start
@dp.message(Command(commands=["start"]))
async def start(message: Message):
    try:
        await message.answer(
            f"Привет, {message.from_user.first_name}! 👋\nДобро пожаловать в наш бот по покупке буста!\nВыберите нужный раздел:",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"Error while handling /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте снова позже.")

# Ответ на кнопки главного меню
@dp.message(lambda msg: msg.text == "📈 Заказать буст")
async def order_boost(message: Message):
    await message.answer("Выберите услугу:", reply_markup=boost_menu)

@dp.message(lambda msg: msg.text == "ℹ️ Помощь")
async def help_info(message: Message):
    await message.answer("Напишите нам в поддержку: @ZeRunart_1")

@dp.message(lambda msg: msg.text == "Мой заказ")
async def user_order_status(message: Message):
    await message.answer("Ваш текущий заказ пока не найден. Оформите новый заказ через меню!")

# Обработка кнопок услуг
@dp.callback_query(lambda c: c.data in ["boost_rank", "boost_mmr", "back_main"])
async def process_boost_menu(callback_query: CallbackQuery):
    if callback_query.data == "boost_rank":
        await callback_query.message.edit_text("Выберите ранг для буста:", reply_markup=rank_menu)
    elif callback_query.data == "boost_mmr":
        await callback_query.message.edit_text(
            "Вы выбрали буст MMR в Mobile Legends. Укажите ваш текущий MMR и желаемый MMR.",
        )
    elif callback_query.data == "back_main":
        await callback_query.message.edit_text("Выберите нужный раздел:", reply_markup=main_menu)

# Обработка кнопок рангов
@dp.callback_query(lambda c: c.data.startswith("rank_"))
async def process_rank_selection(callback_query: CallbackQuery):
    rank_key = callback_query.data
    price = rank_prices.get(rank_key, 0)
    rank_name = {
        "rank_warrior": "Воин",
        "rank_elite": "Элитный",
        "rank_master": "Мастер",
        "rank_grandmaster": "Грандмастер",
        "rank_epic": "Эпик",
        "rank_legend": "Легенда",
        "rank_mythic": "Мифик"
    }.get(rank_key, "Неизвестный ранг")

    await callback_query.message.edit_text(
        f"Вы выбрали ранг: {rank_name}. Стоимость: {price} грн. \nПодтвердите свой выбор, если хотите продолжить.",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{rank_key}"),
            InlineKeyboardButton(text="Назад", callback_data="boost_rank")
        )
    )

# Обработка подтверждения
@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_rank(callback_query: CallbackQuery):
    rank_key = callback_query.data.replace("confirm_", "")
    price = rank_prices.get(rank_key, 0)
    rank_name = {
        "rank_warrior": "Воин",
        "rank_elite": "Элитный",
        "rank_master": "Мастер",
        "rank_grandmaster": "Грандмастер",
        "rank_epic": "Эпик",
        "rank_legend": "Легенда",
        "rank_mythic": "Мифик"
    }.get(rank_key, "Неизвестный ранг")

    # Создаем ссылку на оплату через LiqPay
    liqpay = LiqPay(LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY)
    params = {
        "action": "pay",
        "amount": str(price),
        "currency": "UAH",
        "description": f"Оплата за буст {rank_name}",
        "order_id": f"order_{rank_key}_{callback_query.from_user.id}",
        "version": "3",
        "result_url": "https://your-bot-url.com/payment-success",
        "server_url": "https://your-bot-url.com/payment-callback"
    }
    link = liqpay.cnb_link(params)

    await callback_query.message.edit_text(
        f"Вы подтвердили выбор ранга: {rank_name}. \nДля завершения заказа оплатите по ссылке: {link}.",
    )

# Обработка уведомлений от LiqPay
@app.post("/payment-callback")
async def payment_callback(request: Request):
    data = await request.json()
    logger.info(f"Получены данные от LiqPay: {data}")
    return JSONResponse(content={"status": "ok"})

@app.get("/payment-success")
async def payment_success():
    return JSONResponse(content={"message": "Оплата успешно завершена!"})

# Запуск бота и FastAPI в одном процессе
async def main():
    # Запускаем FastAPI
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

    # Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запуск бота и FastAPI
    asyncio.run(main())
)
