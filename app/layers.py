"""Layer registry: what each layer produces and which approved gate it needs first."""

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from app.agents import strategy
from app.config import settings
from app.context import load_dir
from app.llm import LLM
from app.store import Store


class GateNotApproved(RuntimeError):
    pass


@dataclass
class Layer:
    name: str
    kind: str
    gated: bool
    requires: str | None
    run: Callable[[LLM, Store], BaseModel]


def _run_strategy(llm: LLM, store: Store) -> BaseModel:
    return strategy.run(llm, load_dir(settings.context_dir), load_dir(settings.signals_dir))


LAYERS: dict[str, Layer] = {
    # Strategy runs continuously and is not gated; Roadmap (Gate A), Business Case (Gate B)
    # and Define (Gate C) are added in later phases.
    "strategy": Layer("strategy", "options", gated=False, requires=None, run=_run_strategy),
}


def run_layer(name: str, llm: LLM, store: Store) -> tuple[int, BaseModel]:
    layer = LAYERS[name]
    if layer.requires and store.latest_approved(layer.requires) is None:
        raise GateNotApproved(f"Layer '{name}' needs an approved '{layer.requires}' artifact first")
    artifact = layer.run(llm, store)
    artifact_id = store.save(layer.name, layer.kind, artifact, gated=layer.gated)
    return artifact_id, artifact
