from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import logging

from yandex_music import Client

from .start_handler import get_client, has_token, AUTH_URL

router = Router()
logger = logging.getLogger(__name__)


def require_auth(func):
    """Декоратор для проверки авторизации"""
    async def wrapper(message: Message, *args, **kwargs):
        if not has_token(message.from_user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Авторизоваться", url=AUTH_URL)]
            ])
            await message.answer(
                "❌ <b>Требуется авторизация!</b>\n\n"
                "Используй /auth или /settoken.",
                reply_markup=keyboard
            )
            return
        return await func(message, *args, **kwargs)
    return wrapper


@router.callback_query(F.data == "open_music_menu")
async def open_music_menu_callback(callback: CallbackQuery):
    """Открыть меню «Моя музыка» из инлайн‑кнопки"""
    await callback.answer()
    await my_music_handler(callback.message)


@router.callback_query(F.data == "open_search")
async def open_search_callback(callback: CallbackQuery):
    """Открыть поиск из инлайн‑кнопки"""
    await callback.answer()
    await search_command(callback.message)


@router.message(F.text == "🎵 Моя музыка")
@router.message(Command("mymusic"))
@require_auth
async def my_music_handler(message: Message):
    """Главное меню музыки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Мои лайки", callback_data="show_likes"),
            InlineKeyboardButton(text="📋 Плейлисты", callback_data="show_playlists")
        ],
        [
            InlineKeyboardButton(text="👤 Любимые артисты", callback_data="show_artists"),
            InlineKeyboardButton(text="💿 Альбомы", callback_data="show_albums")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
        ]
    ])

    await message.answer(
        "🎵 <b>Моя музыка</b>\n\n"
        "Выбери раздел:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "show_likes")
async def show_likes_callback(callback: CallbackQuery):
    await callback.answer()
    await show_likes(callback.message, callback.from_user.id)


@router.message(F.text == "❤️ Мои лайки")
@router.message(Command("likes"))
@require_auth
async def likes_command(message: Message):
    await show_likes(message, message.from_user.id)


async def show_likes(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю лайкнутые треки...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        likes = client.users_likes_tracks()
        if not likes:
            await status_msg.edit_text("💔 У тебя пока нет лайкнутых треков.")
            return

        tracks_to_show = likes[:10]
        track_ids = [track.id for track in tracks_to_show]
        tracks = client.tracks(track_ids)

        text = "❤️ <b>Твои лайкнутые треки</b>\n\n"
        text += f"Всего: {len(likes)}\n"
        text += f"Показано: {len(tracks_to_show)}\n\n"

        for i, track in enumerate(tracks, 1):
            artists = ", ".join(artist.name for artist in track.artists)
            duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
            text += f"{i}. <b>{track.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   ⏱ {duration}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ])

        await status_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения лайков: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "show_playlists")
async def show_playlists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_playlists(callback.message, callback.from_user.id)


@router.message(F.text == "📋 Плейлисты")
@router.message(Command("playlists"))
@require_auth
async def playlists_command(message: Message):
    await show_playlists(message, message.from_user.id)


async def show_playlists(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю плейлисты...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        playlists = client.users_playlists_list()
        if not playlists:
            await status_msg.edit_text("📋 У тебя пока нет плейлистов.")
            return

        text = "📋 <b>Твои плейлисты</b>\n\n"
        text += f"Всего: {len(playlists)}\n\n"

        for i, playlist in enumerate(playlists[:15], 1):
            count = playlist.track_count or 0
            text += f"{i}. <b>{playlist.title}</b>\n"
            text += f"   🎵 {count} треков\n"
            if playlist.description:
                desc = playlist.description
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                text += f"   📝 {desc}\n"
            text += "\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ])

        await status_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения плейлистов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "show_artists")
async def show_artists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_artists(callback.message, callback.from_user.id)


@router.message(F.text == "👤 Любимые артисты")
@router.message(Command("artists"))
@require_auth
async def artists_command(message: Message):
    await show_artists(message, message.from_user.id)


async def show_artists(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю любимых артистов...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        artists = client.users_likes_artists()
        if not artists:
            await status_msg.edit_text("👤 У тебя пока нет любимых артистов.")
            return

        text = "👤 <b>Твои любимые артисты</b>\n\n"
        text += f"Всего: {len(artists)}\n\n"

        for i, liked in enumerate(artists[:15], 1):
            art = liked.artist
            text += f"{i}. <b>{art.name}</b>\n"
            if art.genres:
                genres = ", ".join(art.genres[:3])
                text += f"   🎸 {genres}\n"
            text += "\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ])

        await status_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения артистов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "show_albums")
async def show_albums_callback(callback: CallbackQuery):
    await callback.answer()
    await show_albums(callback.message, callback.from_user.id)


@router.message(F.text == "💿 Альбомы")
@router.message(Command("albums"))
@require_auth
async def albums_command(message: Message):
    await show_albums(message, message.from_user.id)


async def show_albums(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю любимые альбомы...")

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

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ])

        await status_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения альбомов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: CallbackQuery):
    await callback.answer()
    await show_stats(callback.message, callback.from_user.id)


@router.message(Command("stats"))
@require_auth
async def stats_command(message: Message):
    await show_stats(message, message.from_user.id)


async def show_stats(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Собираю статистику...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        likes = client.users_likes_tracks()
        playlists = client.users_playlists_list()
        artists = client.users_likes_artists()
        albums = client.users_likes_albums()

        text = "📊 <b>Твоя статистика</b>\n\n"
        text += f"❤️ Лайкнутых треков: {len(likes) if likes else 0}\n"
        text += f"📋 Плейлистов: {len(playlists) if playlists else 0}\n"
        text += f"👤 Любимых артистов: {len(artists) if artists else 0}\n"
        text += f"💿 Любимых альбомов: {len(albums) if albums else 0}\n\n"

        if likes:
            total_ms = sum(t.track.duration_ms for t in likes[:100] if t.track)
            hours = total_ms // (1000 * 60 * 60)
            minutes = (total_ms // (1000 * 60)) % 60
            text += f"⏱ Примерное время первых 100 лайков: {hours}ч {minutes}м\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
        ])

        await status_msg.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")


@router.message(F.text == "🔍 Поиск")
@router.message(Command("search"))
@require_auth
async def search_command(message: Message):
    await message.answer(
        "🔍 <b>Поиск музыки</b>\n\n"
        "Отправь название трека, артиста или альбома.\n\n"
        "Примеры:\n"
        "• <code>Imagine Dragons</code>\n"
        "• <code>Believer</code>\n"
        "• <code>Night Visions</code>"
    )


@router.message(F.text.regexp(r'^[^/].+'))
@require_auth
async def search_handler(message: Message):
    query = message.text.strip()
    if len(query) < 2:
        return

    status_msg = await message.answer(f"🔍 Ищу: <b>{query}</b>...")

    try:
        client = get_client(message.from_user.id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        result = client.search(query, type_="track")
        if not result.tracks or not result.tracks.results:
            await status_msg.edit_text(f"❌ По запросу «<b>{query}</b>» ничего не найдено.")
            return

        tracks = result.tracks.results[:10]

        text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"
        text += f"Найдено: {result.tracks.total}\n"
        text += f"Показано: {len(tracks)}\n\n"

        for i, track in enumerate(tracks, 1):
            artists = ", ".join(a.name for a in track.artists)
            duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
            text += f"{i}. <b>{track.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   ⏱ {duration}\n\n"

        await status_msg.edit_text(text)

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await status_msg.edit_text(f"❌ Ошибка поиска: {str(e)}")


@router.callback_query(F.data == "back_to_music")
async def back_to_music_callback(callback: CallbackQuery):
    await callback.answer()
    await my_music_handler(callback.message)
