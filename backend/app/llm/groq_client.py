"""Owner: M2. Groq (Llama 3.3 70B) wrapper with JSON mode. SDK imported lazily."""
import time

from app.config import settings

MODEL = "llama-3.3-70b-versatile"
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0


def _client():
    from groq import Groq

    return Groq(api_key=settings.groq_api_key)


def _async_client():
    from groq import AsyncGroq

    return AsyncGroq(api_key=settings.groq_api_key)


def chat(
    messages: list[dict],
    *,
    json_mode: bool = False,
    model: str = MODEL,
    temperature: float = 0.0,
) -> str:
    kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _client().chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"Groq chat failed after {_MAX_RETRIES} attempts") from last_exc


async def chat_async(
    messages: list[dict],
    *,
    json_mode: bool = False,
    model: str = MODEL,
    temperature: float = 0.0,
) -> str:
    import asyncio

    kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await _async_client().chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"Groq async chat failed after {_MAX_RETRIES} attempts") from last_exc
