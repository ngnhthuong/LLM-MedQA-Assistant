import os
from functools import lru_cache

from nemoguardrails import RailsConfig, LLMRails

GUARDRAILS_ENABLED = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"

@lru_cache()
def get_rails_app() -> LLMRails:
    config = RailsConfig.from_path("guardrails")
    app = LLMRails(config)
    return app

def generate_with_guardrails(user_message: str, grounded_prompt: str) -> str:
    """
    Simple helper that:
    - uses the grounded_prompt you already build (context + history)
    - lets NeMo Guardrails drive the actual LLM call & safety
    """
    rails = get_rails_app()

    # One simple pattern is: treat grounded_prompt as "system" and user_message as "user"
    messages = [
        {"role": "system", "content": grounded_prompt},
        {"role": "user", "content": user_message},
    ]

    # API name may differ slightly depending on NeMo version; adjust as needed.
    response = rails.generate(messages=messages)

    # Assume a basic OpenAI-like shape; adjust to real return type.
    return response["content"]