from json.decoder import JSONDecodeError

import uvicorn
from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from user import Credentials

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"]),
    Middleware(SessionMiddleware, secret_key="lol"),
]

app = FastAPI(middleware=middleware)


@app.post("/login")
async def login(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except JSONDecodeError:
        raise HTTPException(400, "Request must be JSON")
    username = data["username"]
    password = data["password"]
    credentials = Credentials(username=username, password=password)
    user = credentials.from_db()
    if not user:
        raise HTTPException(403, "Invalid username or password")
    if not credentials.check_password(user):
        raise HTTPException(403, "Invalid username or password")
    request.session.update({"uuid": str(user.uuid)})
    return JSONResponse({"success": True})


@app.get("/get")
async def get(request: Request) -> JSONResponse:
    uuid = request.session["uuid"]
    return JSONResponse({"success": True, "uuid": uuid})


@app.post("/logout")
async def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"success": True})


@app.post("/register")
async def register(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except JSONDecodeError:
        raise HTTPException(400, "Request must be JSON")
    username = data["username"]
    password = data["password"]
    credentials = Credentials(username=username, password=password)
    user = credentials.register()
    if credentials.from_db():
        raise HTTPException(400, "User with this username already exists")
    user.write()
    return JSONResponse({"success": True})


def fake_users():
    credentials = Credentials(username="john", password="password")
    user = credentials.register()
    user.write()
    assert credentials.check_password(user)


if __name__ == "__main__":
    fake_users()
    uvicorn.run(app, host="0.0.0.0", port=8000)
