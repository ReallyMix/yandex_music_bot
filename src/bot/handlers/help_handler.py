from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import AUTH_URL

router = Router()

@router.message(Command("help"))
async def help_command(message: Message):
    """Справка по боту"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Получить токен",
                    url=AUTH_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="📘 GitHub с инструкциями",
                    url="https://github.com/MarshalX/yandex-music-api/discussions/513",
                )
            ]
        ]
    )

    await message.answer(
        "<b>📖 Справка по боту Яндекс.Музыки</b>\n\n"
        "<b>🔐 Авторизация:</b>\n"
        "/start - начало работы\n"
        "/settoken TOKEN - установить токен\n"
        "/check - проверить токен\n"
        "/logout - удалить токен\n\n"
        "<b>ℹ️ Информация:</b>\n"
        "/help - эта справка\n\n"
        "<b>❓ Как получить токен:</b>\n"
        "1. Нажми кнопку «📱 Получить токен»\n"
        "2. Авторизуйся в Яндексе\n"
        "3. Скопируй токен из URL после редиректа\n"
        "4. Отправь командой /settoken\n\n"
        "<i>Подробная инструкция: нажми кнопку выше в /start</i>",
        reply_markup=keyboard,
    )

@router.message(Command("about"))
async def about_command(message: Message):
    """О боте"""
    await message.answer(
        "<b>🎵 Бот для Яндекс.Музыки</b>\n\n"
        "Версия: 1.0.0\n"
        "Разработчик: @yourusername\n\n"
        "Используется:\n"
        "• aiogram 3.x\n"
        "• yandex-music API\n\n"
        "<i>Бот не является официальным продуктом Яндекса</i>"
    )