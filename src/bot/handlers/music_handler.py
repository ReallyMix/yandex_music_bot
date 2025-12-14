from __future__ import annotations

import logging
from typing import Any, List, Optional

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command

from yandex_music import Client

from .start_handler import get_client, has_token, AUTH_URL, user_tokens
from ..ym_service import ym_service

router = Router()
logger = logging.getLogger(__name__)


# ========= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =========

def _effective_user_id_from_message(message: Message) -> int:
    """В message-хендлерах берём user_id из from_user, в крайнем случае — из chat.id."""
    if message.from_user and not message.from_user.is_bot:
        return message.from_user.id
    return message.chat.id


def require_auth(func):
    """Проверка авторизации для message-хендлеров."""

    async def wrapper(message: Message, *args, **kwargs):
        user_id = _effective_user_id_from_message(message)
        if not has_token(user_id):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔑 Авторизоваться", url=AUTH_URL)]
                ]
            )
            await message.answer(
                "❌ <b>Требуется авторизация!</b>\n\n"
                "Используй /auth или /settoken.",
                reply_markup=keyboard,
            )
            return
        return await func(message, *args, **kwargs)

    return wrapper


def _format_track_id_for_lyrics(track: Any) -> str:
    """Для get_song_lyrics лучше передавать track_id:album_id, если он есть."""
    tid = getattr(track, "id", None)
    albums = getattr(track, "albums", None) or []
    if tid and albums:
        aid = getattr(albums[0], "id", None)
        if aid:
            return f"{tid}:{aid}"
    return str(tid)


async def _get_account_uid(token: str, user_id: int) -> Optional[int]:
    """UID аккаунта через client.account_status()."""
    client = ym_service.get_client(token, user_id)
    if client is None:
        return None
    try:
        acc = client.account_status()
        if acc and getattr(acc, "account", None):
            return acc.account.uid
    except Exception as e:
        logger.error(f"Ошибка получения uid для {user_id}: {e}")
    return None


async def _get_playlist_tracks_by_kind(
    token: str, user_id: int, kind: int
) -> List[Any]:
    """
    Получить треки конкретного плейлиста по kind, не меняя services:
    используем Client и утилиты из helpers_mixin через ym_service.
    """
    client: Client | None = ym_service.get_client(token, user_id)
    if client is None:
        return []

    uid = await _get_account_uid(token, user_id)
    if uid is None:
        return []

    playlists = client.users_playlists(uid) or []
    target = next((pl for pl in playlists if getattr(pl, "kind", None) == kind), None)
    if target is None:
        return []

    track_refs = getattr(target, "tracks", None) or []
    direct_tracks: List[Any] = []
    missing_refs: List[Any] = []

    for ref in track_refs:
        tr = getattr(ref, "track", None)
        if tr is not None:
            direct_tracks.append(tr)
        else:
            missing_refs.append(ref)

    if not missing_refs:
        return direct_tracks

    ids: List[str] = []
    for ref in missing_refs:
        tid = ym_service._format_track_id(ref)  # type: ignore[attr-defined]
        if tid:
            ids.append(tid)

    fetched = ym_service._fetch_tracks(client, ids)  # type: ignore[attr-defined]
    return direct_tracks + [t for t in fetched if t is not None]


# ========= ВХОД ИЗ INLINE-КНОПОК =========

@router.callback_query(F.data == "open_music_menu")
async def open_music_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer()
    if not has_token(user_id):
        await callback.message.answer(
            "❌ <b>Требуется авторизация!</b>\n\nИспользуй /start и /auth."
        )
        return
    await _send_music_menu(callback.message)


@router.callback_query(F.data == "open_search")
async def open_search_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer()
    if not has_token(user_id):
        await callback.message.answer(
            "❌ <b>Требуется авторизация!</b>\n\nИспользуй /start и /auth."
        )
        return
    await _send_search_prompt(callback.message)


# ========= МЕНЮ =========

async def _send_music_menu(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Мои лайки", callback_data="show_likes"),
                InlineKeyboardButton(text="📋 Плейлисты", callback_data="show_playlists"),
            ],
            [
                InlineKeyboardButton(text="👤 Любимые артисты", callback_data="show_artists"),
                InlineKeyboardButton(text="💿 Альбомы", callback_data="show_albums"),
            ],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
        ]
    )
    await message.answer("🎵 <b>Моя музыка</b>\n\nВыбери раздел:", reply_markup=keyboard)


