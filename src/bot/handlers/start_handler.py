import logging
import re
from urllib.parse import unquote
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from yandex_music import Client

from ...database.storage import set_token, get_token, has_token, remove_token
from ..keyboards.main_menu import get_main_menu_keyboard, get_auth_keyboard

router = Router()
logger = logging.getLogger(__name__)

AUTH_URL = "https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d"

class AuthStates(StatesGroup):
    waiting_for_token = State()

@router.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    
    if has_token(user_id):
        await message.answer(
            "👋 С возвращением!\n\n"
            "Вы уже авторизованы. Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Добро пожаловать в Yandex Music Bot!</b>\n\n"
            "Этот бот поможет вам управлять вашей музыкой в Яндекс.Музыке.\n\n"
            "<b>Возможности:</b>\n"
            "📁 Просмотр плейлистов\n"
            "🎵 Получение текста песен\n"
            "➕ Создание плейлистов\n"
            "🎼 Добавление треков\n"
            "❤️ Лайки треков\n"
            "📊 Статистика прослушивания\n\n"
            "Для начала работы нужно авторизоваться.\n"
            "Используйте команду /auth"
        )

@router.message(Command("auth"))
async def auth_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if has_token(user_id):
        await message.answer(
            "✅ Вы уже авторизованы!\n\n"
            "Для выхода используйте /logout",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    args = message.text.split(maxsplit=1)
    
    if len(args) >= 2:
        raw_token = args[1].strip()
        await process_token(message, raw_token, state)
    else:
        await state.set_state(AuthStates.waiting_for_token)
        await message.answer(
            "🔑 <b>Авторизация</b>\n\n"
            "1. Нажмите кнопку 'Получить токен' ниже\n"
            "2. Войдите в аккаунт Яндекс\n"
            "3. Разрешите доступ приложению\n"
            "4. Скопируйте URL из адресной строки\n"
            "5. Отправьте его боту\n\n"
            "URL будет выглядеть так:\n"
            "<code>https://music.yandex.ru/#access_token=...</code>\n\n"
            "Отправьте весь URL или только токен.",
            reply_markup=get_auth_keyboard(AUTH_URL)
        )

@router.message(Command("logout"))
async def logout_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not has_token(user_id):
        await message.answer(
            "❌ Вы еще не авторизованы.\n\n"
            "Используйте /auth для входа."
        )
        return
    
    remove_token(user_id)
    await state.clear()
    
    logger.info(f"Пользователь {user_id} разлогинился")
    
    await message.answer(
        "👋 <b>Вы вышли из аккаунта</b>\n\n"
        "Ваш токен удален.\n"
        "Все ваши данные остались в Яндекс.Музыке.\n\n"
        "Для повторной авторизации используйте /auth\n"
        "Справка: /help"
    )

@router.callback_query(F.data == "auth_help")
async def auth_help_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📘 <b>Подробная инструкция</b>\n\n"
        "1️⃣ Перейдите по ссылке (кнопка 'Получить токен')\n"
        "2️⃣ Войдите в свой аккаунт Яндекс\n"
        "3️⃣ Нажмите 'Разрешить'\n"
        "4️⃣ Вас перенаправит на music.yandex.ru\n"
        "5️⃣ В адресной строке будет длинный URL вида:\n\n"
        "<code>https://music.yandex.ru/#access_token=ТОКЕН&token_type=bearer...</code>\n\n"
        "6️⃣ Скопируйте ВЕСЬ этот URL\n"
        "7️⃣ Отправьте его мне\n\n"
        "Бот автоматически вытащит токен из URL."
    )

@router.message(AuthStates.waiting_for_token)
async def receive_token(message: Message, state: FSMContext):
    await process_token(message, message.text.strip(), state)

async def process_token(message: Message, raw_string: str, state: FSMContext):
    status_msg = await message.answer("🔍 Проверяю токен...")
    
    token = extract_token(raw_string)
    
    if not token:
        await status_msg.edit_text(
            "❌ Не удалось найти токен в вашем сообщении.\n\n"
            "Отправьте URL после авторизации или только токен.\n"
            "Попробуйте ещё раз."
        )
        return
    
    try:
        client = Client(token).init()
        account = client.account_status()
        
        set_token(message.from_user.id, token)
        await state.clear()
        
        logger.info(f"Токен установлен для пользователя {message.from_user.id}")
        
        await status_msg.edit_text(
            f"✅ <b>Авторизация успешна!</b>\n\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс ✅' if account.plus else 'Без подписки'}\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка проверки токена: {e}")
        await status_msg.edit_text(
            "❌ <b>Авторизация не выполнена</b>\n\n"
            "Токен недействителен или истек.\n\n"
            "Пожалуйста, получите новый токен\n"
            "через команду /auth и попробуйте снова."
        )

def extract_token(raw_string: str) -> str | None:
    clean_string = ''.join(raw_string.split())
    
    patterns = [
        r'access_token=([A-Za-z0-9_-]{30,})',
        r'access_token%3D([A-Za-z0-9_-]{30,})',
        r'access_token%253D([A-Za-z0-9_-]{30,})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_string)
        if match:
            return match.group(1)
    
    try:
        decoded = unquote(clean_string)
        for pattern in patterns[:2]:
            match = re.search(pattern, decoded)
            if match:
                return match.group(1)
    except:
        pass
    
    direct_match = re.search(r'\b(y0_[A-Za-z0-9_-]{30,})\b', clean_string)
    if direct_match:
        return direct_match.group(1)
    
    fallback = re.search(r'(y0_[A-Za-z0-9_-]{30,})|(AQ[A-Za-z0-9_-]{30,})', clean_string)
    if fallback:
        return fallback.group(1) or fallback.group(2)
    
    return None

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    
    if not has_token(user_id):
        await callback.message.edit_text(
            "❌ Вы не авторизованы.\n\n"
            "Используйте /auth для входа."
        )
        return
    
    await callback.message.edit_text(
        "📱 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )