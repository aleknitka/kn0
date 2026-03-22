"""Async LLM client abstraction for kn0.

Supports OpenAI-compatible endpoints (LM Studio, Ollama, OpenAI) via the
openai SDK, and Anthropic via the anthropic SDK.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_OPENAI_COMPATIBLE = {"openai", "lm_studio", "ollama"}

# Default dummy API keys accepted by local servers
_DEFAULT_API_KEYS: dict[str, str] = {
    "lm_studio": "lm-studio",
    "ollama": "ollama",
    "openai": "",
    "anthropic": "",
}


class LLMClient:
    """Async wrapper over OpenAI-compatible and Anthropic chat APIs.

    Usage::

        client = LLMClient(provider="lm_studio", model="local-model")
        response = await client.chat(system="...", user="...")
    """

    def __init__(
        self,
        provider: str,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        timeout: float = 60.0,
    ) -> None:
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        if self.provider not in _OPENAI_COMPATIBLE and self.provider != "anthropic":
            raise ValueError(
                f"Unknown provider {provider!r}. "
                "Choose from: openai, lm_studio, ollama, anthropic"
            )

        resolved_key = api_key or _DEFAULT_API_KEYS.get(self.provider, "")

        if self.provider in _OPENAI_COMPATIBLE:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for LLM extraction. "
                    "Install it with: pip install openai"
                ) from exc
            self._openai: AsyncOpenAI | None = AsyncOpenAI(
                base_url=base_url,
                api_key=resolved_key or "not-needed",
                timeout=timeout,
            )
            self._anthropic = None
        else:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required for Anthropic provider. "
                    "Install it with: pip install 'kn0[anthropic]'"
                ) from exc
            self._anthropic = AsyncAnthropic(api_key=resolved_key, timeout=timeout)
            self._openai = None

    async def chat(self, system: str, user: str) -> str:
        """Send an async chat completion and return the text response."""
        if self.provider in _OPENAI_COMPATIBLE:
            return await self._chat_openai(system, user)
        return await self._chat_anthropic(system, user)

    async def _chat_openai(self, system: str, user: str) -> str:
        assert self._openai is not None
        response = await self._openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content
        return content or ""

    async def _chat_anthropic(self, system: str, user: str) -> str:
        assert self._anthropic is not None
        response = await self._anthropic.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=self.temperature,
        )
        block = response.content[0]
        return block.text if hasattr(block, "text") else ""
