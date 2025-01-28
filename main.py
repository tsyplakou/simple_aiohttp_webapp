from aiohttp import web

from app.middlewares import jwt_auth_middleware
from app.routes import setup_routes
from app.db import Database
from app.config import DATABASE


async def init_app():
    app = web.Application(middlewares=[jwt_auth_middleware])

    db = Database(
        dsn="postgresql://{user}:{password}@{host}:{port}/{database}".format(
            **DATABASE
        )
    )
    await db.connect()
    app["db"] = db

    setup_routes(app)

    return app


web.run_app(init_app())
