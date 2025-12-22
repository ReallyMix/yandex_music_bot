import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..keyboards.main_menu import get_back_button

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "menu_help")
async def help_callback(callback: CallbackQuery):
    await callback.answer()
    await show_help(callback.message)

@router.message(Command("help"))
async def help_command(message: Message):
    await show_help(message)

async def show_help(message):
    help_text = (
        "❓ <b>Помощь</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Начало работы\n"
        "/auth - Авторизация\n"
        "/logout - Выход из аккаунта\n"
        "/help - Эта справка\n\n"
        "<b>Возможности:</b>\n"
        "📁 <b>Плейлисты</b> - просмотр ваших плейлистов\n"
        "🎵 <b>Текст песни</b> - получить текст по ID трека\n"
        "➕ <b>Создать плейлист</b> - создать новый плейлист\n"
        "🎼 <b>Добавить треки</b> - добавить треки в плейлист по названию\n"
        "❤️ <b>Лайкнуть трек</b> - лайкнуть трек по названию\n"
        "📊 <b>Статистика</b> - ваша статистика прослушивания\n\n"
        "<b>Поддержка:</b>\n"
        "Если у вас возникли проблемы, обратитесь к разработчику."
    )

    await message.answer(help_text, reply_markup=get_back_button())