from uuid import UUID, uuid4

from typing import Optional
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, LargeBinary, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker

from starlette.authentication import BaseUser

engine = create_engine("sqlite:///:memory:", echo=True)

Base = declarative_base()

Session = sessionmaker()
Session.configure(bind=engine)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class _DBUser(Base):
    """
    User data as stored in the database.
    """

    __tablename__ = "users"

    @classmethod
    def from_user(cls, user: "User") -> "_DBUser":
        return cls(uuid=str(user.uuid), username=user.username, hash=user.hash)

    @classmethod
    def from_username(cls, username: str) -> Optional["_DBUser"]:
        session = Session()
        users = [x for x in session.query(_DBUser).filter_by(username=username)]
        if len(users) == 0:
            return
        if len(users) > 1:
            return Exception("Multiple users with same username")  # TODO: Handle better
        user = users[0]
        return cls(uuid=str(user.uuid), username=user.username, hash=user.hash)

    @classmethod
    def from_uuid(cls, uuid: str) -> Optional["_DBUser"]:
        session = Session()
        users = [x for x in session.query(_DBUser).filter_by(uuid=uuid)]
        if len(users) == 0:
            return
        if len(users) > 1:
            return Exception("Multiple users with same UUID")  # TODO: Handle better
        user = users[0]
        return cls(uuid=str(user.uuid), username=user.username, hash=user.hash)

    def write(self):
        session = Session()
        session.add(self)
        session.commit()
        session.close()

    uuid = Column(String, primary_key=True)
    username = Column(String)
    hash = Column(LargeBinary)


class User(BaseUser, BaseModel):
    """
    The main class used to interface with user data.
    """

    uuid: UUID
    username: str
    hash: bytes

    def write(self):
        _DBUser.from_user(self).write()

    @property
    def is_authenticated(self):
        return True

    @property
    def display_name(self):
        return self.username

    @classmethod
    def from_dbuser(cls, user: _DBUser):
        print(user)
        return cls(uuid=UUID(user.uuid), username=user.username, hash=user.hash)


Base.metadata.create_all(engine)


# TODO: refactor out
class Credentials(BaseModel):
    """
    Used to validate user-inputted credentials or register new accounts.
    """

    username: str
    password: str

    def register(self) -> User:
        pw_hash = pwd_context.hash(self.password)
        return User(uuid=uuid4(), username=self.username, hash=pw_hash)

    def from_db(self) -> Optional[User]:
        user = _DBUser.from_username(self.username)
        if not user:
            return
        return User.from_dbuser(user)

    def check_password(self, user: User) -> bool:
        return pwd_context.verify(self.password, user.hash)
