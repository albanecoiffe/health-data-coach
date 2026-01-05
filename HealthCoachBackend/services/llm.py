import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def call_ollama(prompt: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "top_p": 0},
        },
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["response"]
