"""AI providers for turning a natural-language question into a DAX query.

Each provider function has the same signature and either returns a dict
{"dax": str, "explanation": str} or raises ProviderError, so ai_router can
fall back to the next provider in the chain without special-casing errors
from any particular SDK.
"""
from __future__ import annotations

import json
import re

import requests

import config


class ProviderError(RuntimeError):
    """Raised when a provider is unreachable, misconfigured, or returns junk."""


SYSTEM_PROMPT = (
    "You are a DAX expert assisting a Power BI Chat-to-Data application. "
    "Given the model schema and the user's question, respond with ONLY a "
    'JSON object of the form {"dax": "<DAX query>", "explanation": '
    '"<short explanation>"}. Do not wrap it in markdown fences and do not '
    "add any other text."
)


def _build_prompt(schema: dict, question: str, history: list[dict]) -> str:
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    return (
        f"Model schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Question: {question}"
    )


def _extract_json(text: str) -> dict:
    """LLMs often wrap JSON in prose or markdown fences; pull out the object."""
    text = (text or "").strip()
    if not text:
        raise ProviderError("Model returned an empty response")

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Could not parse JSON from model response: {exc}") from exc

    if "dax" not in parsed:
        raise ProviderError("Model response JSON is missing the 'dax' field")
    return parsed


def call_ollama(schema: dict, question: str, history: list[dict]) -> dict:
    try:
        response = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_prompt(schema, question, history)},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=config.AI_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ProviderError(f"Ollama unreachable: {exc}") from exc

    content = response.json().get("message", {}).get("content", "")
    return _extract_json(content)


def call_openai(schema: dict, question: str, history: list[dict]) -> dict:
    if not config.OPENAI_API_KEY:
        raise ProviderError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderError("openai package is not installed") from exc

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=config.AI_REQUEST_TIMEOUT)
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(schema, question, history)},
            ],
        )
    except Exception as exc:  # openai raises its own hierarchy of errors
        raise ProviderError(f"OpenAI request failed: {exc}") from exc

    content = response.choices[0].message.content or ""
    return _extract_json(content)


def call_gemini(schema: dict, question: str, history: list[dict]) -> dict:
    if not config.GEMINI_API_KEY:
        raise ProviderError("GEMINI_API_KEY is not configured")
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ProviderError("google-generativeai package is not installed") from exc

    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL, system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(
            _build_prompt(schema, question, history),
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:
        raise ProviderError(f"Gemini request failed: {exc}") from exc

    return _extract_json(response.text or "")


PROVIDERS = {
    "ollama": call_ollama,
    "openai": call_openai,
    "gemini": call_gemini,
}
