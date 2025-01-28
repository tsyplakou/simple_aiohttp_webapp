import json
from datetime import date
from enum import Enum

import asyncpg
from aiohttp import web

from .utils import hash_password, check_password, generate_jwt


def dumps(data):
    if isinstance(data, asyncpg.Record):
        return json.dumps(dict(data))
    elif isinstance(data, list):
        return json.dumps([dumps(item) for item in data])
    return json.dumps(data)


class StatusEnum(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"


async def register_user(request):
    data = await request.json()

    if not data.get("email") or not data.get("password"):
        raise web.HTTPBadRequest(text="Missing email or password")

    email = data.get("email")
    password = hash_password(data.get("password"))

    await request.app["db"].create_user(email, password)

    return web.json_response({
        "message": "User registered successfully",
    }, status=201)


async def login_user(request):
    data = await request.json()

    if not data.get("email") or not data.get("password"):
        raise web.HTTPBadRequest(text="Missing email or password")

    email = data.get("email")
    password = data.get("password")

    user_data = await request.app["db"].get_user_by_email(email)

    if (
        not user_data or
        not check_password(password, user_data["password"])
    ):
        raise web.HTTPUnauthorized(text="Invalid credentials")

    response = web.json_response({"message": "Login successful"})
    response.set_cookie(
        name="token",
        value=generate_jwt({"user_id": user_data["id"]}),
    )
    return response


class ValidationError(Exception):
    pass


def validate_task_data(data):
    for field, not_null in (
        ("name", True),
        ("description", True),
        ("status", True),
        ("expiration_date", False),
        ("priority", True),
    ):
        if field not in data or (not_null and data[field] is None):
            raise ValidationError(f"{field} is required")

    if data["status"] not in tuple(StatusEnum):
        raise ValidationError("Invalid status")


def deserialize_task(data):
    return {
        "name": data["name"],
        "description": data["description"],
        "status": StatusEnum(data["status"]).value,
        "expiration_date": (
            data["expiration_date"] and
            date.fromisoformat(data["expiration_date"])
        ),
        "priority": data["priority"],
    }


def serialize_task(data):
    return {
        "id": data["id"],
        "name": data["name"],
        "description": data["description"],
        "status": StatusEnum(data["status"]),
        "expiration_date": (
            data["expiration_date"] and
            data["expiration_date"].isoformat()
        ),
        "priority": data["priority"],
        "created": data["created"].isoformat(),
        "last_status_modified": data["last_status_modified"].isoformat(),
    }


async def create_task(request):
    user_id = request["user_id"]
    data = await request.json()

    try:
        validate_task_data(data)
    except ValidationError as e:
        raise web.HTTPBadRequest(text=str(e))

    if data.get("expiration_date"):
        expiration_date = date.fromisoformat(data["expiration_date"])
    else:
        expiration_date = None

    await request.app["db"].create_task(
        name=data["name"],
        description=data["description"],
        status=data["status"],
        user_id=user_id,
        expiration_date=expiration_date,
        priority=data["priority"],
    )

    return web.json_response({"message": "Task created successfully"})


async def get_tasks(request):
    user_id = request["user_id"]

    if request.query.get("status"):
        statuses = request.query.getall("status")
        tasks = await request.app["db"].get_tasks_by_statuses(user_id, statuses)
    else:
        tasks = await request.app["db"].get_tasks(user_id)

    for task in tasks:
        task = serialize_task(task)

    return web.json_response(tasks)


async def get_task(request):
    user_id = request["user_id"]
    task_id = request.match_info["task_id"]

    task = await request.app["db"].get_task_by_id(int(user_id), int(task_id))

    if task:
        return web.json_response(serialize_task(task))
    raise web.HTTPNotFound()


async def update_task(request):
    user_id = request["user_id"]
    task_id = request.match_info["task_id"]
    data = await request.json()

    task = await request.app["db"].get_task_by_id(int(user_id), int(task_id))
    if not task:
        raise web.HTTPNotFound()

    try:
        validate_task_data(data)
    except ValidationError as e:
        raise web.HTTPBadRequest(text=str(e))

    data = deserialize_task(data)

    await request.app["db"].update_task(
        task_id=int(task_id),
        user_id=int(user_id),
        **data,
    )

    return web.json_response({"message": "Task updated successfully"})
