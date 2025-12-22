from sqlalchemy.orm import sessionmaker

from .repository import engine, UserToken

SessionLocal = sessionmaker(bind=engine)


def set_token(user_id: int, token: str) -> None:
    """Сохранить токен пользователя (upsert по user_id)."""
    nickname = str(user_id)
    with SessionLocal() as session:
        row = session.get(UserToken, nickname)
        if row is None:
            session.add(UserToken(nickname=nickname, token=token))
        else:
            row.token = token
        session.commit()


def get_token(user_id: int) -> str | None:
    """Получить токен пользователя."""
    nickname = str(user_id)
    with SessionLocal() as session:
        row = session.get(UserToken, nickname)
        return None if row is None else row.token


def has_token(user_id: int) -> bool:
    """Проверить наличие токена у пользователя."""
    nickname = str(user_id)
    with SessionLocal() as session:
        return session.get(UserToken, nickname) is not None


def remove_token(user_id: int) -> None:
    """Удалить токен пользователя."""
    nickname = str(user_id)
    with SessionLocal() as session:
        row = session.get(UserToken, nickname)
        if row is not None:
            session.delete(row)
            session.commit()
