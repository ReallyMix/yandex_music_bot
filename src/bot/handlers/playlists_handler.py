import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from .common import require_auth, _effective_user_id_from_message, _get_playlist_tracks_by_kind
from ..storage import get_token
from ..services import ym_service

router = Router()
logger = logging.getLogger(__name__)

# 📂 Временное хранилище данных с TTL (время жизни)
class PlaylistCache:
    def __init__(self, ttl_minutes: int = 30):
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.ttl = ttl_minutes
    
    def set(self, user_id: int, data: Dict[str, Any]):
        """Сохранить данные с временной меткой"""
        self.cache[user_id] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def get(self, user_id: int) -> Optional[List[Dict]]:
        """Получить данные, если они не устарели"""
        if user_id not in self.cache:
            return None
        
        cache_entry = self.cache[user_id]
        age = datetime.now() - cache_entry['timestamp']
        
        if age > timedelta(minutes=self.ttl):
            # Удаляем устаревшие данные
            del self.cache[user_id]
            return None
        
        return cache_entry['data']
    
    def clear(self, user_id: int = None):
        """Очистить кэш"""
        if user_id:
            self.cache.pop(user_id, None)
        else:
            self.cache.clear()

# Инициализируем кэш
playlist_cache = PlaylistCache(ttl_minutes=30)

@router.callback_query(F.data == "show_playlists")
async def show_playlists_callback(callback: CallbackQuery):
    """Обработчик для кнопки показа плейлистов"""
    await callback.answer()
    user_id = callback.from_user.id
    await show_playlists_page(callback.message, user_id, page=0)

@router.message(F.text == "Плейлисты")
@router.message(Command("playlists"))
@require_auth
async def playlists_command(message: Message):
    """Обработчик команды /playlists"""
    user_id = _effective_user_id_from_message(message)
    await show_playlists_page(message, user_id, page=0)

@router.message(Command("refresh_playlists"))
@require_auth
async def refresh_playlists_command(message: Message):
    """Обновить кэш плейлистов"""
    user_id = _effective_user_id_from_message(message)
    playlist_cache.clear(user_id)
    await message.answer("🔄 Кэш плейлистов очищен. Загружаю заново...")
    await show_playlists_page(message, user_id, page=0, force_refresh=True)

