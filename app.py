from typing import List
from time import sleep
from threading import Thread

import schedule
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    UnauthenticatedUser,
    requires,
)
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, Response

from database import GameSession, _DBUser
from friend import Friend
from session import SessionInfo
from user import User, session_manager


class SessionAuth(AuthenticationBackend):
    async def authenticate(self, request: HTTPConnection):
        token = request.cookies.get("session")
        if not token:
            return
        user = SessionInfo.find(token)
        if not user:
            return
        user.set_authenticated(token=token)
        return AuthCredentials(["authenticated"]), user


middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"]),
    Middleware(AuthenticationMiddleware, backend=SessionAuth()),
]

app = FastAPI(middleware=middleware)


class Credentials(BaseModel):
    username: str
    password: str


class FriendForm(BaseModel):
    username: str


class SessionCreateForm(BaseModel):
    users: List[str]
    name: str


class AttackForm(BaseModel):
    id: int
    damage: int


def renew(response: Response, token: str = None):
    if not token:
        return response
    # two week expiry
    response.set_cookie(
        "session", token, max_age=(3600 * 24 * 14), samesite="none", secure=True
    )
    return response


@app.post("/login")
async def login(_: Request, form: Credentials) -> JSONResponse:
    tests()
    user = User.find(username=form.username)
    if not user:
        raise HTTPException(403, "Invalid username or password")
    user.authenticate(form.password)
    if not user.is_authenticated:
        raise HTTPException(403, "Invalid username or password")
    token = user.new_token()
    response = JSONResponse({"success": True})
    return renew(response, token)


@app.post("/register")
async def register(form: Credentials) -> JSONResponse:
    if User.find(username=form.username):
        raise HTTPException(400, "User with this username already exists")
    user = User.register(form.username, form.password)
    user.write()
    return JSONResponse({"success": True})


@app.post("/add_friend")
@requires("authenticated")
async def add_friend(request: Request, friend_form: FriendForm) -> JSONResponse:
    id = User.find(username=friend_form.username).id
    request.user.new_friend(id)
    return renew(JSONResponse({"success": True}), request.user.token)


@app.post("/accept_friend")
@requires("authenticated")
async def accept_friend(request: Request, friend_form: FriendForm) -> JSONResponse:
    with session_manager() as session:
        friend = Friend.query_both(
            user_id=User.find(username=friend_form.username).id,
            friend_id=request.user.id,
            session=session,
        )
        friend.confirmed = True
        friend.write(session=session)
    return renew(JSONResponse({"success": True}))


@app.get("/friends_list")
@requires("authenticated")
async def friends_list(request: Request) -> JSONResponse:
    friends = Friend.find(id=request.user.id) or []
    friends_list = []
    for friend in friends:
        # if not accepted, don't show on requester's side
        if friend.user_id == request.user.id and not friend.confirmed:
            continue
        if friend.user_id == request.user.id:
            if not friend.confirmed:
                continue
            friend_id = friend.friend_id
        else:
            friend_id = friend.user_id
        friends_list.append(
            {
                "id": friend_id,
                "name": User.find(id=friend_id).username,
                "confirmed": friend.confirmed,
            }
        )
    return renew(
        JSONResponse({"success": True, "friends": friends_list}), request.user.token
    )


@app.post("/create_session")
@requires("authenticated")
async def create_session(request: Request, form: SessionCreateForm):
    users = []
    with session_manager() as session:
        for user in form.users:
            user = _DBUser.query_unique(session, {"username": user})
            users.append(user)
        users.append(_DBUser.query_unique(session, {"username": request.user.username}))
        game_session = GameSession(name=form.name, users=users)
        game_session.write(session)
    return renew(JSONResponse({"success": True}), request.user.token)


@app.post("/attack")
@requires("authenticated")
async def attack(request: Request, form: AttackForm):
    with session_manager() as session:
        game_session = GameSession.find(session, id=form.id)
        game_session.bossHealth -= form.damage
        game_session.write(session)
        return renew(
            JSONResponse({"success": True, **game_session.as_dict()}),
            request.user.token,
        )


@app.get("/sessions")
@requires("authenticated")
async def sessions(request: Request):
    sessions = [session.as_dict() for session in request.user.sessions]
    return renew(
        JSONResponse({"success": True, "sessions": sessions}),
        request.user.token,
    )


@app.get("/logout")
@requires("authenticated")
async def logout(request: Request) -> JSONResponse:
    with session_manager() as session:
        session_info = SessionInfo.query(request.user.token, session)
        if session_info:
            request.user.session_info.remove(session_info)
        session_info.delete(session)
    del request.cookies["session"]
    return JSONResponse({"success": True})


TESTS = False


def tests():  # ""tests""
    global TESTS
    if TESTS:
        return
    TESTS = True

    user = User.register("john", "password")
    user.write()
    user2 = User.register("pog", "champ")
    user2.write()

    user = User.find(username="john")
    user2 = User.find(username="pog")
    token = user.new_token()

    user.new_friend(user2.id)

    assert user.authenticate("password")
    assert User.from_db(SessionInfo.find(token)) == user


if __name__ == "__main__":
    tests()
    uvicorn.run(app, host="0.0.0.0", port=8080)
