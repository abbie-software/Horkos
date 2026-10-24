import json
import logging
from concurrent.futures import ThreadPoolExecutor

from google import genai

from app.config import settings

log = logging.getLogger(__name__)


class LLMError(Exception):
    """The AI call failed, or its answer could not be used."""


def _call(prompt, schema, client, model, api_key, thinking_level) -> str:
    if client is None:
        client = genai.Client(api_key=api_key)
    options = {
        "model": model,
        "input": prompt,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
    }
    if thinking_level:  # lighter models may not accept this setting, so it is optional
        options["generation_config"] = {"thinking_level": thinking_level}
    interaction = client.interactions.create(**options)
    return interaction.output_text


def generate_json(
    prompt: str,
    schema: dict,
    *,
    client=None,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = 20.0,
    thinking_level: str | None = None,
) -> dict:
    """Ask Gemini for a JSON answer that fits the schema.

    Any problem (not set up, slow, an error, bad JSON) raises LLMError, so the
    caller can fall back to the safe choice. The call runs in a worker thread
    so a hung request can never hold the Guard up for longer than the timeout.
    """
    model = settings.gemini_model if model is None else model
    api_key = settings.gemini_api_key if api_key is None else api_key
    if thinking_level is None:
        thinking_level = settings.gemini_thinking_level
    if not model or (client is None and not api_key):
        raise LLMError("The AI is not set up (GEMINI_API_KEY or GEMINI_MODEL is missing).")

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            _call, prompt, schema, client, model, api_key, thinking_level
        )
        text = future.result(timeout=timeout)
    except Exception as exc:
        log.exception("The AI call failed")
        raise LLMError("The AI call failed.") from exc
    finally:
        executor.shutdown(wait=False)

    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise LLMError("The AI did not return valid JSON.") from exc
    if not isinstance(data, dict):
        raise LLMError("The AI returned JSON that is not an object.")
    return data