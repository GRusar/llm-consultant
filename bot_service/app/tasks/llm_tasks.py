import asyncio
import logging

import httpx
from app.core.config import settings
from app.infra.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.llm_tasks.llm_request")
def llm_request(tg_chat_id: int, prompt: str) -> None:
    asyncio.run(_send_llm_response(tg_chat_id, prompt))


async def _send_llm_response(tg_chat_id: int, prompt: str) -> None:
    from app.services.openrouter_client import call_openrouter

    try:
        answer = await call_openrouter(prompt)
    except Exception as exc:
        logger.exception("OpenRouter request failed")
        await _send_telegram_message(
            tg_chat_id,
            f"Не удалось получить ответ от LLM: {exc}",
        )
        raise

    try:
        await _send_telegram_message(tg_chat_id, answer)
    except Exception:
        logger.exception("Telegram sendMessage failed")
        raise


async def _send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
