from uuid import UUID, uuid4

from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Column, LargeBinary, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.session import sessionmaker

engine = create_engine("sqlite:///:memory:")

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

    def write(self):
        session = Session()
        session.add(self)
        session.commit()
        session.close()

    uuid = Column(String, primary_key=True)
    username = Column(String)
    hash = Column(LargeBinary)


class User(BaseModel):
    """
    The main class used to interface with user data.
    """

    uuid: UUID
    username: str
    hash: bytes

    def write(self):
        _DBUser.from_user(self).write()


Base.metadata.create_all(engine)


class Credentials(BaseModel):
    """
    Used to validate user-inputted credentials or register new accounts.
    """

    username: str
    password: str

    def register(self) -> User:
        pw_hash = pwd_context.hash(self.password)
        return User(uuid=uuid4(), username=self.username, hash=pw_hash)

    def validate(self, user: User) -> bool:
        return pwd_context.verify(self.password, user.hash)
