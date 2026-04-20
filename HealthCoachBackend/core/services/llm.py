import requests
from dotenv import load_dotenv
import os

load_dotenv()

# ========== LLM CONFIGURATION ==========
# OLLAMA model, locally hosted
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

# Hugging Face API
HF_TOKEN = os.getenv("HF_TOKEN")
HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-2-9b-it:featherless-ai"

# ========== UTILITIES ==========


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 256,
    model: str = DEFAULT_MODEL,
) -> str:
    if not system_prompt or not user_prompt:
        raise ValueError("system_prompt and user_prompt must be non-empty strings")

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    # 🔑 HF FIX: system role NOT supported → merge into user
    merged_prompt = f"""
{system_prompt.strip()}

---

{user_prompt.strip()}
"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": merged_prompt,
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    res = requests.post(
        HF_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if res.status_code != 200:
        print("❌ HF ERROR STATUS:", res.status_code)
        print("❌ HF ERROR BODY:", res.text)

    res.raise_for_status()

    data = res.json()
    return data["choices"][0]["message"]["content"].strip()


def call_ollama(prompt: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "top_p": 0},
        },
        timeout=90,
    )
    res.raise_for_status()
    return res.json()["response"]
