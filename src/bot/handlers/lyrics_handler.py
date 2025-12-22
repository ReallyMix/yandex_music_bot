import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ...database.storage import get_token
from ..services import ym_service
from ..keyboards.main_menu import get_back_button

router = Router()
logger = logging.getLogger(__name__)


class LyricsStates(StatesGroup):
    waiting_for_track_query = State()


@router.callback_query(F.data == "menu_lyrics")
async def lyrics_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user_id = callback.from_user.id
    token = get_token(user_id)

    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return

    await state.set_state(LyricsStates.waiting_for_track_query)
    await callback.message.edit_text(
        "🎵 <b>Получить текст песни</b>\n\n"
        "Отправьте название трека или ID.\n\n"
        "<b>Примеры:</b>\n"
        "• <code>Imagine Dragons Believer</code>\n"
        "• <code>Платина Валентина</code>\n"
        "• <code>Платина - ХТТ</code>\n"
        "• <code>33311009:5568718</code> (ID трека)\n\n"
        "<b>ID из URL:</b>\n"
        "<code>music.yandex.ru/album/5568718/track/33311009</code>\n"
        "→ <code>33311009:5568718</code>\n\n"
        "Для отмены используйте /cancel",
        reply_markup=get_back_button()
    )


@router.message(LyricsStates.waiting_for_track_query)
async def receive_track_query(message: Message, state: FSMContext):
    user_id = message.from_user.id
    token = get_token(user_id)
    query = (message.text or "").strip()

    if not token:
        await message.answer(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        await state.clear()
        return

    if not query:
        await message.answer(
            "❌ Пустой запрос.\n\n"
            "Отправьте название трека или ID.",
            reply_markup=get_back_button()
        )
        return

    status_msg = await message.answer("🔍 Ищу трек...")

    try:
        from yandex_music import Client
        client = Client(token).init()

        track_id = None
        track_title = "Трек"

        if ':' in query or (query.replace('-', '').replace('_', '').isdigit() and len(query) > 5):
            track_id = query.strip()
            logger.info(f"[lyrics] Используем прямой ID: {track_id}")

            try:
                tracks = client.tracks([track_id])
                if not tracks:
                    raise RuntimeError("Трек не найден по ID")

                track = tracks[0]
                artists = getattr(track, "artists", []) or []
                artist_name = artists[0].name if artists else "Unknown"
                track_title = f"{artist_name} - {track.title}"
                await status_msg.edit_text(
                    f"✅ Найден: <b>{track_title}</b>\n\n🎵 Получаю текст...",
                    reply_markup=get_back_button()
                )
            except Exception as e:
                logger.warning(f"[lyrics] Не удалось получить трек по ID {track_id}: {e}")
                await status_msg.edit_text(
                    f"❌ Трек не найден по ID.\n\n"
                    f"🆔 <code>{track_id}</code>\n\n"
                    "Проверьте формат: <code>track_id:album_id</code>",
                    reply_markup=get_back_button()
                )
                await state.clear()
                return
        else:
            await status_msg.edit_text("🔍 Ищу трек по названию...", reply_markup=get_back_button())

            clean_query = (
                query.replace('"', '')
                     .replace("'", "")
                     .replace('«', '')
                     .replace('»', '')
                     .strip()
            )

            search_result = client.search(clean_query, type_="track")
            if not search_result or not search_result.tracks or not search_result.tracks.results:
                await status_msg.edit_text(
                    "❌ <b>Трек не найден</b>\n\n"
                    f"Запрос: <code>{query}</code>\n\n"
                    "Попробуйте:\n"
                    "• Добавить исполнителя\n"
                    "• Убрать лишние символы\n"
                    "• Написать более точно",
                    reply_markup=get_back_button()
                )
                await state.clear()
                return

            track = search_result.tracks.results[0]

            albums = getattr(track, "albums", []) or []
            if albums:
                track_id = f"{track.id}:{albums[0].id}"
            else:
                track_id = str(track.id)

            artists = getattr(track, "artists", []) or []
            artist_name = artists[0].name if artists else "Неизвестный исполнитель"
            track_title = f"{artist_name} - {track.title}"

            logger.info(f"[lyrics] Найден трек: {track_title} ({track_id})")
            await status_msg.edit_text(
                f"✅ Найден: <b>{track_title}</b>\n\n🎵 Получаю текст...",
                reply_markup=get_back_button()
            )

        if not track_id:
            await status_msg.edit_text(
                "❌ Не удалось определить ID трека.",
                reply_markup=get_back_button()
            )
            await state.clear()
            return

        lyrics = await ym_service.get_song_lyrics(token, user_id, track_id)

        if not isinstance(lyrics, str) or not lyrics.strip():
            await status_msg.edit_text(
                f"❌ <b>Текст не найден</b>\n\n"
                f"🎵 {track_title}\n"
                f"🆔 <code>{track_id}</code>\n\n"
                "Причины:\n"
                "• У трека нет текста в базе\n"
                "• Инструментал\n"
                "• Региональные ограничения\n\n"
                "Попробуйте другой трек.",
                reply_markup=get_back_button()
            )
            await state.clear()
            return

        text = lyrics.strip()
        header = f"🎵 <b>{track_title}</b>\n🆔 <code>{track_id}</code>\n\n"

        if len(text) > 3800:
            await status_msg.edit_text(
                header + "📄 Текст длинный, отправляю частями:",
                reply_markup=get_back_button()
            )
            parts = [text[i:i + 3800] for i in range(0, len(text), 3800)]
            for idx, part in enumerate(parts, 1):
                await message.answer(
                    f"<pre>Часть {idx}/{len(parts)}\n\n{part}</pre>"
                )
        else:
            await status_msg.edit_text(
                f"{header}<pre>{text}</pre>",
                reply_markup=get_back_button()
            )

        logger.info(f"[lyrics] Текст отправлен пользователю {user_id}: {track_title}")
        await state.clear()

    except Exception as e:
        logger.error(f"[lyrics] Ошибка: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Ошибка при получении текста</b>\n\n"
            f"<code>{str(e)[:200]}</code>",
            reply_markup=get_back_button()
        )
        await state.clear()