async def show_playlists_page(
    message: Message, 
    user_id: int, 
    page: int = 0, 
    force_refresh: bool = False
):
    """Отображение плейлистов с пагинацией и кэшированием"""
    # Используем try-except для обработки ошибок отправки сообщений
    try:
        status_msg = await message.answer("📁 Загружаю плейлисты...")
    except Exception as e:
        logger.error(f"Не удалось отправить статус: {e}")
        return
    
    # Получаем токен
    token = get_token(user_id)
    if not token:
        try:
            await status_msg.edit_text(
                "🔑 Требуется авторизация. Используйте /auth для входа в Яндекс.Музыку."
            )
        except:
            pass
        return
    
    # Проверяем кэш, если не принудительное обновление
    if not force_refresh:
        cached_playlists = playlist_cache.get(user_id)
        if cached_playlists is not None:
            logger.info(f"Используем кэшированные плейлисты для user_id={user_id}")
            await _display_playlists_page(status_msg, message, user_id, cached_playlists, page)
            return
    
    try:
        # Загружаем плейлисты через сервис
        logger.info(f"Запрашиваем плейлисты для user_id={user_id} с токеном: {token[:20]}...")
        
        # Получаем плейлисты
        playlists = await ym_service.get_user_playlists(token, user_id)
        
        # Логируем результат более подробно
        logger.info(f"Получено плейлистов: {len(playlists) if playlists else 0}")
        logger.info(f"Тип данных: {type(playlists)}")
        
        if playlists:
            logger.info(f"Пример структуры первого плейлиста: {playlists[0]}")
            for i, pl in enumerate(playlists[:3]):  # Логируем первые 3 плейлиста
                logger.info(f"Плейлист {i}: {pl.get('title', 'Без названия')}, kind: {pl.get('kind')}, track_count: {pl.get('track_count')}")
        else:
            # Пробуем получить информацию об аккаунте, чтобы понять, работает ли токен
            logger.warning(f"Список плейлистов пустой для user_id={user_id}")
            
            # Проверяем, есть ли исключения при создании клиента
            try:
                # Пробуем получить прямой доступ к API для диагностики
                from yandex_music import Client
                client = Client(token)
                account = client.account_status()
                if account and account.account:
                    logger.info(f"Аккаунт получен: uid={account.account.uid}, login={account.account.login}")
                    # Пробуем получить плейлисты напрямую
                    try:
                        direct_playlists = client.users_playlists(account.account.uid)
                        logger.info(f"Прямой запрос вернул: {len(direct_playlists) if direct_playlists else 0} плейлистов")
                        if direct_playlists:
                            logger.info(f"Пример прямого плейлиста: {direct_playlists[0].title if hasattr(direct_playlists[0], 'title') else 'No title'}")
                    except Exception as direct_e:
                        logger.error(f"Ошибка прямого запроса плейлистов: {direct_e}")
                else:
                    logger.warning("Не удалось получить информацию об аккаунте")
            except Exception as client_e:
                logger.error(f"Ошибка создания клиента: {client_e}")
        
        if not playlists:
            # Даем более информативное сообщение
            await status_msg.edit_text(
                "📭 Не удалось получить плейлисты. Возможные причины:\n\n"
                "1. 🔑 Токен авторизации устарел или недействителен\n"
                "2. 📁 У вас действительно нет созданных плейлистов\n"
                "3. 🌐 Проблемы с подключением к Яндекс.Музыке\n\n"
                "💡 Попробуйте:\n"
                "• Переавторизоваться командой /auth\n"
                "• Проверить, есть ли плейлисты в приложении Яндекс.Музыки\n"
                "• Подождать и попробовать позже"
            )
            return
        
        # Сохраняем в кэш
        playlist_cache.set(user_id, playlists)
        
        # Отображаем плейлисты
        await _display_playlists_page(status_msg, message, user_id, playlists, page)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при получении плейлистов: {e}", exc_info=True)
        
        error_message = (
            f"⚠️ Произошла ошибка при загрузке плейлистов:\n"
            f"<code>{str(e)[:200]}</code>\n\n"
            f"Попробуйте:\n"
            f"1. Обновить плейлисты командой /refresh_playlists\n"
            f"2. Переавторизоваться командой /auth\n"
            f"3. Проверить соединение с интернетом"
        )
        
        try:
            await status_msg.edit_text(
                error_message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="show_playlists")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_music")]
                ])
            )
        except:
            await message.answer(
                error_message,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить", callback_data="show_playlists")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_music")]
                ])
            )

