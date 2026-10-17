from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.main import app
from starlette.types import ASGIApp, Scope, Receive, Send


class VercelPathFixMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            matched = (
                headers.get(b"x-matched-path")
                or headers.get(b"x-invoke-path")
                or headers.get(b"x-forwarded-path")
            )
            if matched:
                scope["path"] = matched.decode("utf-8")
            elif scope.get("path") in ("/api/index.py", "/api/index", "/api", "/api/"):
                scope["path"] = "/"
        await self.app(scope, receive, send)


app.add_middleware(VercelPathFixMiddleware)