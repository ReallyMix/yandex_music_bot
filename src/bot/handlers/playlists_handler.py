import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, _get_playlist_tracks_by_kind
from ..storage import get_token
from ..services import ym_service

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "show_playlists")
async def show_playlists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_playlists(callback.message, callback.from_user.id)

@router.message(F.text == "Плейлисты")
@router.message(Command("playlists"))
@require_auth
async def playlists_command(message: Message):
    await show_playlists(message, _effective_user_id_from_message(message))

async def show_playlists(message: Message, user_id: int):
    status_msg = await message.answer("📁 Загружаю плейлисты...")

    token = get_token(user_id)  # ИЗМЕНЕНО ЗДЕСЬ
    if not token:
        await status_msg.edit_text("✗ Ошибка авторизации")
        return

    try:
        # services.YandexMusicService: асинхронный метод get_user_playlists
        playlists = await ym_service.get_user_playlists(token, user_id)
        if not playlists:
            await status_msg.edit_text("📁 У тебя пока нет плейлистов.")
            return

        text = "📁 <b>Твои плейлисты</b>\n"
        text += f"Всего: {len(playlists)}\n"

        kb = []
        for i, pl in enumerate(playlists[:15], 1):
            title = pl.get("title") or "Без названия"
            count = pl.get("track_count", 0)
            desc = pl.get("description")
            kind = pl.get("kind")

            text += f"{i}. <b>{title}</b>\n"
            text += f"    {count} треков\n"
            if desc:
                d = desc if len(desc) <= 50 else desc[:50] + "..."
                text += f"    {d}\n"
            text += "\n"

            if kind is not None:
                kb.append(
                    [
                        InlineKeyboardButton(
                            text=f"📂 Открыть #{i}",
                            callback_data=f"playlist:{kind}",
                        )
                    ]
                )

        kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")])
        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    except Exception as e:
        logger.error(f"Ошибка получения плейлистов: {e}")
        await status_msg.edit_text(f"✗ Ошибка: {e}")

@router.callback_query(F.data.startswith("playlist:"))
async def playlist_open_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    token = get_token(user_id)  # ИЗМЕНЕНО ЗДЕСЬ
    if not token:
        await callback.message.answer("✗ Нет токена. Используй /start и /auth.")
        return

    try:
        kind = int(callback.data.split(":", 1)[1])
        tracks = await _get_playlist_tracks_by_kind(token, user_id, kind)
        if not tracks:
            await callback.message.answer(
                "✗ Не удалось получить треки этого плейлиста."
            )
            return

        text = "📁 <b>Треки плейлиста</b>\n\n"
        for i, tr in enumerate(tracks[:40], 1):
            title = getattr(tr, "title", "Без названия")
            artists = ", ".join(
                a.name for a in (getattr(tr, "artists", None) or [])
            )
            duration_ms = getattr(tr, "duration_ms", None)
            dur = ""
            if duration_ms:
                dur = f"{duration_ms // 60000}:{(duration_ms // 1000) % 60:02d}"

            text += f"{i}. <b>{title}</b>\n"
            if artists:
                text += f"   🎤 {artists}\n"
            if dur:
                text += f"   ⏳ {dur}\n"
            text += "\n"

        await callback.message.answer(text)

    except Exception as e:
        logger.error(f"Ошибка открытия плейлиста: {e}")
        await callback.message.answer(f"✗ Ошибка: {e}")