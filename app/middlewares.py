from aiohttp import web
from .utils import decode_jwt


@web.middleware
async def jwt_auth_middleware(request, handler):
    if request.path in ["/login", "/register"]:
        return await handler(request)

    token = request.cookies.get("jwt_token")
    if not token:
        raise web.HTTPUnauthorized(text="Authorization header is missing or invalid")

    try:
        user_payload = decode_jwt(token)
        request["user_id"] = user_payload["user_id"]
    except Exception as e:
        raise web.HTTPUnauthorized(text=str(e))

    return await handler(request)
