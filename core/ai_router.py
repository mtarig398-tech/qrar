"""Routes DAX-generation requests across providers with automatic fallback
(Smart Fallback): if the primary provider is unreachable or returns junk,
the next one in config.PROVIDER_ORDER is tried automatically.
"""
from __future__ import annotations

import logging

import config

from .ai_providers import PROVIDERS, ProviderError

logger = logging.getLogger(__name__)


class AllProvidersFailedError(RuntimeError):
    def __init__(self, attempts: dict[str, str]):
        self.attempts = attempts
        details = "; ".join(f"{name}: {err}" for name, err in attempts.items())
        super().__init__(f"All AI providers failed. {details}")


def generate_dax(schema: dict, question: str, history: list[dict]) -> tuple[dict, str]:
    """Try each provider in config.PROVIDER_ORDER until one succeeds.

    Returns (result, provider_name_used).
    """
    attempts: dict[str, str] = {}
    for name in config.PROVIDER_ORDER:
        provider = PROVIDERS.get(name)
        if provider is None:
            attempts[name] = "unknown provider"
            continue
        try:
            result = provider(schema, question, history)
            return result, name
        except ProviderError as exc:
            logger.warning("Provider '%s' failed, falling back: %s", name, exc)
            attempts[name] = str(exc)
            continue
    raise AllProvidersFailedError(attempts)
