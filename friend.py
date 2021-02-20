from typing import List

from dataclasses import dataclass
from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import Session, relationship

from database import Base, NonUniqueException, engine, session_manager


class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer)
    confirmed = Column(Boolean, default=False)

    user = relationship("_DBUser", back_populates="friends")

    @classmethod
    def find(cls, id: str) -> "Optional[List[FriendRelationship]]":
        with session_manager() as session:
            return cls.query(id, session)

    @classmethod
    def query(cls, id: int, session: Session) -> "Optional[_Friend]":
        friends = [x for x in session.query(Friend).filter_by(user_id=id)]
        friends += [x for x in session.query(Friend).filter_by(friend_id=id)]
        return friends

    @classmethod
    def query_both(
        cls, user_id: int, friend_id: int, session: Session
    ) -> "Optional[_Friend]":
        friends = [
            x
            for x in session.query(Friend).filter_by(
                user_id=user_id, friend_id=friend_id
            )
        ]
        if len(friends) == 0:
            return
        if len(friends) > 1:
            return NonUniqueException
        return friends[0]

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()


Base.metadata.create_all(engine)
