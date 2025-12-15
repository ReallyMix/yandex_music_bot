import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, get_client
router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "show_albums")
async def show_albums_callback(callback: CallbackQuery):
    await callback.answer()
    await show_albums(callback.message, callback.from_user.id)

@router.message(F.text == "💿 Альбомы")
@router.message(Command("albums"))
@require_auth
async def albums_command(message: Message):
    await show_albums(message, _effective_user_id_from_message(message))

async def show_albums(message: Message, user_id: int):
    status_msg = await message.answer("💿 Загружаю любимые альбомы...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        albums = client.users_likes_albums()
        if not albums:
            await status_msg.edit_text("💿 У тебя пока нет любимых альбомов.")
            return

        text = "💿 <b>Твои любимые альбомы</b>\n\n"
        text += f"Всего: {len(albums)}\n\n"

        for i, liked in enumerate(albums[:15], 1):
            album = liked.album
            artists = ", ".join(a.name for a in album.artists)
            text += f"{i}. <b>{album.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   📅 {album.year or 'Неизвестно'}\n"
            text += f"   🎵 {album.track_count} треков\n\n"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка получения альбомы: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")