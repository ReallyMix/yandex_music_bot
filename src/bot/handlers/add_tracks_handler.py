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


class AddTracksStates(StatesGroup):
    waiting_for_playlist_title = State()
    waiting_for_track_names = State()


@router.callback_query(F.data == "menu_add_tracks")
async def add_tracks_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user_id = callback.from_user.id
    token = get_token(user_id)

    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return

    await state.set_state(AddTracksStates.waiting_for_playlist_title)
    await callback.message.edit_text(
        "🎼 <b>Добавить треки в плейлист</b>\n\n"
        "Шаг 1: Отправьте название плейлиста.\n\n"
        "Если плейлист не существует, он будет создан.",
        reply_markup=get_back_button()
    )


@router.message(AddTracksStates.waiting_for_playlist_title)
async def receive_playlist_title_for_tracks(message: Message, state: FSMContext):
    playlist_title = (message.text or "").strip()

    if not playlist_title:
        await message.answer("❌ Пустое название плейлиста.")
        return

    await state.update_data(playlist_title=playlist_title)
    await state.set_state(AddTracksStates.waiting_for_track_names)

    await message.answer(
        f"📁 Плейлист: <b>{playlist_title}</b>\n\n"
        "Шаг 2: Отправьте названия треков.\n\n"
        "Можно писать в свободной форме:\n"
        "• <code>Imagine Dragons Believer</code>\n"
        "• <code>The Weeknd - Blinding Lights</code>\n\n"
        "Формат ввода:\n"
        "• каждый трек с новой строки\n"
        "• или через запятую",
        reply_markup=get_back_button()
    )


@router.message(AddTracksStates.waiting_for_track_names)
async def receive_track_names(message: Message, state: FSMContext):
    user_id = message.from_user.id
    token = get_token(user_id)

    data = await state.get_data()
    playlist_title = data.get("playlist_title")

    text = (message.text or "").strip()

    if "\n" in text:
        track_names = [line.strip() for line in text.split("\n") if line.strip()]
    elif "," in text:
        track_names = [name.strip() for name in text.split(",") if name.strip()]
    else:
        track_names = [text] if text else []

    if not track_names:
        await message.answer(
            "❌ Не удалось распознать треки.\n\n"
            "Попробуйте:\n"
            "• Каждый трек с новой строки\n"
            "• Или через запятую"
        )
        return

    if len(track_names) > 50:
        await message.answer(
            f"❌ Слишком много треков ({len(track_names)}).\n"
            "Максимум: 50 за раз."
        )
        return

    status_msg = await message.answer(
        f"🎼 Добавляю {len(track_names)} трек(ов) в плейлист <b>{playlist_title}</b>...",
        reply_markup=get_back_button()
    )

    try:
        result = await ym_service.add_tracks_by_name(
            token,
            user_id,
            playlist_title,
            track_names,
        )

        added = result.get("added", [])
        failed = result.get("failed", [])

        text_resp = (
            f"✅ <b>Готово!</b>\n\n"
            f"📁 Плейлист: <b>{playlist_title}</b>\n"
            f"➕ Добавлено: {len(added)}\n"
            f"❌ Не добавлено: {len(failed)}\n"
        )

        if added:
            text_resp += "\n<b>Добавленные треки:</b>\n"
            for item in added[:10]:
                text_resp += f"• {item['title']}\n"
            if len(added) > 10:
                text_resp += f"... и ещё {len(added) - 10}\n"

        if failed:
            text_resp += "\n<b>Не удалось добавить:</b>\n"
            for item in failed[:10]:
                text_resp += f"• {item['query']}\n"
            if len(failed) > 10:
                text_resp += f"... и ещё {len(failed) - 10}\n"

        await status_msg.edit_text(text_resp, reply_markup=get_back_button())
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка добавления треков: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ <b>Ошибка добавления треков</b>\n\n"
            f"<code>{str(e)[:200]}</code>",
            reply_markup=get_back_button()
        )
        await state.clear()
