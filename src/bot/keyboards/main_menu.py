from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# Client ID для авторизации
CLIENT_ID = "23cabbbdc6cd418abb4b39c32c41195d"
AUTH_URL = f"https://oauth.yandex.ru/authorize?response_type=token&client_id={CLIENT_ID}"

def get_auth_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для авторизации"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📱 Получить токен Яндекс.Музыки",
                url=AUTH_URL,
            )],
            [
                InlineKeyboardButton(
                    text="📘 Инструкция",
                    callback_data="show_instructions",
                )
            ]
        ]
    )

def get_main_menu() -> ReplyKeyboardMarkup:
    """Основное меню бота после авторизации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="♪ Моя музыка"),
                KeyboardButton(text="🔍 Поиск"),
            ],
            [
                KeyboardButton(text="❤️ Мои лайки"),
                KeyboardButton(text="📁 Плейлисты"),
            ],
            [
                KeyboardButton(text="👨‍🎤 Любимые артисты"),
                KeyboardButton(text="💿 Альбомы"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )

def get_check_token_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для проверки токена"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔍 Проверить токен",
                callback_data="check_token",
            )],
            [
                InlineKeyboardButton(
                    text="📱 Получить новый токен",
                    url=AUTH_URL,
                )
            ],
        ]
    )

def get_music_menu() -> InlineKeyboardMarkup:
    """Меню музыки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❤️ Мои лайки", callback_data="show_likes"
                ),
                InlineKeyboardButton(
                    text="📁 Плейлисты", callback_data="show_playlists"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👨‍🎤 Любимые артисты", callback_data="show_artists"
                ),
                InlineKeyboardButton(
                    text="💿 Альбомы", callback_data="show_albums"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика", callback_data="show_stats"
                )
            ],
        ]
    )