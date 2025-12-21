from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📁 Плейлисты", callback_data="menu_playlists"),
            InlineKeyboardButton(text="🎵 Текст песни", callback_data="menu_lyrics")
        ],
        [
            InlineKeyboardButton(text="➕ Создать плейлист", callback_data="menu_create_playlist"),
            InlineKeyboardButton(text="🎼 Добавить треки", callback_data="menu_add_tracks")
        ],
        [
            InlineKeyboardButton(text="❤️ Лайкнуть трек", callback_data="menu_like_track"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")
        ]
    ])
    return keyboard

def get_back_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")]
    ])
    return keyboard

def get_auth_keyboard(auth_url: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Получить токен", url=auth_url)],
        [InlineKeyboardButton(text="❓ Как получить токен?", callback_data="auth_help")]
    ])
    return keyboard

def get_playlists_keyboard(current_page: int, total_pages: int):
    buttons = []
    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"playlists:page:{current_page - 1}"
                )
            )
        else:
            nav_row.append(
                InlineKeyboardButton(
                    text="·",
                    callback_data="noop"
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                text=f"· {current_page + 1}/{total_pages} ·",
                callback_data="noop"
            )
        )
        if current_page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Вперед ▶️",
                    callback_data=f"playlists:page:{current_page + 1}"
                )
            )
        else:
            nav_row.append(
                InlineKeyboardButton(
                    text="·",
                    callback_data="noop"
                )
            )
        buttons.append(nav_row)
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")
    ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard