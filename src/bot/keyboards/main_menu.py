from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура с командами после авторизации"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Мои плейлисты"),
                KeyboardButton(text="🆕 Создать плейлист"),
            ],
            [
                KeyboardButton(text="📝 Текст песни"),
                KeyboardButton(text="ℹ️ Инфо о песне"),
            ],
            [
                KeyboardButton(text="👤 Инфо об исполнителе"),
                KeyboardButton(text="➕ Добавить в плейлист"),
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
    """Клавиатура для авторизации через Telegram WebApp"""
    # ВАЖНО: Замени USERNAME на свой GitHub username после деплоя на GitHub Pages
    webapp_url = "https://USERNAME.github.io/s3v3ryan1n-project-yandex-music/webapp.html"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎵 Авторизоваться",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]
        ]
    )
