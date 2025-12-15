import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, get_client, _format_track_id_for_lyrics
from ..storage import user_tokens

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "show_likes")
async def show_likes_callback(callback: CallbackQuery):
    await callback.answer()
    await show_likes(callback.message, callback.from_user.id)

@router.message(F.text == "❤️ Мои лайки")
@router.message(Command("likes"))
@require_auth
async def likes_command(message: Message):
    await show_likes(message, _effective_user_id_from_message(message))

async def show_likes(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю лайкнутые треки...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        likes = client.users_likes_tracks()
        refs = getattr(likes, "tracks", None) or likes
        refs = list(refs) if refs else []
        if not refs:
            await status_msg.edit_text("💔 У тебя пока нет лайкнутых треков.")
            return

        refs_to_show = refs[:10]
        track_ids = [ref.id for ref in refs_to_show]
        tracks = client.tracks(track_ids)

        text = "❤️ <b>Твои лайкнутые треки</b>\n\n"
        text += f"Всего: {len(refs)}\n"
        text += f"Показано: {len(refs_to_show)}\n\n"

        kb = []
        for i, track in enumerate(tracks, 1):
            artists = ", ".join(a.name for a in track.artists)
            duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
            text += f"{i}. <b>{track.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   ⏳ {duration}\n\n"

            track_id = _format_track_id_for_lyrics(track)
            kb.append(
                [
                    InlineKeyboardButton(
                        text=f"📜 Текст #{i}",
                        callback_data=f"lyrics:{track_id}",
                    )
                ]
            )

        kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")])
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    except Exception as e:
        logger.error(f"Ошибка получения лайков: {e}")
        await status_msg.edit_text(f"✗ Ошибка: {e}")