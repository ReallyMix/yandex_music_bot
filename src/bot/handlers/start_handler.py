# Импорт модуля логирования для записи событий и ошибок
import logging
# Импорт модуля регулярных выражений для извлечения токена из строк
import re
# Импорт функции для декодирования URL-encoded строк
from urllib.parse import unquote

# Импорт компонентов aiogram для создания Telegram-бота
from aiogram import Router, F
# Импорт типов сообщений и кнопок Telegram
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
# Импорт фильтра команд
from aiogram.filters import Command
# Импорт конечного автомата состояний (FSM) для временного хранения данных
from aiogram.fsm.context import FSMContext
# Импорт базовых классов для создания состояний FSM
from aiogram.fsm.state import State, StatesGroup
# Импорт клиента Яндекс.Музыки для взаимодействия с API
from yandex_music import Client

# Импорт кастомных модулей проекта
from ..keyboards.main_menu import get_main_menu  # функция получения главного меню
from ..storage import set_token, get_token, remove_token, has_token as has_token_storage  # функции работы с хранилищем токенов

# Создание роутера для обработки сообщений
router = Router()
# Создание логгера для текущего модуля
logger = logging.getLogger(__name__)

# Определение состояний FSM для процесса авторизации
class AuthStates(StatesGroup):
    waiting_for_url = State()  # Состояние ожидания ввода строки с токеном

# Константы для OAuth авторизации Яндекс
CLIENT_ID = "23cabbbdc6cd418abb4b39c32c41195d"  # ID приложения Яндекс.Музыки
# URL для авторизации пользователя через OAuth
AUTH_URL = f"https://oauth.yandex.ru/authorize?response_type=token&client_id={CLIENT_ID}"

# Обработчик команды /start
@router.message(Command("start"))
async def start_handler(message: Message):
    """Старт бота"""
    user_id = message.from_user.id
    user_has_token = has_token_storage(user_id)

    if user_has_token:
        await message.answer(
            "<b>С возвращением!</b>\n\n"
            "Ты уже авторизован.\n\n"
            "Используй кнопки меню ниже для работы с Яндекс.Музыкой:",
            reply_markup=get_main_menu()
        )
        return

    # Для неавторизованного пользователя — просто приветствие + предложение пройти /auth
    await message.answer(
        "<b>Добро пожаловать в бота для Яндекс.Музыки!</b>\n\n"
        "🔑 Токен не установлен.\n\n"
        "<b>Как начать:</b>\n"
        "1. Выполни команду <code>/auth</code>.\n"
        "2. Следуй подсказкам в чате, чтобы получить и отправить строку с токеном."
    )

# Обработчик колбэка для показа инструкций
@router.callback_query(F.data == "show_instructions")
async def show_instructions(callback: CallbackQuery):
    """Подробная инструкция по получению токена (упрощённая)"""
    await callback.message.answer(
        "📘 <b>Как получить токен</b>\n\n"
        "<b>Через браузер на ПК</b>\n"
        "1. Нажми «📱 Получить токен» или открой ссылку:\n"
        f"<code>{AUTH_URL}</code>\n\n"
        "2. Войди в Яндекс и дай доступ Яндекс.Музыке.\n"
        "3. После входа адрес станет вида:\n"
        "<code>https://music.yandex.ru/#access_token=ТОКЕН&token_type=bearer...</code>\n\n"
        "4. Скопируй этот адрес целиком <b>или</b> любой текст, где есть "
        "<code>access_token=...</code>\n"
        "(подойдёт <code>#access_token=...</code>, "
        "<code>access_token%3D...</code> или просто сам токен).\n\n"
        "5. Отправь строку в бота через:\n"
        " • <code>/auth ВСТАВЬ_СТРОКУ</code>  или\n"
        " • команду <code>/auth</code>, а затем отдельным сообщением вставь строку.\n"
        "Бот сам вырежет токен из этой строки.\n\n"
        "<b>На телефоне (iOS / Android)</b>\n"
        "• Открывай ссылку авторизации <b>в Chrome или обычном браузере</b>,\n"
        "а не во встроенном браузере Telegram, чтобы не перебрасывало в приложение Яндекс.Музыки.\n"
        "• После входа скопируй адрес страницы или любой текст, где есть <code>access_token=...</code>,\n"
        "и отправь его в /auth — бот сам вытащит токен.",
        disable_web_page_preview=True
    )
    await callback.answer()

