from typing import Any

import httpx

from app.core.config import settings


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "\n".join(parts)

    raise RuntimeError("OpenRouter response content has unsupported format")


async def call_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }
    payload: dict[str, Any] = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    base = settings.OPENROUTER_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError("OpenRouter request failed") from exc

    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter returned status {response.status_code}")

    data = response.json()
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenRouter response has unexpected format") from exc

    if not isinstance(message, dict):
        raise RuntimeError("OpenRouter response message has unexpected format")

    content = message.get("content")
    if content is None:
        content = message.get("reasoning") or message.get("refusal")

    return _extract_text_content(content)
