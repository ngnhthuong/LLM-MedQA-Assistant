import os
from functools import lru_cache
from typing import Any

from nemoguardrails import RailsConfig, LLMRails
from nemoguardrails.llm.providers import register_llm_provider


class ExternalInferenceLLM:
    """
    NeMo Guardrails 0.20.0-compatible custom LLM provider.
    Must implement `_acall`.
    """

    async def _acall(
        self,
        prompt: str | None = None,
        messages: list | None = None,
        **kwargs,
    ) -> str:
        from .llm_client import build_kserve_client_from_env

        client = build_kserve_client_from_env()
        if not client:
            raise RuntimeError("External inference client not configured")

        # Guardrails may pass messages OR prompt
        if prompt is None and messages is not None:
            prompt = self._messages_to_prompt(messages)

        if not prompt:
            raise ValueError("No prompt provided to ExternalInferenceLLM")

        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.2)

        # Your client is sync → call it directly
        return client.generate(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    @staticmethod
    def _messages_to_prompt(messages: list[dict]) -> str:
        """
        Convert OpenAI-style messages into a single prompt
        suitable for instruction-tuned models like Mistral.
        """
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"[{role.upper()}]\n{content}")
        return "\n\n".join(parts)


register_llm_provider("external", ExternalInferenceLLM)


GUARDRAILS_ENABLED = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"


@lru_cache()
def get_rails_app() -> LLMRails:
    config = RailsConfig.from_path("guardrails")
    return LLMRails(config)


def generate_with_guardrails(user_message: str, grounded_prompt: str) -> str:
    rails = get_rails_app()

    messages = [
        {"role": "system", "content": grounded_prompt},
        {"role": "user", "content": user_message},
    ]

    response: Any = rails.generate(messages=messages)

    # Normalize output safely
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("content") or response.get("output") or str(response)
    return str(response)
