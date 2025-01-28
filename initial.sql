-- Таблица пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

-- Таблица задач
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created TIMESTAMP DEFAULT NOW(),
    last_status_modified TIMESTAMP NOT NULL,
    expiration_date date,
    priority INTEGER CHECK (priority >= 1 AND priority <= 10)
);
