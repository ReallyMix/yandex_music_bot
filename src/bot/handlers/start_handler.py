from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from yandex_music import Client
import logging
import re
from urllib.parse import unquote

from ..keyboards.main_menu import get_main_menu

router = Router()
logger = logging.getLogger(__name__)

class AuthStates(StatesGroup):
    waiting_for_url = State()

# Хранилище токенов в памяти {telegram_id: token}
user_tokens: dict[int, str] = {}

CLIENT_ID = "23cabbbdc6cd418abb4b39c32c41195d"
AUTH_URL = f"https://oauth.yandex.ru/authorize?response_type=token&client_id={CLIENT_ID}"


@router.message(Command("start"))
async def start_handler(message: Message):
    """Старт бота"""
    user_id = message.from_user.id
    has_token = user_id in user_tokens

    if has_token:
        await message.answer(
            "👋 <b>С возвращением!</b>\n\n"
            "✅ Ты уже авторизован.\n\n"
            "Используй кнопки меню ниже для работы с Яндекс.Музыкой:",
            reply_markup=get_main_menu()
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔑 Получить токен Яндекс.Музыки",
            url=AUTH_URL
        )],
        [InlineKeyboardButton(
            text="📝 Инструкция по получению токена",
            callback_data="show_instructions"
        )]
    ])

    await message.answer(
        "👋 <b>Добро пожаловать в бота для Яндекс.Музыки!</b>\n\n"
        "❌ Токен не установлен.\n\n"
        "<b>Как начать:</b>\n"
        "1. Нажми кнопку «🔑 Получить токен».\n"
        "2. Войди в Яндекс и дай доступ.\n"
        "3. Скопируй строку с токеном из браузера.\n"
        "4. Отправь её через /auth.\n\n"
        "<i>Если токен уже есть — можно сразу использовать /settoken.</i>",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "show_instructions")
async def show_instructions(callback: CallbackQuery):
    """Подробная инструкция по получению токена (упрощённая)"""
    await callback.message.answer(
        "📝 <b>Как получить токен</b>\n\n"
        "<b>Через браузер на ПК</b>\n"
        "1️⃣ Нажми «🔑 Получить токен» или открой ссылку:\n"
        f"<code>{AUTH_URL}</code>\n"
        "2️⃣ Войди в Яндекс и дай доступ Яндекс.Музыке.\n"
        "3️⃣ После входа адрес станет вида:\n"
        "<code>https://music.yandex.ru/#access_token=ТОКЕН&token_type=bearer...</code>\n"
        "4️⃣ Скопируй этот адрес целиком <b>или</b> любой текст, где есть <code>access_token=...</code>\n"
        "   (подойдёт <code>#access_token=...</code>, <code>access_token%3D...</code> или просто сам токен).\n"
        "5️⃣ Отправь строку в бота через:\n"
        "   • <code>/auth ВСТАВЬ_СТРОКУ</code>  или\n"
        "   • команду <code>/auth</code>, а затем отдельным сообщением вставь строку.\n"
        "   Бот сам вырежет токен из этой строки.\n\n"
        "<b>На телефоне (iOS / Android)</b>\n"
        "• Открывай ссылку авторизации <b>в Chrome или обычном браузере</b>,\n"
        "  а не во встроенном браузере Telegram, чтобы не перебрасывало в приложение Яндекс.Музыки [web:33].\n"
        "• После входа скопируй адрес страницы или любой текст, где есть <code>access_token=...</code>,\n"
        "  и отправь его в /auth — бот сам вытащит токен.\n\n"
        "💡 <b>Важно:</b> <code>/auth</code> не требует «чистого» токена.\n"
        "Достаточно любой строки, внутри которой он есть.",
        disable_web_page_preview=True
    )
    await callback.answer()


