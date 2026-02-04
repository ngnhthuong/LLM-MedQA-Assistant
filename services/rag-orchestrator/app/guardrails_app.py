import os
from functools import lru_cache
from typing import Any

from nemoguardrails import RailsConfig, LLMRails
from nemoguardrails.llm.providers import register_llm_provider

from typing import Any, List, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_core.outputs import Generation, LLMResult
from langchain_core.runnables import RunnableConfig


class ExternalInferenceLLM(BaseLanguageModel):
    """
    LangChain-compatible LLM wrapper for NeMo Guardrails 0.20.0
    backed by external inference (KServe).
    """

    def __init__(self, *args, **kwargs):
        super().__init__()

    @property
    def _llm_type(self) -> str:
        return "external-kserve"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        from .llm_client import build_kserve_client_from_env

        client = build_kserve_client_from_env()
        if not client:
            raise RuntimeError("External inference client not configured")

        return client.generate(
            prompt,
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.2),
        )

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        # Guardrails prefers async, but your backend is sync
        return self._call(prompt, stop=stop, **kwargs)

    def generate_prompt(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> LLMResult:
        generations = [
            [Generation(text=self._call(p, stop=stop, **kwargs))]
            for p in prompts
        ]
        return LLMResult(generations=generations)


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
