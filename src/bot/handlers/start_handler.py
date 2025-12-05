from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from yandex_music import Client
from yandex_music.exceptions import UnauthorizedError, NetworkError

from src.bot.keyboards import get_main_keyboard, get_auth_keyboard

router = Router()


class AuthStates(StatesGroup):
    waiting_for_token = State()
    waiting_for_new_playlist_title = State()


def _get_client_from_state(data: dict) -> Client | None:
    """Создаём Yandex Music Client из сохранённого токена."""
    token = data.get("yandex_token")
    if not token:
        return None
    return Client(token).init()


# ================== /start и авторизация ==================


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Приветствие и проверка, есть ли уже сохранённый токен."""
    data = await state.get_data()
    yandex_token = data.get("yandex_token")

    if yandex_token:
        try:
            client = Client(yandex_token).init()
            account = client.account_status()
            await message.answer(
                f"С возвращением, {account.account.display_name or message.from_user.first_name}! 🎵\n\n"
                f"Аккаунт: {account.account.login}\n"
                f"Подписка: {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
                "Используй кнопки ниже.",
                reply_markup=get_main_keyboard(),
            )
            return
        except Exception:
            # если токен протух — чистим всё и просим авторизоваться заново
            await state.clear()

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Для работы с Яндекс.Музыкой нужен токен доступа.\n\n"
        "1️⃣ Нажми кнопку ниже, откроется страница Яндекса.\n"
        "2️⃣ Авторизуйся и разреши доступ.\n"
        "3️⃣ В адресной строке найди часть <code>access_token=...</code>.\n"
        "4️⃣ Скопируй всё после <code>access_token=</code> до символа <code>&</code>.\n"
        "5️⃣ Отправь этот токен одним сообщением сюда.\n\n"
        "После этого бот включит кнопки с плейлистами и остальным функционалом.",
        reply_markup=get_auth_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AuthStates.waiting_for_token)
    print("STATE SET: waiting_for_token", flush=True)


@router.message(AuthStates.waiting_for_token, F.text)
async def process_token(message: Message, state: FSMContext):
    """Принимаем токен, валидируем, сохраняем и включаем меню."""
    token = message.text.strip()
    print("PROCESS TOKEN CALLED, text =", token[:80], flush=True)

    if len(token) < 20:
        await message.answer(
            "❌ Похоже, токен слишком короткий.\n"
            "Убедись, что копируешь ВСЮ строку после <code>access_token=</code> до символа <code>&</code>.",
            parse_mode="HTML",
        )
        return

    checking = await message.answer("⏳ Проверяю токен в Яндекс.Музыке...")

    try:
        client = Client(token).init()
        account = client.account_status()
        playlists = client.users_playlists_list()
        liked = client.users_likes_tracks()

        liked_count = 0
        if hasattr(liked, "tracks") and liked.tracks:
            liked_count = len(liked.tracks)

        # Сохраняем токен в data
        await state.update_data(yandex_token=token)
        # Выходим из состояния ожидания токена
        await state.set_state(None)

        await checking.delete()

        await message.answer(
            "✅ Авторизация прошла успешно!\n\n"
            f"Пользователь: <b>{account.account.display_name or account.account.login}</b>\n"
            f"Аккаунт: {account.account.login}\n"
            f"Подписка: {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
            f"📋 Плейлистов: {len(playlists) if playlists else 0}\n"
            f"❤️ Лайкнутых треков: {liked_count}\n\n"
            "Теперь используй кнопки ниже.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )

    except UnauthorizedError:
        await message.answer(
            "❌ Токен недействителен или истёк.\n\n"
            "Попробуй ещё раз получить токен по инструкции через /start."
        )
    except NetworkError:
        await message.answer(
            "❌ Ошибка сети при обращении к Яндекс.Музыке.\nПопробуй чуть позже."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        await message.answer(
            "❌ Внутренняя ошибка при проверке токена:\n"
            f"<code>{e}</code>",
            parse_mode="HTML",
        )


# ================== КНОПКА: Мои плейлисты ==================


@router.message(F.text == "📋 Мои плейлисты")
async def show_playlists(message: Message, state: FSMContext):
    """Показываем плейлисты с реальным количеством треков."""
    data = await state.get_data()
    client = _get_client_from_state(data)
    if not client:
        await message.answer("❌ Сначала авторизуйся через /start")
        return

    try:
        account = client.account_status()
        user_id = account.account.uid  # нужен для users_playlists(kind, user_id)
        playlists = client.users_playlists_list()
        if not playlists:
            await message.answer("У тебя нет плейлистов 😢")
            return

        text = "📋 <b>Твои плейлисты:</b>\n\n"
        for i, pl in enumerate(playlists[:20], start=1):
            # Подгружаем полный плейлист, чтобы узнать реальное количество треков
            full_pl = client.users_playlists(kind=pl.kind, user_id=user_id)
            track_count = len(full_pl.tracks) if full_pl and full_pl.tracks else 0
            title = pl.title or "Без названия"
            text += f"{i}. <b>{title}</b> — {track_count} треков\n"

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении плейлистов:\n<code>{e}</code>",
            parse_mode="HTML",
        )


# ================== КНОПКА: Создать плейлист ==================


@router.message(F.text == "🆕 Создать плейлист")
async def ask_new_playlist_title(message: Message, state: FSMContext):
    data = await state.get_data()
    client = _get_client_from_state(data)
    if not client:
        await message.answer("❌ Сначала авторизуйся через /start")
        return

    await message.answer("Введи название нового плейлиста:")
    await state.set_state(AuthStates.waiting_for_new_playlist_title)


@router.message(AuthStates.waiting_for_new_playlist_title, F.text)
async def create_playlist(message: Message, state: FSMContext):
    data = await state.get_data()
    client = _get_client_from_state(data)
    if not client:
        # сбрасываем только состояние, но не data с токеном
        await state.set_state(None)
        await message.answer("❌ Токен потерян, авторизуйся заново через /start")
        return

    title = message.text.strip()
    if not title:
        await message.answer("Название не может быть пустым. Введи другое.")
        return

    try:
        pl = client.users_playlists_create(title=title, visibility="private")
        await message.answer(
            f"✅ Плейлист <b>{pl.title}</b> создан.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось создать плейлист:\n<code>{e}</code>",
            parse_mode="HTML",
        )
    finally:
        # выходим из состояния, но токен в data остаётся
        await state.set_state(None)


# ================== КНОПКА: Статистика ==================


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, state: FSMContext):
    data = await state.get_data()
    client = _get_client_from_state(data)
    if not client:
        await message.answer("❌ Сначала авторизуйся через /start")
        return

    try:
        account = client.account_status()
        playlists = client.users_playlists_list()
        liked = client.users_likes_tracks()

        liked_count = 0
        if hasattr(liked, "tracks") and liked.tracks:
            liked_count = len(liked.tracks)

        text = (
            "📊 <b>Статистика аккаунта</b>\n\n"
            f"<b>Логин:</b> {account.account.login}\n"
            f"<b>Отображаемое имя:</b> {account.account.display_name}\n"
            f"<b>Подписка:</b> {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
            f"<b>Плейлистов:</b> {len(playlists) if playlists else 0}\n"
            f"<b>Лайкнутых треков:</b> {liked_count}\n"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при получении статистики:\n<code>{e}</code>",
            parse_mode="HTML",
        )
