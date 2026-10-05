from __future__ import annotations

import os
from typing import Any

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def ollama_status() -> dict[str, Any]:
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.2)
        if response.status_code != 200:
            return {"available": False, "provider": "Ollama", "model": "Gemma 3 4B", "detail": "Ollama responded with an error."}
        models = response.json().get("models", [])
        names = [model.get("name", "") for model in models]
        model_available = any(OLLAMA_MODEL in name or "gemma3" in name.lower() or "gemma" in name.lower() for name in names)
        return {"available": model_available, "provider": "Ollama", "model": "Gemma 3 4B", "detail": "Connected" if model_available else "Ollama is running, but Gemma 3 4B is not installed."}
    except Exception:
        return {"available": False, "provider": "Ollama", "model": "Gemma 3 4B", "detail": "Start Ollama to enable local AI analysis."}


def generate_structured(problem: str, context: dict[str, Any], fallback: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    status = ollama_status()
    # The deterministic workflow is intentionally the safe default. Local model integration can be
    # enabled without changing the API contract once Ollama is available and a strict JSON parser is added.
    # This keeps the product honest and usable in environments where Ollama is not installed.
    return fallback, {**status, "used_fallback": True}
