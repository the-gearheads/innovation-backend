from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Session, relationship

from database import Base, NonUniqueException, engine, session_manager
from user import User


class SessionInfo(Base):
    __tablename__ = "session"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String)

    user = relationship("_DBUser", back_populates="session_info")

    def __eq__(self, other):
        return (
            self.user_id == other.user_id
            and self.id == other.id
            and self.token == other.token
        )

    @classmethod
    def find(cls, token: str) -> "Optional[_DBUser]":
        with session_manager() as session:
            session_info = cls.query(token, session)
            if not session_info:
                return
            return User.from_db(session_info.user)

    @classmethod
    def query(cls, token: str, session: Session) -> "Optional[User]":
        sessions = [x for x in session.query(SessionInfo).filter_by(token=token)]
        if len(sessions) == 0:
            return
        if len(sessions) > 1:
            return NonUniqueException
        session_info = sessions[0]
        return session_info

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()


Base.metadata.create_all(engine)