async def _send_search_prompt(message: Message) -> None:
    await message.answer(
        "🔍 <b>Поиск музыки</b>\n\n"
        "Отправь название трека, артиста или альбома.\n\n"
        "Примеры:\n"
        "• <code>Imagine Dragons</code>\n"
        "• <code>Believer</code>\n"
        "• <code>Night Visions</code>"
    )


@router.message(F.text == "🎵 Моя музыка")
@router.message(Command("mymusic"))
@require_auth
async def my_music_handler(message: Message):
    await _send_music_menu(message)


@router.message(F.text == "🔍 Поиск")
@router.message(Command("search"))
@require_auth
async def search_command(message: Message):
    await _send_search_prompt(message)


# ========= ЛАЙКИ =========

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
            text += f"   ⏱ {duration}\n\n"

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
        await status_msg.edit_text(f"❌ Ошибка: {e}")


# ========= ПЛЕЙЛИСТЫ =========

@router.callback_query(F.data == "show_playlists")
async def show_playlists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_playlists(callback.message, callback.from_user.id)


@router.message(F.text == "📋 Плейлисты")
@router.message(Command("playlists"))
@require_auth
async def playlists_command(message: Message):
    await show_playlists(message, _effective_user_id_from_message(message))


async def show_playlists(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Загружаю плейлисты...")

    token = user_tokens.get(user_id)
    if not token:
        await status_msg.edit_text("❌ Ошибка авторизации")
        return

    try:
        # services.YandexMusicService: асинхронный метод get_user_playlists [file:2]
        playlists = await ym_service.get_user_playlists(token, user_id)
        if not playlists:
            await status_msg.edit_text("📋 У тебя пока нет плейлистов.")
            return

        text = "📋 <b>Твои плейлисты</b>\n\n"
        text += f"Всего: {len(playlists)}\n\n"

        kb = []
        for i, pl in enumerate(playlists[:15], 1):
            title = pl.get("title") or "Без названия"
            count = pl.get("track_count", 0)
            desc = pl.get("description")
            kind = pl.get("kind")

            text += f"{i}. <b>{title}</b>\n"
            text += f"   🎵 {count} треков\n"
            if desc:
                d = desc if len(desc) <= 50 else desc[:50] + "..."
                text += f"   📝 {d}\n"
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
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    except Exception as e:
        logger.error(f"Ошибка получения плейлистов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")


# ========= ЛЮБИМЫЕ АРТИСТЫ =========

@router.callback_query(F.data == "show_artists")
async def show_artists_callback(callback: CallbackQuery):
    await callback.answer()
    await show_artists(callback.message, callback.from_user.id)


@router.message(F.text == "👤 Любимые артисты")
@router.message(Command("artists"))
@require_auth
async def artists_command(message: Message):
    await show_artists(message, _effective_user_id_from_message(message))


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

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка получения артистов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")


# ========= ЛЮБИМЫЕ АЛЬБОМЫ =========

@router.callback_query(F.data == "show_albums")
async def show_albums_callback(callback: CallbackQuery):
    await callback.answer()
    await show_albums(callback.message, callback.from_user.id)


@router.message(F.text == "💿 Альбомы")
@router.message(Command("albums"))
@require_auth
async def albums_command(message: Message):
    await show_albums(message, _effective_user_id_from_message(message))


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

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )

    except Exception as e:
        logger.error(f"Ошибка получения альбомов: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")


# ========= СТАТИСТИКА ЧЕРЕЗ services =========

@router.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: CallbackQuery):
    await callback.answer()
    await show_stats(callback.message, callback.from_user.id)


@router.message(Command("stats"))
@require_auth
async def stats_command(message: Message):
    await show_stats(message, _effective_user_id_from_message(message))


async def show_stats(message: Message, user_id: int):
    status_msg = await message.answer("⏳ Собираю статистику...")

    token = user_tokens.get(user_id)
    if not token:
        await status_msg.edit_text("❌ Ошибка авторизации")
        return

    try:
        # services.YandexMusicService: get_user_statistics [file:2]
        data = await ym_service.get_user_statistics(token, user_id)

        text = "📊 <b>Твоя статистика</b>\n\n"
        text += f"❤️ Лайкнутых треков: {data.get('liked_tracks_count', 0)}\n"
        text += f"🆕 Лайков за 30 дней: {data.get('recent_likes_last_month', 0)}\n"

        lm = data.get("listening_minutes", {}) or {}
        text += (
            f"⏱ Прослушивание: {lm.get('week', 0)} мин за неделю, "
            f"{lm.get('month', 0)} мин за месяц\n\n"
        )

        top_artists = data.get("top_artists") or []
        if top_artists:
            text += "👤 <b>Топ артистов:</b>\n"
            for i, item in enumerate(top_artists, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')} треков\n"
            text += "\n"

        top_genres_recent = data.get("top_genres_recent") or []
        if top_genres_recent:
            text += "🎧 <b>Жанры (недавние):</b>\n"
            for i, item in enumerate(top_genres_recent, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')}\n"
            text += "\n"

        top_genres_library = data.get("top_genres_library") or []
        if top_genres_library:
            text += "💿 <b>Жанры (библиотека):</b>\n"
            for i, item in enumerate(top_genres_library, 1):
                text += f"{i}. {item.get('name')} — {item.get('count')}\n"
            text += "\n"

        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_music")]
                ]
            ),
        )
    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {e}")


