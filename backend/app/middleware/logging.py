import time
import logging

from fastapi import Request
from starlette.types import ASGIApp, Scope, Receive, Send, Message

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """
    ASGI middleware for logging HTTP requests and responses.
    Logs method, path, status code, duration, and client IP.
    Works at the ASGI level, avoiding issues with BaseHTTPMiddleware.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        client_ip = scope.get("client", ("unknown", 0))[0]
        forwarded = ""
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                forwarded = value.decode()
                break
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        method = scope.get("method", "")
        path = scope.get("path", "")

        response_status = None
        response_sent = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status, response_sent
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_sent = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            logger.exception(f"Request failed: {method} {path} - {str(e)}")
            raise
        finally:
            if response_status is not None:
                duration = time.time() - start_time
                log_message = f"{method} {path} - {response_status} ({duration:.3f}s) from {client_ip}"
                if response_status >= 500:
                    logger.error(log_message)
                elif response_status >= 400:
                    logger.warning(log_message)
                else:
                    logger.info(log_message)
            else:
                logger.warning(f"{method} {path} - No response status (client disconnected?) from {client_ip}")

