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


class LikeTrackStates(StatesGroup):
    waiting_for_track_query = State()


@router.callback_query(F.data == "menu_like_track")
async def like_track_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    user_id = callback.from_user.id
    token = get_token(user_id)
    
    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return
    
    await state.set_state(LikeTrackStates.waiting_for_track_query)
    await callback.message.edit_text(
        "❤️ <b>Лайкнуть трек</b>\n\n"
        "Отправьте название трека или ID.\n\n"
        "<b>Примеры:</b>\n"
        "• <code>Imagine Dragons Believer</code>\n"
        "• <code>The Weeknd Blinding Lights</code>\n"
        "• <code>Моргенштерн</code>\n"
        "• <code>67890:12345</code> (ID трека)\n\n"
        "💡 Можно писать без дефисов и кавычек\n\n"
        "Для отмены используйте /cancel",
        reply_markup=get_back_button()
    )


@router.message(LikeTrackStates.waiting_for_track_query)
async def receive_track_query(message: Message, state: FSMContext):
    user_id = message.from_user.id
    token = get_token(user_id)
    query = message.text.strip()
    
    status_msg = await message.answer("🔍 Ищу трек...")
    
    try:
        from yandex_music import Client
        client = Client(token).init()
        
        track_id = None
        track_info = None
        
        if ':' in query or (query.replace('-', '').replace('_', '').isdigit() and len(query) > 5):
            track_id = query
            
            try:
                tracks = client.tracks([track_id])
                if tracks and len(tracks) > 0:
                    track = tracks[0]
                    track_info = f"{track.artists[0].name} - {track.title}" if track.artists else track.title
            except:
                pass
        else:
            await status_msg.edit_text("🔍 Ищу трек по названию...")
            
            clean_query = query.replace('"', '').replace("'", '').strip()
            
            search_result = client.search(clean_query, type_='track')
            
            if not search_result or not search_result.tracks or not search_result.tracks.results:
                await status_msg.edit_text(
                    f"❌ <b>Трек не найден</b>\n\n"
                    f"Запрос: <code>{query}</code>\n\n"
                    "Попробуйте:\n"
                    "• Написать по-другому\n"
                    "• Убрать лишние символы\n"
                    "• Добавить имя исполнителя\n"
                    "• Использовать только название песни\n\n"
                    "Примеры хороших запросов:\n"
                    "• <code>Imagine Dragons Believer</code>\n"
                    "• <code>The Weeknd Blinding</code>\n"
                    "• <code>Моргенштерн Cadillac</code>",
                    reply_markup=get_back_button()
                )
                await state.clear()
                return
            
            track = search_result.tracks.results[0]
            
            if hasattr(track, 'albums') and track.albums and len(track.albums) > 0:
                track_id = f"{track.id}:{track.albums[0].id}"
            else:
                track_id = str(track.id)
            
            artist_name = track.artists[0].name if track.artists else "Неизвестный исполнитель"
            track_info = f"{artist_name} - {track.title}"
            
            logger.info(f"Найден трек: {track_info}, ID: {track_id}")
            await status_msg.edit_text(f"✅ Найден: <b>{track_info}</b>\n\n❤️ Лайкаю...")
        
        try:
            client.users_likes_tracks_add(track_id)
            
            success_text = "✅ <b>Трек лайкнут!</b>\n\n"
            if track_info:
                success_text += f"🎵 {track_info}\n"
            success_text += f"🆔 ID: <code>{track_id}</code>"
            
            await status_msg.edit_text(
                success_text,
                reply_markup=get_back_button()
            )
            logger.info(f"Трек {track_id} лайкнут пользователем {user_id}")
            
        except Exception as like_error:
            logger.error(f"Ошибка лайка трека {track_id}: {like_error}")
            
            error_msg = str(like_error).lower()
            if 'already' in error_msg or 'exist' in error_msg:
                await status_msg.edit_text(
                    f"ℹ️ <b>Трек уже в ваших лайках</b>\n\n"
                    f"🎵 {track_info if track_info else query}\n"
                    f"🆔 ID: <code>{track_id}</code>",
                    reply_markup=get_back_button()
                )
            else:
                await status_msg.edit_text(
                    f"❌ <b>Не удалось лайкнуть</b>\n\n"
                    f"🎵 {track_info if track_info else query}\n"
                    f"🆔 ID: <code>{track_id}</code>\n\n"
                    f"Ошибка: <code>{str(like_error)[:100]}</code>",
                    reply_markup=get_back_button()
                )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка поиска/лайка трека: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Ошибка</b>\n\n"
            f"Запрос: <code>{query}</code>\n\n"
            f"Описание: <code>{str(e)[:150]}</code>\n\n"
            "Попробуйте:\n"
            "• Написать название по-другому\n"
            "• Использовать только ключевые слова\n"
            "• Указать прямой ID трека",
            reply_markup=get_back_button()
        )
        await state.clear()