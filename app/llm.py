"""Single entry point for Claude calls. Every agent returns a schema-valid Pydantic object."""

from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class AgentRefused(RuntimeError):
    pass


class LLM(Protocol):
    def structured(self, system: str, prompt: str, schema: type[T]) -> T: ...


class ClaudeLLM:
    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()

    def structured(self, system: str, prompt: str, schema: type[T]) -> T:
        response = self.client.beta.messages.parse(
            model=settings.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": settings.effort},
            # On a safety decline, the API re-runs the request on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            category = response.stop_details.category if response.stop_details else None
            raise AgentRefused(f"Model declined (category={category})")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("Output hit max_tokens before the artifact was complete")
        return response.parsed_output