async def _display_playlists_page(
    status_msg: Message, 
    original_msg: Message, 
    user_id: int, 
    playlists: List[Dict], 
    page: int
):
    """Вспомогательная функция для отображения страницы плейлистов"""
    total_playlists = len(playlists)
    
    # Проверяем корректность страницы
    if page < 0 or page >= total_playlists:
        page = 0
    
    # Получаем текущий плейлист
    pl = playlists[page]
    
    # Извлекаем данные с проверками
    title = pl.get("title") or "Без названия"
    count = pl.get("track_count", pl.get("trackCount", 0))
    desc = pl.get("description", "")
    kind = pl.get("kind")
    playlist_id = pl.get("id")
    
    # Получаем дополнительную информацию
    owner_info = pl.get("owner", {})
    owner_name = owner_info.get("name", owner_info.get("login", "Неизвестно"))
    
    # Форматируем текст
    text = (
        f"📁 <b>Плейлист {page + 1}/{total_playlists}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎵 <b>{title}</b>\n"
        f"📊 Треков: {count}\n"
        f"👤 Владелец: {owner_name}\n"
    )
    
    # Добавляем описание если есть
    if desc and desc.strip():
        # Ограничиваем длину и чистим от лишних пробелов
        clean_desc = ' '.join(desc.strip().split())
        if len(clean_desc) > 100:
            clean_desc = clean_desc[:97] + "..."
        text += f"📝 <i>{clean_desc}</i>\n"
    
    # Добавляем время создания/обновления если есть
    modified = pl.get("modified")
    if modified:
        try:
            # Пытаемся преобразовать timestamp в читаемый формат
            dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
            text += f"🕐 Обновлен: {dt.strftime('%d.%m.%Y %H:%M')}\n"
        except:
            pass
    
    # Создаем клавиатуру
    kb_buttons = []
    
    # Кнопки навигации по плейлистам
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️", 
            callback_data=f"pl_nav:{user_id}:{page-1}"
        ))
    
    # Кнопка открытия треков (используем kind или id)
    if kind is not None:
        nav_row.append(InlineKeyboardButton(
            text="🎵 Открыть треки", 
            callback_data=f"pl_open:{user_id}:{kind}:0"
        ))
    elif playlist_id:
        nav_row.append(InlineKeyboardButton(
            text="🎵 Открыть треки", 
            callback_data=f"pl_open_id:{user_id}:{playlist_id}:0"
        ))
    
    if page < total_playlists - 1:
        nav_row.append(InlineKeyboardButton(
            text="▶️", 
            callback_data=f"pl_nav:{user_id}:{page+1}"
        ))
    
    if nav_row:
        kb_buttons.append(nav_row)
    
    # Кнопки быстрой навигации (если много плейлистов)
    if total_playlists > 1:
        quick_nav = []
        max_buttons = min(5, total_playlists)
        start_page = max(0, page - max_buttons // 2)
        end_page = min(total_playlists, start_page + max_buttons)
        
        # Корректируем начальную страницу если вышли за границы
        if end_page - start_page < max_buttons and start_page > 0:
            start_page = max(0, end_page - max_buttons)
        
        for p in range(start_page, end_page):
            if p == page:
                quick_nav.append(InlineKeyboardButton(
                    text=f"• {p+1} •", 
                    callback_data=f"pl_nav:{user_id}:{p}"
                ))
            else:
                quick_nav.append(InlineKeyboardButton(
                    text=str(p+1), 
                    callback_data=f"pl_nav:{user_id}:{p}"
                ))
        
        if quick_nav:
            kb_buttons.append(quick_nav)
    
    # Дополнительные кнопки
    kb_buttons.extend([
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_playlists"),
            InlineKeyboardButton(text="📋 Все треки", callback_data="all_tracks")
        ],
        [
            InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_music")
        ]
    ])
    
    # Пытаемся редактировать существующее сообщение
    try:
        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e) or "message is not modified" in str(e):
            # Отправляем новое сообщение
            try:
                await status_msg.delete()
            except:
                pass
            
            await original_msg.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
                parse_mode="HTML"
            )
        else:
            raise
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения: {e}")
        await original_msg.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("pl_nav:"))
async def playlist_navigate_callback(callback: CallbackQuery):
    """Навигация по плейлистам"""
    await callback.answer()
    
    try:
        # Формат: pl_nav:user_id:page
        _, user_id_str, page_str = callback.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)
        
        # Получаем кэшированные плейлисты
        playlists = playlist_cache.get(user_id)
        if playlists is None:
            await callback.message.answer("🔄 Данные устарели. Загружаю заново...")
            await show_playlists_page(callback.message, user_id, page, force_refresh=True)
            return
        
        await _display_playlists_page(callback.message, callback.message, user_id, playlists, page)
        
    except ValueError as e:
        logger.error(f"Ошибка парсинга callback данных: {e}")
        await callback.answer("❌ Ошибка навигации")
    except Exception as e:
        logger.error(f"Ошибка навигации по плейлистам: {e}", exc_info=True)
        await callback.answer("⚠️ Ошибка при загрузке")

@router.callback_query(F.data.startswith("pl_open:"))
async def playlist_open_callback(callback: CallbackQuery):
    """Открытие плейлиста по kind"""
    await callback.answer("🎵 Загружаю треки...")
    
    try:
        # Формат: pl_open:user_id:kind:page
        _, user_id_str, kind_str, page_str = callback.data.split(":")
        user_id = int(user_id_str)
        kind = int(kind_str)
        page = int(page_str)
        
        await show_playlist_tracks_page(callback.message, user_id, kind, page)
        
    except Exception as e:
        logger.error(f"Ошибка открытия плейлиста: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {str(e)[:100]}")

