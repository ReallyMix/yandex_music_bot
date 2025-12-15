import logging
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps

from ..storage import user_tokens
from ..services import ym_service

logger = logging.getLogger(__name__)

CLIENT_ID = "23cabbbdc6cd418abb4b39c32c41195d"
AUTH_URL = f"https://oauth.yandex.ru/authorize?response_type=token&client_id={CLIENT_ID}"

def _effective_user_id_from_message(message: Message) -> int:
    """Получение user_id из сообщения"""
    if message.from_user and not message.from_user.is_bot:
        return message.from_user.id
    return message.chat.id

def require_auth(func):
    """Декоратор проверки авторизации"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user_id = _effective_user_id_from_message(message)
        if not has_token(user_id):
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📌 Авторизоваться", url=AUTH_URL)]
                ]
            )
            await message.answer(
                "✗ <b>Требуется авторизация!</b>\nИспользуй /auth или /settoken.",
                reply_markup=keyboard,
            )
            return
        return await func(message, *args, **kwargs)
    return wrapper

def _format_track_id_for_lyrics(track) -> str:
    """Форматирование ID трека для получения текста"""
    tid = getattr(track, "id", None)
    albums = getattr(track, "albums", None) or []
    if tid and albums:
        aid = getattr(albums[0], "id", None)
        if aid:
            return f"{tid}:{aid}"
    return str(tid)

def has_token(user_id: int) -> bool:
    """Проверка наличия токена"""
    return user_id in user_tokens

def get_client(user_id: int):
    """Получение клиента Яндекс.Музыки"""
    token = user_tokens.get(user_id)
    if not token:
        return None
    return ym_service.get_client(token, user_id)

async def _get_account_uid(token: str, user_id: int):
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
        raise e
    return None

async def _get_playlist_tracks_by_kind(token: str, user_id: int, kind: int):
    """
    Получить треки конкретного плейлиста по kind.
    """
    client = ym_service.get_client(token, user_id)
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
    direct_tracks = []
    missing_refs = []

    for ref in track_refs:
        tr = getattr(ref, "track", None)
        if tr is not None:
            direct_tracks.append(tr)
        else:
            missing_refs.append(ref)

    if not missing_refs:
        return direct_tracks

    ids = []
    for ref in missing_refs:
        tid = ym_service._format_track_id(ref)  # type: ignore[attr-defined]
        if tid:
            ids.append(tid)

    fetched = ym_service._fetch_tracks(client, ids)  # type: ignore[attr-defined]
    return direct_tracks + [t for t in fetched if t is not None]