@router.message(Command("auth"))
async def auth_command(message: Message, state: FSMContext):
    """Команда для обработки сырой строки с токеном"""
    args = message.text.split(maxsplit=1)

    if len(args) >= 2:
        raw_string = args[1].strip()
        await process_raw_string(message, raw_string)
    else:
        await state.set_state(AuthStates.waiting_for_url)
        await message.answer(
            "📋 <b>Отправь строку с токеном</b>\n\n"
            "Подойдёт любой вариант:\n"
            "• полный URL из адресной строки после логина,\n"
            "• любой текст, где внутри есть <code>access_token=...</code>\n"
            "  или токен, начинающийся на <code>y0_</code> / <code>AQ</code>.\n\n"
            "Бот сам вырежет нужный кусок.\n\n"
            "Для отмены — /cancel."
        )


@router.message(AuthStates.waiting_for_url)
async def process_auth_url(message: Message, state: FSMContext):
    """Получили строку после /auth"""
    await state.clear()
    await process_raw_string(message, message.text.strip())


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    if await state.get_state() is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")


async def process_raw_string(message: Message, raw_string: str):
    """Обработка сырой строки, извлечение и проверка токена"""
    status_msg = await message.answer("🔍 Ищу токен в строке...")

    token = extract_token_from_raw(raw_string)

    if not token:
        await status_msg.edit_text(
            "❌ <b>Токен не найден.</b>\n\n"
            "Убедись, что в строке есть кусок вида <code>access_token=...</code>\n"
            "или токен, начинающийся на <code>y0_</code> / <code>AQ</code>.\n\n"
            "Попробуй ещё раз: /auth."
        )
        return

    await status_msg.edit_text("✅ Токен найден.\n⏳ Проверяю валидность...")

    try:
        client = Client(token).init()
        account = client.account_status()

        user_tokens[message.from_user.id] = token
        logger.info(f"Токен установлен для пользователя {message.from_user.id}")

        inline_menu = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎵 Моя музыка", callback_data="open_music_menu"),
                InlineKeyboardButton(text="🔍 Поиск", callback_data="open_search")
            ],
            [
                InlineKeyboardButton(text="❤️ Лайки", callback_data="show_likes"),
                InlineKeyboardButton(text="📋 Плейлисты", callback_data="show_playlists")
            ]
        ])

        await status_msg.edit_text(
            "✅ <b>Авторизация успешна!</b>\n\n"
            f"🔑 Токен: <code>{token[:20]}...{token[-10:]}</code>\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс ✨' if account.plus else 'Без подписки'}\n"
            "🎵 Статус: Активен.\n\n"
            "👇 Выбери, что открыть:",
            reply_markup=inline_menu
        )

    except Exception as e:
        logger.error(f"Ошибка валидации токена: {e}")
        await status_msg.edit_text(
            "❌ <b>Найденный токен не сработал.</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуй получить токен ещё раз и отправить другую строку через /auth."
        )


@router.message(Command("settoken"))
async def settoken_command(message: Message):
    """Установка токена, если пользователь присылает его вручную"""
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверный формат.</b>\n\n"
            "Используй: <code>/settoken ВАШ_ТОКЕН_ИЛИ_СТРОКА</code>\n\n"
            "Можно прислать:\n"
            "• чистый токен (начинается с <code>y0_</code> или <code>AQ</code>),\n"
            "• полный URL с <code>#access_token=...</code>,\n"
            "• строку с <code>access_token%3D...</code>.\n\n"
            "Но проще использовать /auth — он работает с любыми строками."
        )
        return

    token_input = args[1].strip()
    token = None

    if 'access_token=' in token_input:
        match = re.search(r'access_token=([^&\s]+)', token_input)
        if match:
            token = match.group(1)
    elif 'access_token%3D' in token_input:
        decoded = unquote(token_input)
        match = re.search(r'access_token=([^&\s]+)', decoded)
        if match:
            token = match.group(1)
    elif re.match(r'^(y0_|AQ)[A-Za-z0-9_-]{30,}$', token_input):
        token = token_input
    else:
        match = re.search(r'(y0_[A-Za-z0-9_-]{30,}|AQ[A-Za-z0-9_-]{30,})', token_input)
        if match:
            token = match.group(1)

    if not token:
        await message.answer(
            "❌ <b>Не удалось вытащить токен.</b>\n\n"
            "Проверь, что в тексте есть токен или используй /auth — он проще."
        )
        return

    status_msg = await message.answer("⏳ Проверяю токен...")

    try:
        client = Client(token).init()
        account = client.account_status()

        user_tokens[message.from_user.id] = token
        logger.info(f"Токен установлен для пользователя {message.from_user.id}")

        inline_menu = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎵 Моя музыка", callback_data="open_music_menu"),
                InlineKeyboardButton(text="🔍 Поиск", callback_data="open_search")
            ],
            [
                InlineKeyboardButton(text="❤️ Лайки", callback_data="show_likes"),
                InlineKeyboardButton(text="📋 Плейлисты", callback_data="show_playlists")
            ]
        ])

        await status_msg.edit_text(
            "✅ <b>Авторизация успешна!</b>\n\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс ✨' if account.plus else 'Без подписки'}\n"
            "🎵 Статус: Активен.\n\n"
            "👇 Выбери, что открыть:",
            reply_markup=inline_menu
        )

    except Exception as e:
        logger.error(f"Ошибка валидации токена: {e}")
        await status_msg.edit_text(
            "❌ <b>Токен не прошёл проверку.</b>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуй получить новый токен и отправить его снова."
        )


