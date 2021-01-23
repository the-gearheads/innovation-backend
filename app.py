import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse

app = Starlette()


@app.route("/")
async def index(_: Request) -> PlainTextResponse:
    return PlainTextResponse("Hello, world!")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
