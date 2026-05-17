import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.jwt import decode_and_validate
from app.infra.celery_app import celery_app as _celery_app  # noqa: F401 — инициализирует брокер в процессе бота
from app.infra.redis import get_redis
from app.tasks.llm_tasks import llm_request

router = Router()
logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 24 * 60 * 60


def _token_key(user_id: int) -> str:
    return f"token:{user_id}"


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Это бот для доступа к LLM через OpenRouter по JWT-токену.\n"
        "Сначала отправьте токен командой /token <JWT>.\n"
        "Потом просто напишите вопрос и я вам отвечу!"
    )


@router.message(Command("token"))
async def cmd_token(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /token <ваш_JWT>")
        return
    token = parts[1].strip()
    try:
        decode_and_validate(token)
    except ValueError as e:
        await message.answer(f"Токен недействителен: {e}")
        return

    try:
        redis = get_redis()
        await redis.set(_token_key(message.from_user.id), token, ex=TOKEN_TTL_SECONDS)
    except Exception:
        logger.exception("Failed to save JWT token to Redis")
        await message.answer("Не удалось сохранить токен. Попробуйте позже.")
        return

    await message.answer("Токен сохранён. Теперь можно отправлять запросы модели.")


@router.message(F.text)
async def handle_message(message: Message) -> None:
    prompt = message.text.strip()
    if not prompt:
        await message.answer("Пожалуйста, отправьте текстовый вопрос.")
        return

    token_key = _token_key(message.from_user.id)
    try:
        redis = get_redis()
        token = await redis.get(token_key)
    except Exception:
        logger.exception("Failed to read JWT token from Redis")
        await message.answer("Не удалось проверить токен. Попробуйте позже.")
        return

    if not token:
        await message.answer(
            "Токен не найден. Пожалуйста, отправьте его командой /token <JWT>."
        )
        return

    try:
        decode_and_validate(token)
    except ValueError:
        await redis.delete(token_key)
        await message.answer(
            "Токен недействителен или истёк. Получите новый в Auth Service и отправьте /token <JWT>."
        )
        return

    try:
        llm_request.delay(message.chat.id, prompt)
    except Exception:
        logger.exception("Failed to publish LLM task")
        await message.answer("Не удалось поставить запрос в очередь. Попробуйте позже.")
        return

    await message.answer("Запрос принят. Ответ придёт следующим сообщением.")