@router.message(Command("check"))
async def check_command(message: Message):
    """Проверка сохранённого токена"""
    user_id = message.from_user.id
    token = user_tokens.get(user_id)

    if not token:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Получить токен", url=AUTH_URL)]
        ])
        await message.answer(
            "❌ Токен не установлен.\n\n"
            "Используй /auth или /settoken для авторизации.",
            reply_markup=keyboard
        )
        return

    try:
        client = Client(token).init()
        account = client.account_status()

        await message.answer(
            "✅ <b>Токен действителен.</b>\n\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс' if account.plus else 'Без подписки'}"
        )

    except Exception as e:
        logger.error(f"Ошибка проверки токена: {e}")
        user_tokens.pop(user_id, None)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Получить новый токен", url=AUTH_URL)]
        ])

        await message.answer(
            "❌ Токен недействителен или истёк.\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Нужно получить новый токен и снова выполнить /auth.",
            reply_markup=keyboard
        )


@router.message(Command("logout"))
async def logout_command(message: Message):
    """Удаление токена"""
    user_id = message.from_user.id

    if user_id in user_tokens:
        user_tokens.pop(user_id)
        logger.info(f"Токен удалён для пользователя {user_id}")
        await message.answer(
            "✅ Токен удалён.\n\n"
            "Для новой авторизации используй /start и /auth."
        )
    else:
        await message.answer("❌ У тебя нет сохранённого токена.")


def extract_token_from_raw(raw_string: str) -> str | None:
    """Извлечение токена из сырой строки любого формата"""
    clean_string = ' '.join(raw_string.split())

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
        decoded_once = unquote(clean_string)
        for pattern in patterns[:2]:
            match = re.search(pattern, decoded_once)
            if match:
                return match.group(1)

        decoded_twice = unquote(decoded_once)
        for pattern in patterns[:2]:
            match = re.search(pattern, decoded_twice)
            if match:
                return match.group(1)
    except Exception as e:
        logger.warning(f"Ошибка декодирования URL: {e}")

    direct_match = re.search(r'\b(y0_[A-Za-z0-9_-]{30,}|AQ[A-Za-z0-9_-]{30,})\b', clean_string)
    if direct_match:
        return direct_match.group(1)

    fallback_match = re.search(r'(y0_[A-Za-z0-9_-]{30,}|AQ[A-Za-z0-9_-]{30,})', clean_string)
    if fallback_match:
        return fallback_match.group(1)

    return None


def get_client(user_id: int) -> Client | None:
    """Получить клиент Яндекс.Музыки для пользователя"""
    token = user_tokens.get(user_id)
    if not token:
        return None
    try:
        return Client(token).init()
    except Exception as e:
        logger.error(f"Ошибка создания клиента для {user_id}: {e}")
        return None


def has_token(user_id: int) -> bool:
    """Проверить наличие токена у пользователя"""
    return user_id in user_tokens
