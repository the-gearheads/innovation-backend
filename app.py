import uvicorn

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from user import Credentials

app = Starlette()


@app.route("/")
async def index(_: Request) -> PlainTextResponse:
    return PlainTextResponse("Hello, world!")


def test():
    credentials = Credentials(username="john", password="password")
    user = credentials.register()
    user.write()
    assert credentials.validate(user)


if __name__ == "__main__":
    test()
    uvicorn.run(app, host="0.0.0.0", port=8000)
