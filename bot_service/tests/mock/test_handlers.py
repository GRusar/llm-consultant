import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from jose import jwt

from app.bot.handlers import cmd_token, handle_message

TEST_SECRET = "change_me_super_secret"


def make_valid_token() -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "42", "role": "user", "iat": now, "exp": now + timedelta(hours=1)},
        TEST_SECRET,
        algorithm="HS256",
    )


def make_expired_token() -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "42", "role": "user", "iat": now, "exp": now - timedelta(seconds=1)},
        TEST_SECRET,
        algorithm="HS256",
    )


def make_message(text: str, user_id: int = 123, chat_id: int = 456) -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.chat = MagicMock()
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_token_command_saves_token(fake_redis):
    token = make_valid_token()
    message = make_message(f"/token {token}")
    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        await cmd_token(message)
    saved = await fake_redis.get("token:123")
    assert saved == token
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "сохранён" in call_text


@pytest.mark.asyncio
async def test_token_command_invalid_token(fake_redis):
    message = make_message("/token garbage_token")
    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        await cmd_token(message)
    saved = await fake_redis.get("token:123")
    assert saved is None
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "недействителен" in call_text


@pytest.mark.asyncio
async def test_handle_message_no_token(fake_redis):
    message = make_message("Привет, как дела?")
    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        await handle_message(message)
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "Токен" in call_text or "не найден" in call_text


@pytest.mark.asyncio
async def test_handle_message_with_valid_token(fake_redis):
    token = make_valid_token()
    await fake_redis.set("token:123", token)
    message = make_message("Кто такой Толстой?")
    with (
        patch("app.bot.handlers.get_redis", return_value=fake_redis),
        patch("app.bot.handlers.llm_request") as mock_llm,
    ):
        mock_llm.delay = MagicMock()
        await handle_message(message)
    mock_llm.delay.assert_called_once_with(456, "Кто такой Толстой?")
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "принят" in call_text


@pytest.mark.asyncio
async def test_handle_message_deletes_invalid_saved_token(fake_redis):
    await fake_redis.set("token:123", make_expired_token())
    message = make_message("Кто такой Толстой?")

    with patch("app.bot.handlers.get_redis", return_value=fake_redis):
        await handle_message(message)

    assert await fake_redis.get("token:123") is None
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "недействителен" in call_text or "истёк" in call_text


@pytest.mark.asyncio
async def test_handle_message_reports_queue_error(fake_redis):
    token = make_valid_token()
    await fake_redis.set("token:123", token)
    message = make_message("Кто такой Толстой?")

    with (
        patch("app.bot.handlers.get_redis", return_value=fake_redis),
        patch("app.bot.handlers.llm_request") as mock_llm,
    ):
        mock_llm.delay.side_effect = RuntimeError("broker down")
        await handle_message(message)

    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "очередь" in call_text
