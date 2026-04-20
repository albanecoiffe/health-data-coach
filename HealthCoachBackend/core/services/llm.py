import requests

from core.config import get_settings

settings = get_settings()


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 256,
    model: str | None = None,
) -> str:
    if not system_prompt or not user_prompt:
        raise ValueError("system_prompt and user_prompt must be non-empty strings")

    merged_prompt = f"""
{system_prompt.strip()}

---

{user_prompt.strip()}
"""
    return call_ollama(merged_prompt, model=model, temperature=temperature).strip()


def call_ollama(prompt: str, model: str | None = None, temperature: float = 0) -> str:
    res = requests.post(
        settings.ollama_url,
        json={
            "model": model or settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0},
        },
        timeout=settings.ollama_timeout_seconds,
    )
    res.raise_for_status()
    return res.json()["response"]
