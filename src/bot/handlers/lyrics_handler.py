import logging
from typing import Optional
from aiogram import Router, F
from aiogram.types import CallbackQuery
from yandex_music import Client

from ..storage import get_token  # ИЗМЕНЕНО ЗДЕСЬ

router = Router()
logger = logging.getLogger(__name__)

async def get_song_lyrics(token: str, user_id: int, track_id: str) -> Optional[str]:
    """
    Получение текста песни через Yandex Music API
    """
    try:
        # Создаем клиент Yandex Music с токеном пользователя
        client = Client(token).init()
        
        # Получаем информацию о треке
        tracks = client.tracks([track_id])
        if not tracks or len(tracks) == 0:
            logger.error(f"Трек с ID {track_id} не найден")
            return None

        track = tracks[0]

        # Получаем информацию о тексте песни
        lyrics = track.get_lyrics()
        if lyrics is None:
            logger.warning(f"Текст песни недоступен для трека {track_id}")
            return None

        # Получаем полный текст
        full_lyrics = lyrics.full_lyrics
        if full_lyrics is None:
            logger.warning(f"Полный текст песни недоступен для трека {track_id}")
            return None

        logger.info(f"Получен текст песни для трека {track_id}")
        return full_lyrics

    except Exception as e:
        logger.error(f"Ошибка при получении текста песни для трека {track_id}: {e}")
        return None

@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery):
    """
    Обработчик callback-запросов для получения текста песни
    """
    await callback.answer()
    user_id = callback.from_user.id

    # Получаем токен пользователя из хранилища
    token = get_token(user_id)
    if not token:
        await callback.message.answer(
            "❌ Нет токена авторизации Yandex Music. "
            "Используйте /start и /auth для авторизации."
        )
        return

    # Извлекаем ID трека из callback-данных
    # Формат данных: "lyrics:track_123456"
    track_id = callback.data.split(":", 1)[1]
    
    if not track_id:
        await callback.message.answer("❌ Не указан ID трека")
        return

    try:
        # Получаем текст песни через API Yandex Music
        lyrics = await get_song_lyrics(token, user_id, track_id)
        
        if not lyrics:
            await callback.message.answer(
                "📭 Текст песни не найден.\n\n"
                "Возможные причины:\n"
                "• Текст недоступен для этого трека\n"
                "• Трек не существует или удален\n"
                "• Ограничения прав доступа к контенту"
            )
            return

        # Разбиваем текст на части (Telegram имеет ограничение на длину сообщения)
        chunk_size = 4000  # Оставляем запас для HTML-разметки и эмодзи
        lyrics_parts = []
        
        if len(lyrics) > chunk_size:
            # Разбиваем на абзацы или по предложениям для лучшей читаемости
            paragraphs = lyrics.split('\n\n')
            current_part = ""
            
            for paragraph in paragraphs:
                if len(current_part) + len(paragraph) + 2 > chunk_size:
                    if current_part:
                        lyrics_parts.append(current_part)
                    current_part = paragraph
                else:
                    if current_part:
                        current_part += "\n\n" + paragraph
                    else:
                        current_part = paragraph
            
            if current_part:
                lyrics_parts.append(current_part)
        else:
            lyrics_parts = [lyrics]

        # Отправляем текст песни частями
        for i, part in enumerate(lyrics_parts):
            if i == 0:
                message_text = (
                    "🎵 <b>Текст песни</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{part}"
                )
            else:
                message_text = part
            
            if len(lyrics_parts) > 1:
                message_text += f"\n\n┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\nЧасть {i + 1} из {len(lyrics_parts)}"
            
            await callback.message.answer(message_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка получения текста песни: {e}", exc_info=True)
        
        # Более понятные сообщения об ошибках для пользователя
        error_message = str(e).lower()
        if "token" in error_message or "авториз" in error_message:
            await callback.message.answer(
                "🔑 Проблема с авторизацией Yandex Music.\n"
                "Возможно, токен устарел. Попробуйте авторизоваться заново командой /auth"
            )
        elif "network" in error_message or "сеть" in error_message or "timeout" in error_message:
            await callback.message.answer(
                "🌐 Проблема с сетью или Yandex Music API временно недоступен.\n"
                "Пожалуйста, попробуйте позже."
            )
        else:
            await callback.message.answer(
                f"⚠️ Произошла ошибка при получении текста песни:\n"
                f"<code>{str(e)[:200]}</code>",
                parse_mode="HTML"
            )