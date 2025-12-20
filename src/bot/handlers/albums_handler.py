import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .common import require_auth, _effective_user_id_from_message, get_client
router = Router()
logger = logging.getLogger(__name__)

# Хранилище данных о альбомах пользователей (временное, в памяти)
# В реальном приложении лучше использовать базу данных
user_albums_data = {}

@router.callback_query(F.data == "show_albums")
async def show_albums_callback(callback: CallbackQuery):
    await callback.answer()
    await show_first_album(callback.message, callback.from_user.id)

@router.message(F.text == "💿 Альбомы")
@router.message(Command("albums"))
@require_auth
async def albums_command(message: Message):
    await show_first_album(message, _effective_user_id_from_message(message))

async def show_first_album(message: Message, user_id: int):
    """Показать первый альбом из списка"""
    status_msg = await message.answer("💿 Загружаю любимые альбомы...")
    
    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return
        
        # Получаем все альбомы
        liked_albums = client.users_likes_albums()
        if not liked_albums:
            await status_msg.edit_text("💿 У тебя пока нет любимых альбомов.")
            return
        
        # Преобразуем в удобный формат
        albums_list = []
        for liked in liked_albums:
            album = liked.album
            artists = ", ".join(a.name for a in album.artists)
            
            albums_list.append({
                'title': album.title,
                'artists': artists,
                'year': album.year or 'Неизвестно',
                'track_count': album.track_count,
                'album_id': album.id
            })
        
        # Сохраняем данные для пользователя
        user_albums_data[user_id] = {
            'albums': albums_list,
            'current_index': 0,
            'message_id': status_msg.message_id
        }
        
        # Показываем первый альбом
        await display_album(status_msg, user_id, 0)
        
    except Exception as e:
        logger.error(f"Ошибка получения альбомов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")

async def display_album(message: Message, user_id: int, index: int):
    """Отобразить альбом по индексу"""
    try:
        user_data = user_albums_data.get(user_id)
        if not user_data:
            await message.edit_text("❌ Данные не найдены. Запросите альбомы заново.")
            return
        
        albums = user_data['albums']
        
        if index < 0 or index >= len(albums):
            await message.edit_text("❌ Альбом не найден.")
            return
        
        album = albums[index]
        
        # Формируем текст
        text = f"💿 <b>Альбом {index + 1} из {len(albums)}</b>\n\n"
        text += f"<b>Название:</b> {album['title']}\n"
        text += f"<b>Артист(ы):</b> {album['artists']}\n"
        text += f"<b>Год:</b> {album['year']}\n"
        text += f"<b>Треков:</b> {album['track_count']}\n"
        text += f"<b>ID:</b> {album['album_id']}"
        
        # Создаем клавиатуру навигации
        builder = InlineKeyboardBuilder()
        
        # Кнопки навигации
        if index > 0:
            builder.button(text="⬅️ Предыдущий", callback_data=f"album_prev_{index}")
        if index < len(albums) - 1:
            builder.button(text="Следующий ➡️", callback_data=f"album_next_{index}")
        
        # Дополнительные кнопки
        builder.row(
            InlineKeyboardButton(text="🎵 Открыть в Яндекс.Музыке", 
                               url=f"https://music.yandex.ru/album/{album['album_id']}")
        )
        builder.row(
            InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_music"),
            InlineKeyboardButton(text="❌ Закрыть", callback_data="close_album")
        )
        
        # Обновляем текущий индекс
        user_albums_data[user_id]['current_index'] = index
        
        # Показываем альбом в текстовом формате
        await message.edit_text(
            text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
            
    except Exception as e:
        logger.error(f"Ошибка отображения альбома: {e}")
        await message.edit_text(f"❌ Ошибка при отображении альбома: {e}")

@router.callback_query(F.data.startswith("album_"))
async def handle_album_navigation(callback: CallbackQuery):
    """Обработка навигации по альбомам"""
    await callback.answer()
    
    user_id = callback.from_user.id
    data = callback.data
    
    # Получаем текущий индекс из callback_data
    if data.startswith("album_prev_"):
        current_index = int(data.split("_")[2])
        new_index = current_index - 1
    elif data.startswith("album_next_"):
        current_index = int(data.split("_")[2])
        new_index = current_index + 1
    else:
        return
    
    # Показываем альбом с новым индексом
    await display_album(callback.message, user_id, new_index)

@router.callback_query(F.data == "close_album")
async def close_album(callback: CallbackQuery):
    """Закрыть просмотр альбомов"""
    await callback.answer()
    
    # Удаляем сообщение с альбомом
    await callback.message.delete()
    
    # Очищаем данные пользователя (опционально)
    user_id = callback.from_user.id
    if user_id in user_albums_data:
        del user_albums_data[user_id]