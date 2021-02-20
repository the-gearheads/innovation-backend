from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import Session, relationship

from database import Base, NonUniqueException, engine, session_manager
from dataclasses import dataclass

from typing import List


@dataclass
class FriendRelationship:
    friends: List[int]
    confirmed: bool


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
            friend_list = cls.query(id, session)
            if not friend_list:
                return
            friends = []
            for i in friend_list:
                friends.append(
                    FriendRelationship(
                        friends=[i.user_id, i.friend_id], confirmed=i.confirmed
                    )
                )
            return friends

    @classmethod
    def query(cls, id: int, session: Session) -> "Optional[_Friend]":
        sessions = [x for x in session.query(Friend).filter_by(user_id=id)]
        sessions += [x for x in session.query(Friend).filter_by(friend_id=id)]
        return sessions

    def write(self, session: Session):
        session.add(self)
        session.commit()

    def delete(self, session: Session):
        session.delete(self)
        session.commit()


Base.metadata.create_all(engine)
