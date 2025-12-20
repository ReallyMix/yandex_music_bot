import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, get_client, AUTH_URL
from ..storage import has_token

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "open_music_menu")
async def open_music_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer()
    if not has_token(user_id):
        await callback.message.answer(
            "✗ <b>Требуется авторизация!</b>\nИспользуй /start и /auth."
        )
        return
    await _send_music_menu(callback.message)

@router.callback_query(F.data == "open_search")
async def open_search_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer()
    if not has_token(user_id):
        await callback.message.answer(
            "✗ <b>Требуется авторизация!</b>\nИспользуй /start и /auth."
        )
        return
    await _send_search_prompt(callback.message)

async def _send_music_menu(message: Message) -> None:
    # 🔄 Добавляем кнопку "Назад" в самый конец клавиатуры
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Мои лайки", callback_data="show_likes"),
                InlineKeyboardButton(text="📁 Плейлисты", callback_data="show_playlists"),
            ],
            [
                InlineKeyboardButton(text="👨‍🎤 Любимые артисты", callback_data="show_artists"),
                InlineKeyboardButton(text="💿 Альбомы", callback_data="show_albums"),
            ],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
            # 🔙 Новая строка с кнопкой "Назад" - возвращает в главное меню
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )
    await message.answer("♪ <b>Моя музыка</b>\nВыбери раздел:", reply_markup=keyboard)

async def _send_search_prompt(message: Message) -> None:
    await message.answer(
        "🔍 <b>Поиск музыки</b>\n\n"
        "Отправь название трека, артиста или альбома.\n\n"
        "Примеры:\n"
        "• <code>Imagine Dragons</code>\n"
        "• <code>Believer</code>\n"
        "• <code>Night Visions</code>"
    )

@router.message(F.text == "Моя музыка")
@router.message(Command("mymusic"))
@require_auth
async def my_music_handler(message: Message):
    await _send_music_menu(message)

@router.message(F.text == "Поиск")
@router.message(Command("search"))
@require_auth
async def search_command(message: Message):
    await _send_search_prompt(message)

@router.callback_query(F.data == "back_to_music")
async def back_to_music_callback(callback: CallbackQuery):
    await callback.answer()
    if not has_token(callback.from_user.id):
        await callback.message.answer("✗ Требуется авторизация. Используй /start.")
        return
    await _send_music_menu(callback.message)

# 🔄 НОВЫЙ ОБРАБОТЧИК ДЛЯ КНОПКИ "НАЗАД" В ГЛАВНОЕ МЕНЮ
@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    """
    Возвращает пользователя в главное меню бота
    (этап, который был до меню "Моя музыка")
    """
    await callback.answer()
    
    # 📱 Создаем клавиатуру главного меню
    # (предполагаем, что это основное меню бота с основными командами)
    main_menu_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎵 Моя музыка", callback_data="open_music_menu")],
            [InlineKeyboardButton(text="🔍 Поиск музыки", callback_data="open_search")],
            [InlineKeyboardButton(text="🔑 Авторизация", callback_data="auth")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
        ]
    )
    
    # ✉️ Отправляем сообщение с главным меню
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard
    )