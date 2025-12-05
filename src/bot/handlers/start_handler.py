from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import json

from yandex_music import Client
from yandex_music.exceptions import UnauthorizedError, NetworkError

from src.bot.keyboards import get_main_keyboard, get_auth_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start - приветствие и проверка авторизации"""
    
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
                "Используй кнопки ниже для работы с Яндекс.Музыкой.",
                reply_markup=get_main_keyboard(),
            )
            return
        except Exception:
            await state.clear()

    # Показываем приветствие неавторизованному пользователю
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для работы с Яндекс.Музыкой. С моей помощью ты можешь:\n\n"
        "🎵 Управлять своими плейлистами\n"
        "📝 Получать тексты песен\n"
        "ℹ️ Смотреть информацию о треках и исполнителях\n"
        "📊 Отслеживать статистику прослушиваний\n"
        "➕ Добавлять треки в плейлисты\n\n"
        "Для начала работы нажми кнопку ниже 👇",
        reply_markup=get_auth_keyboard(),
    )

@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, state: FSMContext):
    """Обработка данных из WebApp (токен от Яндекса)"""
    
    try:
        data = json.loads(message.web_app_data.data)
        token = data.get("token")
        
        if not token:
            await message.answer("❌ Токен не получен из WebApp. Попробуй ещё раз через /start")
            return
        
        checking_msg = await message.answer("⏳ Проверяю токен и права доступа...")
        
        # Проверяем токен через yandex-music-api
        client = Client(token).init()
        account = client.account_status()
        
        # Проверяем доступ к данным
        playlists = client.users_playlists_list()
        liked = client.users_likes_tracks()
        
        # Сохраняем токен в состоянии пользователя
        await state.update_data(yandex_token=token)
        
        # TODO: Добавить пользователя в базу данных (неделя 2)
        # from src.database.repository import get_repository
        # repo = get_repository()
        # repo.save_user(message.from_user.id, token, account.account.login)
        
        await checking_msg.delete()
        
        await message.answer(
            "✅ Авторизация успешна!\n\n"
            f"Пользователь: <b>{account.account.display_name or account.account.login}</b>\n"
            f"Аккаунт: {account.account.login}\n"
            f"Подписка: {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
            f"📊 Найдено плейлистов: {len(playlists) if playlists else 0}\n"
            f"❤️ Лайкнутых треков: {liked.total if liked else 0}\n\n"
            "Теперь используй команды через кнопки меню!",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
        
    except UnauthorizedError:
        await message.answer(
            "❌ Токен недействителен или истёк.\n\n"
            "Попробуй авторизоваться заново через /start"
        )
    except AttributeError:
        await message.answer(
            "❌ Токен не имеет нужных прав доступа.\n\n"
            "При авторизации на Яндексе РАЗРЕШИ ВСЕ запрашиваемые права.\n"
            "Используй /start для повторной попытки."
        )
    except NetworkError:
        await message.answer(
            "❌ Ошибка сети. Проверь подключение к интернету.\n\n"
            "Используй /start для повторной попытки."
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при проверке токена:\n\n"
            f"de>{str(e)}</code>\n\n"
            "Попробуй ещё раз через /start",
            parse_mode="HTML",
        )
