from sqlalchemy import create_engine, Column, String, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

engine = create_engine("sqlite:///yandex_music_bot.db", echo=True)
Base = declarative_base()

class UserToken(Base):
    __tablename__ = "user_tokens"

    nickname = Column(String, primary_key=True)
    token = Column(String, nullable=False)


Base.metadata.create_all(engine)
