# Двухсервисная система LLM-консультаций

Распределённая система из двух независимых сервисов: Auth Service (регистрация и выпуск JWT) и Bot Service (Telegram-бот + LLM через очередь задач).

## Архитектура

```mermaid
flowchart TB
    U[Пользователь]

    subgraph EntryPoints[Точки входа]
        AUTH[Swagger Auth Service]
        TG[Telegram Bot]
    end

    subgraph Storage[Хранилище состояния]
        R[(Redis)]
    end

    subgraph AsyncLayer[Асинхронная обработка]
        MQ[[RabbitMQ]]
        CW[Celery Worker]
    end

    subgraph External[Внешний LLM-провайдер]
        OR[OpenRouter LLM]
    end

    U -->|Регистрация / логин| AUTH
    AUTH -->|JWT токен| U

    U -->|/token JWT| TG
    TG -->|Сохраняет токен пользователя| R

    U -->|Текстовый вопрос| TG
    TG -->|Проверяет наличие / валидность JWT| R

    TG -->|Создаёт задачу на обработку| MQ
    MQ -->|Передаёт задачу| CW

    CW -->|Отправляет prompt| OR
    OR -->|LLM-ответ| CW

    CW -->|sendMessage напрямую| TG
    TG -->|Ответ в Telegram| U
```

**Сценарий работы:**
1. Пользователь регистрируется через Auth Service.
2. Пользователь входит через `/auth/login` и получает JWT.
3. Отправляет боту команду `/token <jwt>` — бот сохраняет токен в Redis.
4. Отправляет текстовое сообщение — бот проверяет JWT локально и ставит задачу в очередь.
5. Celery-воркер вызывает LLM (OpenRouter) и отправляет ответ пользователю через Telegram.

JWT создаётся только в Auth Service. Bot Service только проверяет подпись — к базе Auth Service не обращается.

## Сервисы

### Auth Service (порт 8000)

Swagger UI: http://localhost:8000/docs

| Эндпоинт          | Метод   | Описание |
|---                |---      |---       |
| `/auth/register`  | POST    | Регистрация пользователя, возвращает публичный профиль |
| `/auth/login`     | POST    | Вход (OAuth2PasswordRequestForm), возвращает JWT |
| `/auth/me`        | GET     | Профиль текущего пользователя (требует Bearer-токен) |
| `/health`         | GET     | Проверка работоспособности |


### Bot Service

Telegram-бот на aiogram 3.x.

| Команда / сообщение    | Поведение |
|---                     |---|
| `/start`               | Инструкция по использованию |
| `/token <JWT>`         | Сохранить токен в Redis для данного пользователя |
| Любой текст            | Проверить JWT, поставить задачу в очередь, вернуть ответ LLM |

### Инфраструктура

| Сервис                      | Адрес                  | Доступ |
|---                          |---                     |---|
| RabbitMQ (веб-интерфейс)    | http://localhost:15672 | guest / guest |
| Redis                       | localhost:6379         | — |

В Docker Compose используются named volumes:
- `auth_data` — хранит SQLite-базу Auth Service;
- `redis_data` — хранит данные Redis;
- `rabbitmq_data` — хранит состояние RabbitMQ.

## Быстрый старт

### Через Docker Compose

1. Заполните переменные окружения:

```bash
# Можно скопировать примеры:
cp auth_service/.env.example auth_service/.env
cp bot_service/.env.example bot_service/.env

# Обязательно укажите в bot_service/.env:
TELEGRAM_BOT_TOKEN=<токен от @BotFather>
OPENROUTER_API_KEY=<ключ с openrouter.ai>
```

2. Запустите:

```bash
docker-compose up --build
```

### Локальная разработка (без Docker)

Сначала поднимите RabbitMQ и Redis:

```bash
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management
docker run -d -p 6379:6379 redis:7-alpine
```

**Auth Service:**

```bash
cd auth_service
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Bot Service** (два отдельных терминала):

```bash
cd bot_service
uv sync