@router.callback_query(F.data.startswith("pl_open_id:"))
async def playlist_open_by_id_callback(callback: CallbackQuery):
    """Открытие плейлиста по ID (альтернативный вариант)"""
    await callback.answer("🎵 Загружаю треки...")
    
    try:
        # Формат: pl_open_id:user_id:playlist_id:page
        _, user_id_str, playlist_id, page_str = callback.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)
        
        # Здесь можно реализовать альтернативный метод получения треков по ID
        # Пока что используем тот же метод, но с поиском kind по ID
        playlists = playlist_cache.get(user_id)
        if playlists:
            for pl in playlists:
                if pl.get("id") == playlist_id or str(pl.get("id")) == playlist_id:
                    kind = pl.get("kind")
                    if kind:
                        await show_playlist_tracks_page(callback.message, user_id, kind, page)
                        return
        
        await callback.message.answer("❌ Не удалось найти плейлист")
        
    except Exception as e:
        logger.error(f"Ошибка открытия плейлиста по ID: {e}", exc_info=True)
        await callback.message.answer(f"❌ Ошибка: {str(e)[:100]}")

async def show_playlist_tracks_page(
    message: Message, 
    user_id: int, 
    kind: int, 
    page: int = 0, 
    tracks_per_page: int = 10
):
    """Отображение треков плейлиста с пагинацией"""
    token = get_token(user_id)
    if not token:
        await message.answer("🔑 Требуется авторизация. Используйте /auth")
        return
    
    try:
        status_msg = await message.answer("🎵 Загружаю треки...")
    except:
        return
    
    try:
        # Получаем треки
        tracks = await _get_playlist_tracks_by_kind(token, user_id, kind)
        
        if not tracks:
            await status_msg.edit_text("📭 В этом плейлисте пока нет треков.")
            return
        
        total_tracks = len(tracks)
        total_pages = max(1, (total_tracks + tracks_per_page - 1) // tracks_per_page)
        
        # Корректируем страницу
        if page < 0 or page >= total_pages:
            page = 0
        
        # Получаем диапазон треков
        start_idx = page * tracks_per_page
        end_idx = min(start_idx + tracks_per_page, total_tracks)
        current_tracks = tracks[start_idx:end_idx]
        
        # Получаем информацию о плейлисте из кэша
        playlist_title = "Плейлист"
        playlists = playlist_cache.get(user_id)
        if playlists:
            for pl in playlists:
                if pl.get("kind") == kind:
                    playlist_title = pl.get("title", "Плейлист")
                    break
        
        # Формируем текст
        text = (
            f"🎵 <b>{playlist_title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Треки {start_idx + 1}-{end_idx} из {total_tracks}\n"
            f"📄 Страница {page + 1}/{total_pages}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        # Добавляем треки
        for i, track in enumerate(current_tracks, start=start_idx + 1):
            # Извлекаем информацию о треке безопасно
            title = getattr(track, 'title', 'Без названия')
            
            # Обрабатываем артистов
            artists = []
            try:
                artists_list = getattr(track, 'artists', [])
                if artists_list:
                    artists = [getattr(a, 'name', '') for a in artists_list if hasattr(a, 'name')]
            except:
                pass
            
            artist_names = ", ".join(filter(None, artists)) or "Неизвестный исполнитель"
            
            # Форматируем длительность
            duration = ""
            try:
                duration_ms = getattr(track, 'duration_ms', None)
                if duration_ms:
                    minutes = duration_ms // 60000
                    seconds = (duration_ms // 1000) % 60
                    duration = f"{minutes}:{seconds:02d}"
            except:
                pass
            
            # Форматируем альбом
            album_name = ""
            try:
                album = getattr(track, 'album', None)
                if album:
                    album_name = getattr(album, 'title', '')
            except:
                pass
            
            # Добавляем строку с треком
            text += f"<b>{i}. {title}</b>\n"
            if artist_names:
                text += f"   🎤 {artist_names}\n"
            if album_name:
                text += f"   💿 {album_name}\n"
            if duration:
                text += f"   ⏳ {duration}\n"
            text += "\n"
        
        # Создаем клавиатуру
        kb_buttons = []
        
        # Навигация
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"pl_open:{user_id}:{kind}:{page-1}"
            ))
        
        nav_row.append(InlineKeyboardButton(
            text="📋 К плейлистам",
            callback_data="show_playlists"
        ))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=f"pl_open:{user_id}:{kind}:{page+1}"
            ))
        
        if nav_row:
            kb_buttons.append(nav_row)
        
        # Быстрая навигация по страницам
        if total_pages > 1:
            quick_nav = []
            max_buttons = min(5, total_pages)
            start_page = max(0, page - max_buttons // 2)
            end_page = min(total_pages, start_page + max_buttons)
            
            if end_page - start_page < max_buttons and start_page > 0:
                start_page = max(0, end_page - max_buttons)
            
            for p in range(start_page, end_page):
                if p == page:
                    quick_nav.append(InlineKeyboardButton(
                        text=f"• {p+1} •",
                        callback_data=f"pl_open:{user_id}:{kind}:{p}"
                    ))
                else:
                    quick_nav.append(InlineKeyboardButton(
                        text=str(p+1),
                        callback_data=f"pl_open:{user_id}:{kind}:{p}"
                    ))
            
            if quick_nav:
                kb_buttons.append(quick_nav)
        
        # Кнопки управления
        kb_buttons.append([
            InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_music")
        ])
        
        # Отправляем сообщение
        try:
            await status_msg.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await status_msg.delete()
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения с треками: {e}")
            await message.answer(
                "❌ Не удалось отобразить треки. Попробуйте позже."
            )
    
    except Exception as e:
        logger.error(f"Ошибка загрузки треков плейлиста: {e}", exc_info=True)
        
        try:
            await status_msg.edit_text(
                f"❌ Ошибка загрузки треков:\n<code>{str(e)[:100]}</code>",
                parse_mode="HTML"
            )
        except:
            await message.answer(
                f"❌ Ошибка загрузки треков: {str(e)[:100]}"
            )

@router.callback_query(F.data == "refresh_playlists")
async def refresh_playlists_callback(callback: CallbackQuery):
    """Обновить список плейлистов"""
    await callback.answer("🔄 Обновляю...")
    user_id = callback.from_user.id
    playlist_cache.clear(user_id)
    await show_playlists_page(callback.message, user_id, page=0, force_refresh=True)

@router.callback_query(F.data == "all_tracks")
async def all_tracks_callback(callback: CallbackQuery):
    """Показать все треки (заглушка)"""
    await callback.answer("📋 Эта функция в разработке")

# Дополнительная команда для дебага
@router.message(Command("debug_playlists"))
@require_auth
async def debug_playlists(message: Message):
    """Команда для отладки плейлистов"""
    user_id = _effective_user_id_from_message(message)
    token = get_token(user_id)
    
    debug_info = []
    
    if not token:
        debug_info.append("❌ Токен отсутствует")
    else:
        debug_info.append(f"✅ Токен: {token[:10]}...")
        
        # Проверяем кэш
        cached = playlist_cache.get(user_id)
        if cached:
            debug_info.append(f"📂 В кэше: {len(cached)} плейлистов")
            for i, pl in enumerate(cached[:3]):
                debug_info.append(f"  {i+1}. {pl.get('title')} (kind: {pl.get('kind')})")
        else:
            debug_info.append("📭 Кэш пуст")
        
        # Пробуем получить информацию напрямую
        try:
            from yandex_music import Client
            client = Client(token)
            account = client.account_status()
            if account and account.account:
                debug_info.append(f"👤 Аккаунт: {account.account.login} (uid: {account.account.uid})")
                
                # Пробуем получить плейлисты напрямую
                try:
                    playlists = client.users_playlists(account.account.uid)
                    debug_info.append(f"🎵 Прямой запрос: {len(playlists) if playlists else 0} плейлистов")
                except Exception as e:
                    debug_info.append(f"❌ Ошибка прямого запроса: {str(e)[:100]}")
            else:
                debug_info.append("❌ Не удалось получить информацию об аккаунте")
        except Exception as e:
            debug_info.append(f"❌ Ошибка создания клиента: {str(e)[:100]}")
    
    await message.answer(
        "\n".join(debug_info),
        parse_mode="HTML"
    )