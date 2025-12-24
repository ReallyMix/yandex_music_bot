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


class CreatePlaylistStates(StatesGroup):
    waiting_for_title = State()


@router.callback_query(F.data == "menu_create_playlist")
async def create_playlist_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    user_id = callback.from_user.id
    token = get_token(user_id)

    if not token:
        await callback.message.edit_text(
            "❌ Вы не авторизованы. Используйте /auth",
            reply_markup=get_back_button()
        )
        return

    await state.set_state(CreatePlaylistStates.waiting_for_title)
    await callback.message.edit_text(
        "➕ <b>Создать плейлист</b>\n\n"
        "Отправьте название нового плейлиста.",
        reply_markup=get_back_button()
    )


@router.message(CreatePlaylistStates.waiting_for_title)
async def receive_playlist_title(message: Message, state: FSMContext):
    user_id = message.from_user.id
    token = get_token(user_id)
    title = message.text.strip()

    if len(title) > 100:
        await message.answer(
            "❌ Название слишком длинное. Максимум 100 символов.\n"
            "Попробуйте ещё раз."
        )
        return

    status_msg = await message.answer(f"➕ Создаю плейлист '{title}'...")

    try:
        result = await ym_service.create_playlist(token, user_id, title)

        if result:
            await status_msg.edit_text(
                f"✅ <b>Плейлист создан!</b>\n\n"
                f"📁 Название: <b>{result['title']}</b>",
                reply_markup=get_back_button()
            )
        else:
            await status_msg.edit_text(
                "❌ Не удалось создать плейлист. Попробуйте позже.",
                reply_markup=get_back_button()
            )

        await state.clear()

    except Exception:
        logger.exception("Ошибка создания плейлиста")
        
        await status_msg.edit_text(
            "❌ Не получилось создать\n"
            "Попробуйте ещё раз",
            reply_markup=get_back_button()
        )
        await state.clear()
