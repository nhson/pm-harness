from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.layers import LAYERS, GateNotApproved, run_layer
from app.llm import LLM, AgentRefused, ClaudeLLM
from app.notion import NotionPublisher
from app.store import Store

app = FastAPI(title="PM Harness")
_store = Store(settings.db_path)


def get_store() -> Store:
    return _store


def get_llm() -> LLM:
    return ClaudeLLM()


def get_publisher() -> NotionPublisher | None:
    if settings.notion_token and settings.notion_parent_page_id:
        return NotionPublisher(settings.notion_token, settings.notion_parent_page_id)
    return None


class GateDecision(BaseModel):
    approve: bool
    decision: str | None = None


@app.get("/health")
def health():
    return {"ok": True, "layers": list(LAYERS)}


@app.post("/layers/{layer}/run")
def run(layer: str, store: Store = Depends(get_store), llm: LLM = Depends(get_llm), publisher=Depends(get_publisher)):
    if layer not in LAYERS:
        raise HTTPException(404, f"Unknown layer '{layer}'. Available: {list(LAYERS)}")
    try:
        artifact_id, artifact = run_layer(layer, llm, store)
    except GateNotApproved as e:
        raise HTTPException(409, str(e))
    except AgentRefused as e:
        raise HTTPException(502, str(e))
    notion_url = None
    if publisher:
        notion_url = publisher.publish(f"{layer.capitalize()} · artifact {artifact_id}", artifact.model_dump())
        store.set_notion_url(artifact_id, notion_url)
    return {"artifact_id": artifact_id, "notion_url": notion_url, "artifact": artifact.model_dump()}


@app.get("/artifacts")
def list_artifacts(layer: str | None = None, store: Store = Depends(get_store)):
    return store.list(layer)


@app.get("/artifacts/{artifact_id}")
def get_artifact(artifact_id: int, store: Store = Depends(get_store)):
    artifact = store.get(artifact_id)
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    return artifact


@app.post("/gates/{artifact_id}")
def decide_gate(artifact_id: int, body: GateDecision, store: Store = Depends(get_store)):
    try:
        return store.decide(artifact_id, body.approve, body.decision)
    except KeyError:
        raise HTTPException(404, "No gate for this artifact")
