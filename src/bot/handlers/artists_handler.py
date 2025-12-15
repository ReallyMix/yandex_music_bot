import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, get_client
router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "show_artists")
async def show_artists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_artists(callback.message, callback.from_user.id)

@router.message(F.text == "👨‍🎤 Любимые артисты")
@router.message(Command("artists"))
@require_auth
async def artists_command(message: Message):
    await show_artists(message, _effective_user_id_from_message(message))

async def show_artists(message: Message, user_id: int):
    status_msg = await message.answer("👨‍🎤 Загружаю любимых артистов...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("✗ Ошибка авторизации")
            return

        artists = client.users_likes_artists()
        if not artists:
            await status_msg.edit_text("👨‍🎤 У тебя пока нет любимых артистов.")
            return

        text = "👨‍🎤 <b>Твои любимые артисты</b>\n\n"
        text += f"Всего: {len(artists)}\n\n"

        for i, liked in enumerate(artists[:15], 1):
            art = liked.artist
            text += f"{i}. <b>{art.name}</b>\n"
            if art.genres:
                genres = ", ".join(art.genres[:3])
                text += f"   🎵 {genres}\n"
            text += "\n"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка получения артистов: {e}")
        await status_msg.edit_text(f"✗ Ошибка: {e}")