import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .common import require_auth, _effective_user_id_from_message, get_client, _format_track_id_for_lyrics

router = Router()
logger = logging.getLogger(__name__)

# Храним последний поиск каждого пользователя
user_search_cache = {}

@router.message(F.text.regexp(r"^[^/].+"))
@require_auth
async def search_handler(message: Message):
    """Обработчик поиска треков"""
    try:
        user_id = message.from_user.id
        query = message.text.strip()
        
        if len(query) < 2:
            await message.answer("🔍 Введите минимум 2 символа для поиска")
            return
        
        # Отправляем сообщение о поиске
        status_msg = await message.answer(f"🔍 Ищу: <b>{query}</b>...")
        
        # Получаем клиент Яндекс.Музыки
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации Яндекс.Музыки")
            return
        
        # Выполняем поиск
        search_result = client.search(query, type_="track")
        
        if not search_result or not search_result.tracks or not search_result.tracks.results:
            await status_msg.edit_text(f"❌ По запросу \"<b>{query}</b>\" ничего не найдено.")
            return
        
        tracks = search_result.tracks.results
        
        # Ограничиваем количество результатов на нашей стороне
        max_results = 20
        if len(tracks) > max_results:
            tracks = tracks[:max_results]
        
        if not tracks:
            await status_msg.edit_text(f"❌ По запросу \"<b>{query}</b>\" ничего не найдено.")
            return
        
        # Сохраняем в кэш
        user_search_cache[user_id] = {
            "tracks": tracks,
            "current_index": 0,
            "query": query,
            "total": len(tracks),
            "total_found": search_result.tracks.total if search_result.tracks else 0
        }
        
        # Показываем первый трек
        await show_track_result(user_id, status_msg, 0)
        
    except Exception as e:
        logger.error(f"Ошибка в search_handler: {e}", exc_info=True)
        try:
            await message.answer(f"❌ Ошибка при поиске: {str(e)[:100]}")
        except:
            pass

async def show_track_result(user_id: int, message: Message, index: int):
    """Показывает один трек с кнопками навигации"""
    try:
        # Проверяем есть ли данные для пользователя
        if user_id not in user_search_cache:
            await message.edit_text("❌ Результаты поиска устарели. Выполните поиск заново.")
            return
        
        data = user_search_cache[user_id]
        tracks = data["tracks"]
        
        # Проверяем валидность индекса
        if index < 0:
            index = 0
        if index >= len(tracks):
            index = len(tracks) - 1
        
        # Получаем трек
        track = tracks[index]
        
        # Форматируем данные с проверками
        artists = "Неизвестный исполнитель"
        if track.artists:
            try:
                artists = ", ".join(a.name for a in track.artists)
            except:
                pass
        
        duration = "0:00"
        if track.duration_ms:
            try:
                minutes = track.duration_ms // 60000
                seconds = (track.duration_ms // 1000) % 60
                duration = f"{minutes}:{seconds:02d}"
            except:
                pass
        
        album_name = "Не указан"
        if hasattr(track, 'albums') and track.albums and len(track.albums) > 0:
            album_name = track.albums[0].title
        elif hasattr(track, 'album') and track.album:
            album_name = track.album.title if hasattr(track.album, 'title') else "Не указан"
        
        track_title = "Без названия"
        if hasattr(track, 'title'):
            track_title = track.title
        
        # Формируем текст
        text = f"🎵 <b>Результат поиска</b>\n\n"
        text += f"<b>Исполнитель:</b> {artists}\n"
        text += f"<b>Песня:</b> {track_title}\n"
        text += f"<b>Длительность:</b> {duration}\n"
        text += f"<b>Альбом:</b> {album_name}\n\n"
        text += f"📄 <i>Результат {index + 1} из {len(tracks)} (всего найдено: {data.get('total_found', len(tracks))})</i>\n"
        text += f"🔍 <i>Запрос: \"{data.get('query', '')}\"</i>"
        
        # Создаем кнопки навигации между треками
        buttons_row = []
        
        # Кнопка "Назад" (предыдущий трек)
        if index > 0:
            buttons_row.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"search_prev:{user_id}:{index}")
            )
        
        # Кнопка "Текст"
        try:
            track_id = _format_track_id_for_lyrics(track)
            buttons_row.append(
                InlineKeyboardButton(text="📜 Текст", callback_data=f"lyrics:{track_id}")
            )
        except:
            buttons_row.append(
                InlineKeyboardButton(text="📜 Текст", callback_data="lyrics:error")
            )
        
        # Кнопка "Вперед" (следующий трек)
        if index < len(tracks) - 1:
            buttons_row.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"search_next:{user_id}:{index}")
            )
        
        # Собираем клавиатуру
        keyboard_rows = []
        if buttons_row:
            keyboard_rows.append(buttons_row)
        
        # Кнопки управления поиском
        keyboard_rows.append([
            InlineKeyboardButton(text="🔙 Назад к меню", callback_data="search_back"),
            InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_new")
        ])
        
        # Обновляем сообщение
        await message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        )
        
        # Обновляем индекс в кэше
        user_search_cache[user_id]["current_index"] = index
        
    except Exception as e:
        logger.error(f"Ошибка в show_track_result: {e}", exc_info=True)
        await message.edit_text("❌ Ошибка при отображении результата")

@router.callback_query(F.data.startswith("search_"))
async def handle_search_navigation(callback: CallbackQuery):
    """Обработчик всех callback-кнопок поиска"""
    try:
        data = callback.data
        
        if data.startswith("search_prev:"):
            # Обработка кнопки "Назад" (предыдущий трек)
            parts = data.split(":")
            if len(parts) >= 3:
                user_id = int(parts[1])
                current_index = int(parts[2])
                await show_track_result(user_id, callback.message, current_index - 1)
        
        elif data.startswith("search_next:"):
            # Обработка кнопки "Вперед" (следующий трек)
            parts = data.split(":")
            if len(parts) >= 3:
                user_id = int(parts[1])
                current_index = int(parts[2])
                await show_track_result(user_id, callback.message, current_index + 1)
        
        elif data == "search_new":
            # Обработка кнопки "Новый поиск"
            user_id = callback.from_user.id
            if user_id in user_search_cache:
                del user_search_cache[user_id]
            
            await callback.message.edit_text(
                "🔍 <b>Новый поиск</b>\n\n"
                "Введите название песни или исполнителя для поиска."
            )
        
        elif data == "search_back":
            # Обработка кнопки "Назад к меню" - возврат на уровень выше
            user_id = callback.from_user.id
            if user_id in user_search_cache:
                del user_search_cache[user_id]
            
            # Здесь можно вернуться в главное меню или предыдущее состояние
            # Если у вас есть главное меню, вызовите соответствующую функцию
            # Если нет, просто покажем сообщение о возврате
            await callback.message.edit_text(
                "🔙 <b>Возврат в главное меню</b>\n\n"
                "Поиск отменен. Вы можете использовать другие команды бота."
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_search_navigation: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)

@router.callback_query(F.data.startswith("lyrics:"))
async def handle_lyrics(callback: CallbackQuery):
    """Обработчик кнопки Текст"""
    try:
        track_id = callback.data.split(":")[1]
        
        if track_id == "error":
            await callback.answer("❌ Не удалось получить информацию о треке", show_alert=True)
            return
        
        # Здесь должна быть ваша логика получения текста песни
        await callback.answer(f"Запрос текста для трека: {track_id}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_lyrics: {e}")
        await callback.answer("❌ Ошибка при запросе текста", show_alert=True)