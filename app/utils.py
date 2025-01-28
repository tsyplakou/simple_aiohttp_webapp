from datetime import datetime, timedelta

import bcrypt
import jwt
from aiohttp import web

from .config import SECRET_KEY


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_jwt(payload, expires_in=60):
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_in)
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_jwt(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise web.HTTPUnauthorized(text="Token has expired")
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(text="Invalid token")
