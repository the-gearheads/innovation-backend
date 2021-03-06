from base64 import b64encode
from dataclasses import dataclass
from os import urandom
from typing import List, Optional

from passlib.hash import bcrypt
from starlette.authentication import BaseUser

from database import _DBUser, session_manager


@dataclass
class User(BaseUser):
    """
    The main class used to interface with user data.
    """

    id: int
    username: str
    hash: bytes
    session_info: "List[SessionInfo]"
    friends: "List[Friend]"
    sessions: "List[GameSession]"
    points: int

    _authenticated: bool = False
    _auth_with: str = None

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented

        return (
            self.id == other.id
            and self.username == other.username
            and self.hash == other.hash
        )

    @classmethod
    def from_db(cls, db_user: _DBUser) -> "User":
        return cls(
            id=db_user.id,
            username=db_user.username,
            hash=db_user.hash,
            session_info=list(db_user.session_info),
            friends=list(db_user.friends),
            sessions=list(db_user.sessions),
            points=db_user.points,
        )

    @property
    def is_authenticated(self):
        return self._authenticated

    @property
    def display_name(self):
        return self.username

    @classmethod
    def register(cls, username, password) -> "User":
        hash = bcrypt.using(rounds=8).hash(password)
        db_user = _DBUser(username=username, hash=hash)
        return cls.from_db(db_user)

    @classmethod
    def find(cls, session=None, **kwargs) -> "Optional[User]":
        with session_manager() as session:
            db_user = _DBUser.query_unique(session, kwargs)
            if not db_user:
                return
            return cls.from_db(db_user)

    def write(self):
        with session_manager() as session:
            _DBUser.from_user(self).write(session)

    def authenticate(self, password) -> bool:
        if bcrypt.verify(password, self.hash):
            self._authenticated = True
        return self._authenticated

    def set_authenticated(self, authenticated=True, token=None) -> bool:
        if token:
            self._auth_with = token
        self._authenticated = authenticated

    @property
    def token(self) -> "Optional[str]":
        return self._auth_with

    def new_token(self) -> str:
        from session import SessionInfo

        token = b64encode(urandom(128)).decode("utf-8")
        session_info = SessionInfo(user_id=self.id, token=token)
        self.session_info.append(session_info)
        with session_manager() as session:
            session_info.write(session)
        return token

    def new_friend(self, friend_id: int):
        from friend import Friend

        friend = Friend(user_id=self.id, friend_id=friend_id)
        with session_manager() as session:
            if Friend.query_both(user_id=self.id, friend_id=friend_id, session=session):
                return
            self.friends.append(friend)
            friend.write(session)
