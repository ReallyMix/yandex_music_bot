# Глобальное хранилище токенов {user_id: token}
user_tokens = {}

def set_token(user_id: int, token: str) -> None:
    """Сохранить токен пользователя"""
    user_tokens[user_id] = token

def get_token(user_id: int) -> str | None:
    """Получить токен пользователя"""
    return user_tokens.get(user_id)

def has_token(user_id: int) -> bool:
    """Проверить наличие токена у пользователя"""
    return user_id in user_tokens

def remove_token(user_id: int) -> None:
    """Удалить токен пользователя"""
    user_tokens.pop(user_id, None)