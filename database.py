from contextlib import contextmanager
from typing import Dict, List, Optional

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

engine = create_engine("sqlite:///:memory:")

Base = declarative_base()


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

    @classmethod
    def from_user(cls, user: "User") -> "_DBUser":
        return cls(
            id=user.id,
            username=user.username,
            hash=user.hash,
            session_info=user.session_info,
            friends=user.friends,
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


Base.metadata.create_all(engine)
