from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    text = (
        "🤖 <b>Yandex Music Bot — справка</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — начало работы и авторизация\n"
        "/help — показать это сообщение\n\n"
        "<b>Кнопки после авторизации:</b>\n"
        "📋 Мои плейлисты — показать твои плейлисты\n"
        "🆕 Создать плейлист — создать новый плейлист\n"
        "📊 Статистика — базовая информация по аккаунту\n"
        "❓ Помощь — показать это сообщение\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message):
    """Обработка нажатия кнопки '❓ Помощь'"""
    await cmd_help(message)
