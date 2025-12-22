import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from typing import Any, Dict, List

from ...database.storage import get_token
from ..services import ym_service
from ..keyboards.main_menu import get_back_button, get_playlists_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "menu_playlists")
async def playlists_callback(callback: CallbackQuery):
    await show_playlists_page(callback, page=0)

@router.callback_query(F.data.startswith("playlists:"))
async def playlists_page_callback(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) >= 3:
        try:
            page = int(parts[2])
        except ValueError:
            page = 0
        await show_playlists_page(callback, page=page)

async def show_playlists_page(callback: CallbackQuery, page: int = 0):
    user_id = callback.from_user.id
    token = get_token(user_id)

    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return

    if page == 0:
        await callback.message.edit_text("📁 Загружаю плейлисты...")

    try:
        playlists = await ym_service.get_user_playlists(token, user_id)

        if not playlists:
            await callback.message.edit_text(
                "📁 <b>Плейлисты</b>\n\n"
                "У вас пока нет плейлистов.\n\n"
                "💡 Создайте первый плейлист через меню!",
                reply_markup=get_back_button()
            )
            return

        def _modified_key(pl: Dict[str, Any]) -> str:
            return pl.get("modified") or ""

        playlists_sorted = sorted(playlists, key=_modified_key, reverse=True)

        per_page = 5
        total_playlists = len(playlists_sorted)
        total_pages = (total_playlists + per_page - 1) // per_page

        if page < 0:
            page = 0
        elif page >= total_pages:
            page = total_pages - 1

        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total_playlists)
        page_playlists = playlists_sorted[start_idx:end_idx]

        text = "📁 <b>Ваши плейлисты</b>\n"
        text += f"Всего: {total_playlists} • Страница {page + 1}/{total_pages}\n\n"

        for i, pl in enumerate(page_playlists, start=start_idx + 1):
            title = pl.get("title") or "Без названия"
            track_count = pl.get("track_count", 0)

            kind = pl.get("kind")
            if kind == 3:
                icon = "❤️"
            elif title.lower() in ["избранное", "favorites", "liked"]:
                icon = "⭐"
            else:
                icon = "📁"

            text += f"{icon} <b>{title}</b>\n"
            text += (
                f"   └ {track_count} "
                f"{'трек' if track_count == 1 else 'треков'}\n"
            )

            owner_login = pl.get("owner_login")
            if owner_login and str(owner_login) != str(user_id):
                text += f"   👤 by @{owner_login}\n"

            text += "\n"

        logger.info(f"Показана страница {page + 1}/{total_pages} плейлистов пользователя {user_id}")

        keyboard = get_playlists_keyboard(page, total_pages)
        await callback.message.edit_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка получения плейлистов: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Ошибка</b>\n\n"
            "Не удалось загрузить плейлисты.\n\n"
            f"Описание: <code>{str(e)[:150]}</code>\n\n"
            "Попробуйте:\n"
            "• Переавторизоваться (/logout → /auth)\n"
            "• Повторить попытку позже",
            reply_markup=get_back_button()
        )