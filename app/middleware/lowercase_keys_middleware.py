# app/middleware/lowercase_keys_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import json

class LowercaseKeysMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            # Read the body
            body_bytes = await request.body()
            if body_bytes:
                # Parse JSON
                json_body = json.loads(body_bytes)
                if isinstance(json_body, dict):
                    # Lowercase keys
                    json_body = {k.lower(): v for k, v in json_body.items()}
                    # Serialize back to JSON
                    body_bytes = json.dumps(json_body).encode('utf-8')
                # Define a new receive method
                async def receive():
                    return {'type': 'http.request', 'body': body_bytes}
                # Replace the request's receive method
                request._receive = receive
        response = await call_next(request)
        return response
