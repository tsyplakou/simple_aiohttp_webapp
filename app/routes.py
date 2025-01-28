from .handlers import register_user, login_user, create_task, get_tasks, update_task, get_task


def setup_routes(app):
    app.router.add_post("/register", register_user)
    app.router.add_post("/login", login_user)
    app.router.add_post("/tasks", create_task)
    app.router.add_get("/tasks", get_tasks)

    app.router.add_get("/tasks/{task_id:\\d+}/", get_task)
    app.router.add_put("/tasks/{task_id:\\d+}/", update_task)
