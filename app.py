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
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from user import User


class SessionAuth(AuthenticationBackend):
    async def authenticate(self, request):
        uuid = request.session.get("uuid")
        if not uuid:
            return
        user = User.from_db(uuid=uuid)
        if not user:
            return
        user.set_authenticated()
        return AuthCredentials(["authenticated"]), user


middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"]),
    Middleware(SessionMiddleware, secret_key="{F$f]G/V09;u"),
    Middleware(AuthenticationMiddleware, backend=SessionAuth()),
]

app = FastAPI(middleware=middleware)


class Credentials(BaseModel):
    username: str
    password: str


@app.post("/login")
async def login(request: Request, form: Credentials) -> JSONResponse:
    user = User.from_db(username=form.username)
    if not user:
        raise HTTPException(403, "Invalid username or password")
    user.authenticate(form.password)
    if not user.is_authenticated:
        raise HTTPException(403, "Invalid username or password")
    request.session.update({"uuid": str(user.uuid)})  # TODO: implement actual tokens
    return JSONResponse({"success": True})


@app.post("/register")
async def register(form: Credentials) -> JSONResponse:
    if User.from_db(username=form.username):
        raise HTTPException(400, "User with this username already exists")
    user = User.register(form.username, form.password)
    user.write()
    return JSONResponse({"success": True})


@app.get("/get")
@requires("authenticated")
async def get(request: Request) -> JSONResponse:
    return JSONResponse({"success": True, "value": 10})


@app.get("/logout")
async def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"success": True})


def fake_users():
    User.register("john", "password").write()
    user = User.from_db(username="john")
    assert user.authenticate("password")


if __name__ == "__main__":
    fake_users()
    uvicorn.run(app, host="0.0.0.0", port=8000)
