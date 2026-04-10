import logging
import os
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class MissingOpenRouterKeyError(RuntimeError):
    pass


class OpenRouterTimeoutError(RuntimeError):
    pass


class OpenRouterProviderError(RuntimeError):
    pass


def _extract_text_from_response(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise OpenRouterProviderError("OpenRouter response missing choices.")

    message = choices[0].get("message", {})
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return " ".join(part for part in text_parts if part).strip()

    raise OpenRouterProviderError("OpenRouter response missing text content.")


def run_openrouter_chat(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.0,
    timeout_s: float = 20.0,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    target_model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    request_payload = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
    }
    response_payload = _post_chat_completion(request_payload, timeout_s=timeout_s)
    text = _extract_text_from_response(response_payload)
    return {"model": target_model, "response_text": text}


def _post_chat_completion(request_payload: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise MissingOpenRouterKeyError("OPENROUTER_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers=headers,
            json=request_payload,
            timeout=timeout_s,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise OpenRouterTimeoutError("OpenRouter request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else "unknown"
        raise OpenRouterProviderError(f"OpenRouter provider returned HTTP {status_code}.") from exc
    except httpx.RequestError as exc:
        raise OpenRouterProviderError("OpenRouter request failed.") from exc

    return response.json()


def run_openrouter_connectivity_check(prompt: str = "2+2", timeout_s: float = 20.0) -> Dict[str, Any]:
    target_model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    messages = [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": prompt},
        ]

    logger.info("Running OpenRouter connectivity check with model=%s", target_model)
    result = run_openrouter_chat(messages, temperature=0, timeout_s=timeout_s, model=target_model)
    return {
        "model": result["model"],
        "prompt": prompt,
        "response_text": result["response_text"],
    }
