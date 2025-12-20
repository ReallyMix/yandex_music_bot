import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from .common import require_auth, _effective_user_id_from_message, get_client
from ..storage import user_tokens

router = Router()
logger = logging.getLogger(__name__)

user_track_messages = {}

@router.callback_query(F.data == "show_likes")
async def show_likes_callback(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id in user_track_messages:
        try:
            await user_track_messages[callback.from_user.id].delete()
        except:
            pass
    
    message = await callback.message.answer("⏳ Загружаю лайкнутые треки...")
    user_track_messages[callback.from_user.id] = message
    await show_liked_track(callback.from_user.id, 0, message)

@router.message(F.text == "❤️ Мои лайки")
@router.message(Command("likes"))
@require_auth
async def likes_command(message: Message):
    user_id = _effective_user_id_from_message(message)
    
    if user_id in user_track_messages:
        try:
            await user_track_messages[user_id].delete()
        except:
            pass
    
    status_msg = await message.answer("⏳ Загружаю лайкнутые треки...")
    user_track_messages[user_id] = status_msg
    await show_liked_track(user_id, 0, status_msg)

@router.callback_query(F.data.startswith("prev_liked:"))
async def prev_liked_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    if user_id not in user_track_messages:
        await callback.answer("Сообщение устарело, начните заново /likes", show_alert=True)
        return
    
    index = int(callback.data.split(":")[1])
    await show_liked_track(user_id, index - 1, user_track_messages[user_id])

@router.callback_query(F.data.startswith("next_liked:"))
async def next_liked_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    if user_id not in user_track_messages:
        await callback.answer("Сообщение устарело, начните заново /likes", show_alert=True)
        return
    
    index = int(callback.data.split(":")[1])
    await show_liked_track(user_id, index + 1, user_track_messages[user_id])

@router.callback_query(F.data == "back_to_music")
async def back_to_music_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    
    if user_id in user_track_messages:
        try:
            await user_track_messages[user_id].delete()
            del user_track_messages[user_id]
        except:
            pass

async def show_liked_track(user_id: int, index: int, message_to_edit: Message):
    try:
        client = get_client(user_id)
        if not client:
            await message_to_edit.edit_text("❌ Ошибка авторизации")
            return

        likes = client.users_likes_tracks()
        refs = getattr(likes, "tracks", None) or likes
        refs = list(refs) if refs else []
        
        if not refs:
            await message_to_edit.edit_text("💔 У тебя пока нет лайкнутых треков.")
            return
        
        total = len(refs)
        index = index % total
        
        track_id = refs[index].id
        track = client.tracks(track_id)[0]
        
        artists = ", ".join(a.name for a in track.artists)
        duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
        
        text = "❤️ <b>Твои лайкнутые треки</b>\n\n"
        text += f"Трек {index + 1} из {total}\n\n"
        text += f"<b>{track.title}</b>\n"
        text += f"🎤 {artists}\n"
        text += f"⏳ {duration}\n"
        text += f"💿 {track.albums[0].title if track.albums else 'Неизвестный альбом'}\n"
        
        kb = [
            [
                InlineKeyboardButton(text="◀️", callback_data=f"prev_liked:{index}"),
                InlineKeyboardButton(text="▶️", callback_data=f"next_liked:{index}")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ]
        
        await message_to_edit.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        
    except Exception as e:
        logger.error(f"Ошибка получения лайков: {e}")
        await message_to_edit.edit_text(f"✗ Ошибка: {e}")