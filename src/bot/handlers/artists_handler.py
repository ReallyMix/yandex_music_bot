import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from .common import require_auth, _effective_user_id_from_message, get_client

router = Router()
logger = logging.getLogger(__name__)

# Храним данные артистов в памяти для пагинации
user_artists_cache = {}


@router.callback_query(F.data == "show_artists")
async def show_artists_callback(callback: CallbackQuery):
    await callback.answer()
    # Отправляем новое сообщение при первом открытии
    await show_artist(callback.message, callback.from_user.id, artist_index=0, edit=False)


@router.message(F.text == "👨‍🎤 Любимые артисты")
@router.message(Command("artists"))
@require_auth
async def artists_command(message: Message):
    # Отправляем новое сообщение при команде
    await show_artist(message, _effective_user_id_from_message(message), artist_index=0, edit=False)


async def show_artist(message: Message, user_id: int, artist_index: int = 0, edit: bool = True):
    """
    Основная функция для отображения одного артиста с пагинацией
    """
    try:
        # Отправляем промежуточное сообщение только при первом открытии
        if not edit:
            status_msg = await message.answer("👨‍🎤 Загружаю артистов...")
            message_to_edit = status_msg
        else:
            message_to_edit = message
            await message_to_edit.edit_text("👨‍🎤 Обновляю информацию...")

        client = get_client(user_id)
        if not client:
            await message_to_edit.edit_text("✗ Ошибка авторизации")
            return

        # Получаем список артистов
        artists = client.users_likes_artists()
        if not artists:
            await message_to_edit.edit_text("👨‍🎤 У тебя пока нет любимых артистов.")
            return

        # Сохраняем артистов в кэш
        user_artists_cache[user_id] = artists
        
        # Проверяем границы индекса
        if artist_index < 0:
            artist_index = 0
        if artist_index >= len(artists):
            artist_index = len(artists) - 1

        # Получаем текущего артиста
        liked = artists[artist_index]
        art = liked.artist

        # Формируем текст
        text = f"👨‍🎤 <b>Артист {artist_index + 1} из {len(artists)}</b>\n\n"
        text += f"<b>{art.name}</b>\n"
        
        if hasattr(art, 'genres') and art.genres:
            genres = ", ".join(art.genres[:3])
            text += f"🎵 <b>Жанры:</b> {genres}\n"
        
        # Убрали блок с описанием
        
        if hasattr(art, 'counts'):
            if hasattr(art.counts, 'tracks'):
                text += f"\n📊 <b>Треков:</b> {art.counts.tracks}"
            if hasattr(art.counts, 'albums'):
                text += f" | <b>Альбомов:</b> {art.counts.albums}"
            if hasattr(art.counts, 'videos'):
                text += f" | <b>Видео:</b> {art.counts.videos}"

        # Создаем клавиатуру
        keyboard_buttons = []
        
        # Первый ряд: навигация между артистами
        nav_buttons = []
        
        if artist_index > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️", callback_data=f"artist_prev:{artist_index}")
            )
        
        # Добавляем кнопку "Назад" в мою музыку в середину
        nav_buttons.append(
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_my_music")
        )
        
        if artist_index < len(artists) - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="▶️", callback_data=f"artist_next:{artist_index}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        # Кнопка "Открыть в Яндекс.Музыке"
        if hasattr(art, 'id'):
            yandex_music_url = f"https://music.yandex.ru/artist/{art.id}"
            keyboard_buttons.append([
                InlineKeyboardButton(text="🎧 Открыть в Яндекс.Музыке", url=yandex_music_url)
            ])
        
        # Убрали кнопку "Список всех артистов"

        # Редактируем существующее сообщение
        await message_to_edit.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            disable_web_page_preview=True
        )

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            if not edit:
                await message.answer(f"✗ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Ошибка получения артиста: {e}")
        if not edit:
            await message.answer(f"✗ Ошибка: {e}")
        else:
            await message.edit_text(f"✗ Ошибка: {e}")


@router.callback_query(F.data.startswith("artist_prev:"))
async def artist_prev_callback(callback: CallbackQuery):
    await callback.answer()
    
    data = callback.data.split(":")
    if len(data) != 2:
        return
    
    current_index = int(data[1])
    new_index = current_index - 1
    
    await show_artist(callback.message, callback.from_user.id, artist_index=new_index, edit=True)


@router.callback_query(F.data.startswith("artist_next:"))
async def artist_next_callback(callback: CallbackQuery):
    await callback.answer()
    
    data = callback.data.split(":")
    if len(data) != 2:
        return
    
    current_index = int(data[1])
    new_index = current_index + 1
    
    await show_artist(callback.message, callback.from_user.id, artist_index=new_index, edit=True)


@router.callback_query(F.data == "back_to_my_music")
async def back_to_my_music_callback(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    if user_id in user_artists_cache:
        del user_artists_cache[user_id]
    
    # Удаляем текущее сообщение (с артистом)
    try:
        await callback.message.delete()
    except:
        pass
    
    # Отправляем новое сообщение с меню "Моя музыка" (только базовые разделы)
    await callback.message.answer(
        "🎵 <b>Моя музыка</b>\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👨‍🎤 Любимые артисты", callback_data="show_artists")],
                [InlineKeyboardButton(text="🎵 Любимые треки", callback_data="show_tracks")],
                [InlineKeyboardButton(text="🎼 Любимые альбомы", callback_data="show_albums")],
                [InlineKeyboardButton(text="📻 Любимые плейлисты", callback_data="show_playlists")]
                # Убрали кнопки "Поиск музыки" и "В главное меню"
            ]
        )
    )