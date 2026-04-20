import requests

# ========== LLM CONFIGURATION ==========
# OLLAMA model, locally hosted
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

# ========== UTILITIES ==========


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 256,
    model: str = MODEL,
) -> str:
    if not system_prompt or not user_prompt:
        raise ValueError("system_prompt and user_prompt must be non-empty strings")

    merged_prompt = f"""
{system_prompt.strip()}

---

{user_prompt.strip()}
"""
    return call_ollama(merged_prompt, model=model, temperature=temperature).strip()


def call_ollama(prompt: str, model: str = MODEL, temperature: float = 0) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": 0},
        },
        timeout=90,
    )
    res.raise_for_status()
    return res.json()["response"]