# Обработчик команды /auth
@router.message(Command("auth"))
async def auth_command(message: Message, state: FSMContext):
    """Команда для обработки сырой строки с токеном"""
    args = message.text.split(maxsplit=1)

    # Клавиатура с ссылкой на авторизацию и инструкцией
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Получить токен Яндекс.Музыки",
            url=AUTH_URL
        )],
        [InlineKeyboardButton(
            text="📘 Инструкция по получению токена",
            callback_data="show_instructions"
        )]
    ])

    if len(args) >= 2:
        raw_string = args[1].strip()
        await process_raw_string(message, raw_string)
    else:
        await state.set_state(AuthStates.waiting_for_url)
        await message.answer(
            "🔴 <b>Отправь строку с токеном</b>\n\n"
            "Подойдёт любой вариант:\n"
            "• полный URL из адресной строки после логина\n"
            "• любой текст, где внутри есть <code>access_token=...</code>\n"
            "или токен, начинающийся на <code>y0_</code> / <code>AQ</code>.\n\n"
            "Бот сам вырежет нужный кусок.\n\n"
            "Для отмены — /cancel.",
            reply_markup=keyboard
        )

# Обработчик сообщения в состоянии ожидания токена
@router.message(AuthStates.waiting_for_url)
async def process_auth_url(message: Message, state: FSMContext):
    """Получили строку после /auth"""
    await state.clear()
    await process_raw_string(message, message.text.strip())

# Обработчик команды /cancel
@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Отмена текущего действия"""
    if await state.get_state() is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer("✅ Действие отменено.")

# Основная функция обработки сырой строки
async def process_raw_string(message: Message, raw_string: str):
    """Обработка сырой строки, извлечение и проверка токена"""
    status_msg = await message.answer("🔍 Ищу токен в строке...")

    token = extract_token_from_raw(raw_string)

    if not token:
        await status_msg.edit_text(
            "✗ <b>Токен не найден.</b>\n"
            "Убедись, что в строке есть кусок вида <code>access_token=...</code>\n"
            "или токен, начинающийся на <code>y0_</code> / <code>AQ</code>.\n"
            "Попробуй ещё раз: /auth."
        )
        return

    await status_msg.edit_text("✅ Токен найден.\n🔐 Проверяю валидность...")

    try:
        client = Client(token).init()
        account = client.account_status()

        set_token(message.from_user.id, token)
        logger.info(f"Токен установлен для пользователя {message.from_user.id}")

        inline_menu = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Моя музыка", callback_data="open_music_menu"),
                InlineKeyboardButton(text="Поиск", callback_data="open_search")
            ],
            [
                InlineKeyboardButton(text="Мои лайки", callback_data="show_likes"),
                InlineKeyboardButton(text="Плейлисты", callback_data="show_playlists")
            ]
        ])

        await status_msg.edit_text(
            "✅ <b>Авторизация успешна!</b>\n"
            f"🔑 Токен: <code>{token[:20]}...{token[-10:]}</code>\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс ✅' if account.plus else 'Без подписки'}\n"
            "🎵 Статус: Активен.\n\n"
            "💡 Выбери, что открыть:",
            reply_markup=inline_menu
        )

    except Exception as e:
        logger.error(f"Ошибка валидации токена: {e}")
        await status_msg.edit_text(
            "✗ <b>Найденный токен не сработал.</b>\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Попробуй получить токен ещё раз и отправить другую строку через /auth."
        )

# Обработчик команды /check
@router.message(Command("check"))
async def check_command(message: Message):
    """Проверка сохранённого токена"""
    user_id = message.from_user.id
    token = get_token(user_id)

    if not token:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Получить токен", url=AUTH_URL)]
        ])
        await message.answer(
            "✗ Токен не установлен.\n\n"
            "Используй /auth для авторизации.",
            reply_markup=keyboard
        )
        return

    try:
        client = Client(token).init()
        account = client.account_status()

        await message.answer(
            "✅ <b>Токен действителен.</b>\n"
            f"👤 Аккаунт: <code>{account.account.login}</code>\n"
            f"💎 Подписка: {'Яндекс Плюс' if account.plus else 'Без подписки'}"
        )

    except Exception as e:
        logger.error(f'Ошибка проверки токена: {e}')
        remove_token(user_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Получить новый токен", url=AUTH_URL)]
        ])

        await message.answer(
            "✗ Токен недействителен или истёк.\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            "Нужно получить новый токен и снова выполнить /auth.",
            reply_markup=keyboard
        )

# Обработчик команды /logout
@router.message(Command("logout"))
async def logout_command(message: Message):
    """Удаление токена"""
    user_id = message.from_user.id

    if has_token_storage(user_id):
        remove_token(user_id)
        logger.info(f"Токен удалён для пользователя {user_id}")
        await message.answer(
            "✅ Токен удалён.\n\n"
            "Для новой авторизации используй /start и /auth."
        )
    else:
        await message.answer("✗ У тебя нет сохранённого токена.")

def extract_token_from_raw(raw_string: str) -> str | None:
    """Извлечение токена из сырой строки любого формата"""
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

    direct_match = re.search(r'\b(y0_[A-Za-z0-9_-]{30,})\b', clean_string)
    if direct_match:
        return direct_match.group(1)

    fallback_match = re.search(r'(y0_[A-Za-z0-9_-]{30,})|(AQ[A-Za-z0-9_-]{30,})', clean_string)
    if fallback_match:
        return fallback_match.group(1)

    return None
