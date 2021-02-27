from contextlib import contextmanager
from typing import Dict, List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

engine = create_engine("sqlite:///:memory:")

Base = declarative_base()

session_users = Table(
    "session_users",
    Base.metadata,
    Column("session_id", ForeignKey("gamesessions.id"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
)


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

    id = Column(Integer, primary_key=True)
    username = Column(String)
    hash = Column(String)
    session_info = relationship("SessionInfo")
    friends = relationship("Friend")
    sessions = relationship(
        "GameSession", secondary=session_users, back_populates="users"
    )

    @classmethod
    def from_user(cls, user: "User") -> "_DBUser":
        return cls(
            id=user.id,
            username=user.username,
            hash=user.hash,
            session_info=user.session_info,
            friends=user.friends,
            sessions=user.sessions,
        )

    @classmethod
    def query_unique(
        cls, session: Session, query: Dict[str, str]
    ) -> "Optional[_DBUser]":
        users = cls.query(session, query)
        if len(users) == 0:
            return
        if len(users) > 1:
            return NonUniqueException
        user = users[0]
        return user

    @classmethod
    def query(cls, session: Session, query: Dict[str, str]) -> "List[_DBUser]":
        return [x for x in session.query(_DBUser).filter_by(**query)]

    def write(self, session: Session):
        session.add(self)
        session.commit()


class GameSession(Base):
    __tablename__ = "gamesessions"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    bossHealth = Column(Integer, default=1000)
    partyHealth = Column(Integer, default=1000)

    users = relationship(
        "_DBUser", secondary=session_users, back_populates="sessions", lazy="joined"
    )

    @classmethod
    def find(cls, session: Session, **kwargs) -> "Optional[GameSession]":
        users = cls.query(session, kwargs)
        if len(users) == 0:
            return
        if len(users) > 1:
            return NonUniqueException
        user = users[0]
        return user

    @classmethod
    def query(cls, session: Session, query: Dict[str, str]) -> "List[GameSession]":
        return [x for x in session.query(GameSession).filter_by(**query)]

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bossHealth": self.bossHealth,
            "partyHealth": self.partyHealth,
            "users": [user.username for user in self.users],
        }

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()


Base.metadata.create_all(engine)
