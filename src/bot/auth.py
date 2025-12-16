"""
Управление аутентификацией пользователей
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Хранилище токенов в памяти
user_tokens: dict[int, str] = {}

def get_token(user_id: int) -> Optional[str]:
    """Получить токен пользователя"""
    return user_tokens.get(user_id)

def has_token(user_id: int) -> bool:
    """Проверить наличие токена у пользователя"""
    return user_id in user_tokens

def set_token(user_id: int, token: str) -> None:
    """Установить токен пользователя"""
    user_tokens[user_id] = token
    logger.info(f"Токен установлен для пользователя {user_id}")

def remove_token(user_id: int) -> None:
    """Удалить токен пользователя"""
    if user_id in user_tokens:
        del user_tokens[user_id]
        logger.info(f"Токен удалён для пользователя {user_id}")

def get_user_tokens() -> dict[int, str]:
    """Получить все токены (для отладки)"""
    return user_tokens.copy()