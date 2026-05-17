import pytest
import respx
import httpx
from app.services.openrouter_client import call_openrouter


@pytest.mark.asyncio
async def test_call_openrouter_success():
    mock_response = {
        "choices": [{"message": {"content": "Лев Толстой родился в 1828 году."}}]
    }
    with respx.mock:
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        result = await call_openrouter("Кто такой Толстой?")
    assert result == "Лев Толстой родился в 1828 году."


@pytest.mark.asyncio
async def test_call_openrouter_content_parts():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "Первая часть."},
                        {"type": "text", "text": "Вторая часть."},
                    ]
                }
            }
        ]
    }
    with respx.mock:
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        result = await call_openrouter("Ответь частями")
    assert result == "Первая часть.\nВторая часть."


@pytest.mark.asyncio
async def test_call_openrouter_error():
    with respx.mock:
        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(RuntimeError, match="OpenRouter returned status"):
            await call_openrouter("test")
