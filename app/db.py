import asyncpg
from typing import List, Dict, Optional


class Database:
    def __init__(self, dsn: str):
        """
        Инициализация базы данных.
        :param dsn: Строка подключения к базе данных (DSN).
        """
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        """
        Устанавливает подключение к базе данных через пул соединений.
        """
        self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def close(self):
        """
        Закрывает пул соединений с базой данных.
        """
        if self.pool:
            await self.pool.close()

    # Пользователи

    async def create_user(self, email: str, password: str) -> int:
        """
        Создаёт нового пользователя.
        :param email: Email пользователя.
        :param password: Хэш пароля пользователя.
        :return: ID созданного пользователя.
        """
        query = """
        INSERT INTO users (email, password)
        VALUES ($1, $2)
        RETURNING id;
        """
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(query, email, password)
            return user_id

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Получает пользователя по email.
        :param email: Email пользователя.
        :return: Данные пользователя или None.
        """
        query = """
        SELECT id, email, password
        FROM users
        WHERE email = $1;
        """
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(query, email)
            return dict(user) if user else None

    # Задачи

    async def create_task(
        self,
        name: str,
        description: str,
        status: str,
        user_id: int,
        expiration_date: Optional[str],
        priority: int,
    ) -> int:
        """
        Создаёт новую задачу.
        :param name: Название задачи.
        :param description: Описание задачи.
        :param status: Статус задачи.
        :param user_id: ID пользователя, создавшего задачу.
        :param expiration_date: Дата завершения задачи (опционально).
        :param priority: Приоритет задачи (от 1 до 10).
        :return: ID созданной задачи.
        """
        query = """
        INSERT INTO tasks (name, description, status, user_id, expiration_date, priority, last_status_modified)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        RETURNING id;
        """
        async with self.pool.acquire() as conn:
            task_id = await conn.fetchval(query, name, description, status, user_id, expiration_date, priority)
            return task_id

    async def get_tasks(self, user_id: int) -> List[Dict]:
        """
        Получает список задач для пользователя.
        :param user_id: ID пользователя.
        :return: Список задач.
        """
        query = """
        SELECT id, name, description, status, created, last_status_modified, expiration_date, priority
        FROM tasks
        WHERE user_id = $1
        
        ORDER BY 
            CASE status
                WHEN 'in_progress' THEN 1
                WHEN 'new' THEN 2
                WHEN 'done' THEN 3
            END ASC,
            priority DESC,
            last_status_modified DESC;
        """
        async with self.pool.acquire() as conn:
            tasks = await conn.fetch(query, user_id)
            return [dict(task) for task in tasks]

    async def get_tasks_by_statuses(self, user_id: int, statuses: List) -> List[Dict]:
        """
        Получает список задач для пользователя.
        :param user_id: ID пользователя.
        :return: Список задач.
        """
        query = """
        SELECT id, name, description, status, created, last_status_modified, expiration_date, priority
        FROM tasks
        WHERE user_id = $1 AND status = ANY($2::text[])
        ORDER BY 
            CASE status
                WHEN 'in_progress' THEN 1
                WHEN 'new' THEN 2
                WHEN 'done' THEN 3
            END ASC,
            priority DESC,
            last_status_modified DESC;
        """
        async with self.pool.acquire() as conn:
            tasks = await conn.fetch(query, user_id, statuses)
            return [dict(task) for task in tasks]

    async def get_task_by_id(self, user_id: int, task_id: int) -> Optional[Dict]:
        """
        Получает задачу по ID.
        :param task_id: ID задачи.
        :param user_id: ID пользователя (для проверки владельца задачи).
        :return: Данные задачи или None.
        """
        query = """
        SELECT id, name, description, status, created, last_status_modified, expiration_date, priority
        FROM tasks
        WHERE id = $1 AND user_id = $2;
        """
        async with self.pool.acquire() as conn:
            task = await conn.fetchrow(query, task_id, user_id)
            return dict(task) if task else None

    async def update_task(
        self,
        task_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        expiration_date: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> bool:
        """
        Обновляет задачу.
        :param task_id: ID задачи.
        :param user_id: ID пользователя (для проверки владельца задачи).
        :param name: Новое название.
        :param description: Новое описание.
        :param status: Новый статус.
        :param expiration_date: Новая дата завершения.
        :param priority: Новый приоритет.
        :return: True, если обновление успешно, иначе False.
        """
        fields = []
        values = []

        if name:
            fields.append("name = ${}".format(len(values) + 1))
            values.append(name)
        if description:
            fields.append("description = ${}".format(len(values) + 1))
            values.append(description)
        if status:
            fields.append("status = ${}".format(len(values) + 1))
            values.append(status)
            fields.append("last_status_modified = NOW()")  # Обновляем время статуса
        if expiration_date is not None:
            fields.append("expiration_date = ${}".format(len(values) + 1))
            values.append(expiration_date)
        else:
            fields.append("expiration_date = NULL")
        if priority:
            fields.append("priority = ${}".format(len(values) + 1))
            values.append(priority)

        if not fields:
            return False

        values.extend([task_id, user_id])  # Добавляем task_id и user_id в конец

        query = f"""
        UPDATE tasks
        SET {', '.join(fields)}
        WHERE id = ${len(values) - 1} AND user_id = ${len(values)};
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            return result == "UPDATE 1"

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Удаляет задачу.
        :param task_id: ID задачи.
        :param user_id: ID пользователя (для проверки владельца задачи).
        :return: True, если удаление успешно, иначе False.
        """
        query = """
        DELETE FROM tasks
        WHERE id = $1 AND user_id = $2;
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, task_id, user_id)
            return result == "DELETE 1"
