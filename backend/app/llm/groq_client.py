"""Owner: M2. Groq (Llama 3.3 70B) wrapper with JSON mode. SDK imported lazily."""
from app.config import settings

MODEL = "llama-3.3-70b-versatile"


def _client():
    from groq import Groq

    return Groq(api_key=settings.groq_api_key)


def chat(messages: list[dict], *, json_mode: bool = False, model: str = MODEL) -> str:
    kwargs: dict = {"model": model, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content
    # TODO(M2): retries, temperature, streaming helper.