# ========= ПОИСК =========

@router.message(F.text.regexp(r"^[^/].+"))
@require_auth
async def search_handler(message: Message):
    user_id = _effective_user_id_from_message(message)
    query = message.text.strip()
    if len(query) < 2:
        return

    status_msg = await message.answer(f"🔍 Ищу: <b>{query}</b>...")

    try:
        client = get_client(user_id)
        if not client:
            await status_msg.edit_text("❌ Ошибка авторизации")
            return

        result = client.search(query, type_="track")
        if not result.tracks or not result.tracks.results:
            await status_msg.edit_text(
                f"❌ По запросу «<b>{query}</b>» ничего не найдено."
            )
            return

        tracks = result.tracks.results[:10]

        text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"
        text += f"Найдено: {result.tracks.total}\n"
        text += f"Показано: {len(tracks)}\n\n"

        kb = []
        for i, track in enumerate(tracks, 1):
            artists = ", ".join(a.name for a in track.artists)
            duration = f"{track.duration_ms // 60000}:{(track.duration_ms // 1000) % 60:02d}"
            text += f"{i}. <b>{track.title}</b>\n"
            text += f"   🎤 {artists}\n"
            text += f"   ⏱ {duration}\n\n"

            track_id = _format_track_id_for_lyrics(track)
            kb.append(
                [
                    InlineKeyboardButton(
                        text=f"📜 Текст #{i}",
                        callback_data=f"lyrics:{track_id}",
                    )
                ]
            )

        await status_msg.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )

    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await status_msg.edit_text(f"❌ Ошибка поиска: {e}")


# ========= ТЕКСТ ПЕСНИ ЧЕРЕЗ services =========

@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    token = user_tokens.get(user_id)
    if not token:
        await callback.message.answer("❌ Нет токена. Используй /start и /auth.")
        return

    track_id = callback.data.split(":", 1)[1]

    try:
        # services.YandexMusicService: get_song_lyrics(token, user_id, track_id) [file:2]
        lyrics = await ym_service.get_song_lyrics(token, user_id, track_id)
        if not lyrics:
            await callback.message.answer(
                "❌ Текст для этого трека не найден (в API он есть не у всех треков)."
            )
            return

        chunk = 3500
        for i in range(0, len(lyrics), chunk):
            await callback.message.answer(
                "📜 <b>Текст песни</b>:\n\n" + lyrics[i : i + chunk]
            )

    except Exception as e:
        logger.error(f"Ошибка получения текста песни: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")


# ========= ОТКРЫТИЕ ПЛЕЙЛИСТА =========

@router.callback_query(F.data.startswith("playlist:"))
async def playlist_open_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    token = user_tokens.get(user_id)
    if not token:
        await callback.message.answer("❌ Нет токена. Используй /start и /auth.")
        return

    try:
        kind = int(callback.data.split(":", 1)[1])
        tracks = await _get_playlist_tracks_by_kind(token, user_id, kind)
        if not tracks:
            await callback.message.answer(
                "❌ Не удалось получить треки этого плейлиста."
            )
            return

        text = "📂 <b>Треки плейлиста</b>\n\n"
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
                text += f"   ⏱ {dur}\n"
            text += "\n"

        await callback.message.answer(text)

    except Exception as e:
        logger.error(f"Ошибка открытия плейлиста: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")


# ========= НАЗАД В МЕНЮ МУЗЫКИ =========

@router.callback_query(F.data == "back_to_music")
async def back_to_music_callback(callback: CallbackQuery):
    await callback.answer()
    if not has_token(callback.from_user.id):
        await callback.message.answer("❌ Требуется авторизация. Используй /start.")
        return
    await _send_music_menu(callback.message)

