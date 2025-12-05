from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура после авторизации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Мои плейлисты"),
                KeyboardButton(text="🆕 Создать плейлист"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите команду",
    )


def get_auth_keyboard() -> InlineKeyboardMarkup:
    """Кнопка с переходом на страницу, где юзер сам достаёт токен"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎵 Открыть Яндекс.Музыку для получения токена",
                    url=(
                        "https://oauth.yandex.ru/authorize"
                        "?response_type=token"
                        "&client_id=23cabbbdc6cd418abb4b39c32c41195d"
                    ),
                )
            ]
        ]
    )
