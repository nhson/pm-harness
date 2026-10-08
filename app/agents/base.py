from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.llm import LLM

T = TypeVar("T", bound=BaseModel)

COMMON_RULES = """You are one agent in a product management harness. A human Product Lead reviews your output.
Rules:
- Ground every finding in the provided sources. Cite each by its source id exactly as given (for rows in a CSV, use "<file>#<row id>").
- If you make a claim you cannot source, list it in unsourced_claims (when the schema has that field) rather than presenting it as fact.
- Prefer fewer, sharper items over long lists. Do not invent data that is not in the sources."""


@dataclass(frozen=True)
class Agent(Generic[T]):
    name: str
    role: str
    output: type[T]

    def run(self, llm: LLM, inputs: str) -> T:
        system = f"{COMMON_RULES}\n\nYour role: {self.name}. {self.role}"
        return llm.structured(system, inputs, self.output)
