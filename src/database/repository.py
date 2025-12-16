from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

engine = create_engine('sqlite:///yandex_music_bot.db', echo=True)
Base = declarative_base()

class UserRepository(Base):
    __tablename__ = 'telegram_users'

    tg_id = Column(BigInteger, primary_key=True)
    
    username = Column(String)

    tokens = relationship("UserToken", back_populates="user")


class UserToken(Base):
    __tablename__ = 'user_tokens'

    token = Column(String, primary_key=True)

    user_tg_id = Column(BigInteger, ForeignKey('telegram_users.tg_id'))

    user = relationship("UserRepository", back_populates="tokens")
    service_info = relationship("UserRepository", back_populates="token_ref", uselist=False)


class UserRepository(Base):
    __tablename__ = 'service_data'

    token = Column(String, ForeignKey('user_tokens.token'), primary_key=True)
    
    data_field = Column(String)

    token_ref = relationship("UserToken", back_populates="service_info")

Base.metadata.create_all(engine)
