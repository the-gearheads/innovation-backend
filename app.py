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

from user import User, session_manager
from session import SessionInfo


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


def renew(response: Response, token: str = None):
    if not token:
        return response
    # two week expiry
    response.set_cookie("session", token, max_age=(3600 * 24 * 14))
    return response


@app.post("/login")
async def login(_: Request, form: Credentials) -> JSONResponse:
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


@app.get("/get")
@requires("authenticated")
async def get(request: Request) -> JSONResponse:
    return renew(JSONResponse({"success": True, "value": 10}), request.user.token)


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


def tests():  # ""tests""
    user = User.register("john", "password")
    user.write()

    user = User.find(username="john")
    token = user.new_token()

    assert user.authenticate("password")
    assert User.from_db(SessionInfo.find(token)) == user


if __name__ == "__main__":
    tests()
    uvicorn.run(app, host="0.0.0.0", port=8080)
