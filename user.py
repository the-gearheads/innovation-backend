from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from passlib.context import CryptContext
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from starlette.authentication import BaseUser

engine = create_engine("sqlite:///:memory:")

Base = declarative_base()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class NonUniqueException(Exception):
    pass


@contextmanager
def session_manager():
    session = Session(engine)
    try:
        yield session
    except:
        session.rollback()
        raise
    finally:
        session.close()


class _DBUser(Base):
    """
    User data as stored in the database.
    """

    __tablename__ = "users"

    @classmethod
    def from_user(cls, user: "User") -> "_DBUser":
        return cls(uuid=str(user.uuid), username=user.username, hash=user.hash)

    def to_user(self) -> "User":
        return User(uuid=UUID(self.uuid), username=self.username, hash=self.hash)

    @classmethod
    def query_unique(cls, session: Session, query: Dict[str, str]) -> Optional[_DBUser]:
        users = cls.query(session, query)
        if len(users) == 0:
            return
        if len(users) > 1:
            return NonUniqueException
        user = users[0]
        return cls(uuid=str(user.uuid), username=user.username, hash=user.hash)

    @classmethod
    def query(cls, session: Session, query: Dict[str, str]) -> List[_DBUser]:
        return [x for x in session.query(_DBUser).filter_by(**query)]

    def write(self, session: Session):
        session.add(self)
        session.commit()

    uuid = Column(String, primary_key=True)
    username = Column(String)
    hash = Column(String)


Base.metadata.create_all(engine)


@dataclass
class User(BaseUser):
    """
    The main class used to interface with user data.
    """

    uuid: UUID
    username: str
    hash: bytes
    _authenticated: bool = False

    @property
    def is_authenticated(self):
        return self._authenticated

    @property
    def display_name(self):
        return self.username

    @classmethod
    def register(cls, username, password) -> "User":
        pw_hash = pwd_context.hash(password)
        return cls(uuid=uuid4(), username=username, hash=pw_hash)

    @classmethod
    def from_db(cls, **kwargs) -> Optional["User"]:
        with session_manager() as session:
            db_user = _DBUser.query_unique(session, kwargs)
            if not db_user:
                return
            return db_user.to_user()

    def write(self):
        with session_manager() as session:
            _DBUser.from_user(self).write(session)

    def authenticate(self, password) -> bool:
        if pwd_context.verify(password, self.hash):
            self._authenticated = True
        return self._authenticated

    def set_authenticated(self, authenticated=True) -> bool:
        self._authenticated = authenticated
