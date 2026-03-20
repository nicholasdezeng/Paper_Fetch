from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class LLMConfigError(RuntimeError):
    pass


def load_llm_config() -> tuple[str, str, str]:
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or "https://api.openai.com/v1"
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip() or "gpt-4o-mini"

    if not api_key:
        raise LLMConfigError("LLM_API_KEY is not set")

    return base_url.rstrip("/"), api_key, model


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout_s: int = 60,
) -> str:
    url = f"{base_url}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful research assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    try:
        return str(data["choices"][0]["message"]["content"])
    except Exception:
        raise RuntimeError(f"Unexpected LLM response format: {data}")
