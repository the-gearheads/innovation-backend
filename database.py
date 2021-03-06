from contextlib import contextmanager
from math import floor
from time import time
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
)
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
    points = Column(Integer, default=0)
    avatar = Column(String, default="default")  # url to avatar

    @classmethod
    def from_user(cls, user: "User") -> "_DBUser":
        return cls(
            id=user.id,
            username=user.username,
            hash=user.hash,
            session_info=user.session_info,
            friends=user.friends,
            sessions=user.sessions,
            points=user.points,
            avatar=user.avatar,
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
    startTime = Column(Float, default=time)
    tag = Column(String)

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
            "tag": self.tag,
            **self.exercises,
        }

    @property
    def exercises(self) -> Dict:
        tag = {self.tag: True}
        exercises = {}
        with session_manager() as session:
            exercises["beginner"] = [
                x.name for x in Exercise.query(session, difficulty="beginner", **tag)
            ]
            exercises["intermediate"] = [
                x.name
                for x in Exercise.query(session, difficulty="intermediate", **tag)
            ]
            exercises["advanced"] = [
                x.name for x in Exercise.query(session, difficulty="advanced", **tag)
            ]
            return exercises

    @property
    def partyHealth(self):
        day = 24 * 60 * 60
        delta = time() - self.startTime
        return 1000 - (100 * floor(delta / day))

    def check_status(self):
        if self.partyHealth > 0:
            return True
        with session_manager() as session:
            self.delete(session)
        return False

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def delete(self, session: Session):
        self.users.clear()
        session.add(self)
        session.delete(self)
        session.commit()


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    difficulty = Column(String)
    core = Column(Boolean)
    lower_body = Column(Boolean)
    upper_body = Column(Boolean)
    balance = Column(Boolean)
    cardiovascular = Column(Boolean)

    @classmethod
    def create(cls, name, tags, difficulty) -> "Exercise":
        return cls(
            name=name,
            difficulty=difficulty,
            core="C" in tags,
            lower_body="L" in tags,
            upper_body="U" in tags,
            balance="B" in tags,
            cardiovascular="V" in tags,
        )

    @classmethod
    def query(cls, session: Session, **kwargs) -> "List[Exercise]":
        return [x for x in session.query(Exercise).filter_by(**kwargs)]

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def __repr__(self):
        return f"<Exercise {self.name}/{self.difficulty}>"


Base.metadata.create_all(engine)