# Терминал 1 — Telegram-бот
uv run python -m app.bot.run

# Терминал 2 — Celery-воркер
uv run celery -A app.infra.celery_app worker --loglevel=info
```

## Тесты

```bash
# Auth Service
cd auth_service && uv run pytest tests/ -v

# Bot Service
cd bot_service  && uv run pytest tests/ -v
```

Тесты запускаются без Docker и без реальных внешних сервисов:
- интеграционные тесты Auth Service используют SQLite in-memory
- мок-тесты Bot Service используют `fakeredis` и `respx`
- обработчики Bot Service проверяют отсутствие токена, невалидный токен,
  удаление истёкшего токена и ошибку публикации задачи в очередь
- дополнительно: есть github ci на оба компонента

## Пользовательский сценарий

1. Откройте Swagger: http://localhost:8000/docs
2. Зарегистрируйтесь: `POST /auth/register` → `{"email": "surname@email.com", "password": "12345678"}`
3. Войдите через `POST /auth/login`, где `username` — это email, а `password` — пароль
4. Скопируйте `access_token` из ответа `/auth/login`
5. В Telegram отправьте боту: `/token <скопированный_токен>`
6. Бот ответит: «Токен сохранён. Теперь можно отправлять запросы модели.»
7. Отправьте любой вопрос — бот ответит: «Запрос принят. Ответ придёт следующим сообщением.»
8. Следующим сообщением придёт ответ от LLM

Если Redis, RabbitMQ, Telegram API или OpenRouter временно недоступны, бот
возвращает пользователю понятное сообщение об ошибке вместо молчаливого сбоя.

## Выбор модели LLM

По умолчанию используется `openrouter/free` — OpenRouter сам выбирает доступную бесплатную модель.

В задании упоминается `stepfun/step-3.5-flash:free`, но на практике она периодически недоступна.
Рекомендуется оставить `openrouter/free` или выбрать любую рабочую модель на [openrouter.ai/models](https://openrouter.ai/models?q=free):

```
OPENROUTER_MODEL=openrouter/free           # авто-выбор (рекомендуется)
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
```

## Переменные окружения

### `auth_service/.env`

| Переменная                      | По умолчанию             | Описание |
|---                              |---                       |---       |
| `JWT_SECRET`                    | `change_me_super_secret` | Секрет подписи JWT (должен совпадать с bot_service) |
| `JWT_ALG`                       | `HS256`                  | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES`   | `60`                     | Время жизни токена в минутах |
| `SQLITE_PATH`                   | `./auth.db`              | Путь к файлу базы данных |

### `bot_service/.env`

| Переменная             | Описание |
|---                     |---       |
| `TELEGRAM_BOT_TOKEN`   | Токен бота от @BotFather |
| `JWT_SECRET`           | Должен совпадать с auth_service |
| `OPENROUTER_API_KEY`   | Ключ API с openrouter.ai |
| `OPENROUTER_MODEL`     | Модель LLM (по умолчанию `openrouter/free`) |
| `REDIS_URL`            | URL Redis (по умолчанию `redis://redis:6379/0`) |
| `RABBITMQ_URL`         | URL RabbitMQ (по умолчанию `amqp://guest:guest@rabbitmq:5672//`) |

## Демонстрация работы

### Auth Service — регистрация

![register](screenshots/01_auth_register.png)

### Auth Service — логин

![login](screenshots/02_auth_login.png)

### Auth Service — /auth/me

![me](screenshots/03_auth_me.png)

### Telegram-бот

![chat](screenshots/04_chat.png)

### RabbitMQ — обзор

![rabbitmq overview](screenshots/05_rabit_overview.png)

### RabbitMQ — очереди

![rabbitmq queues](screenshots/06_rabit_queues.png)

### Тесты

![tests](screenshots/07_tests.png)
Или посмотреть в [CI](https://github.com/GRusar/llm-consultant/actions/workflows/ci.yml)