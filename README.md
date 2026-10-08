# PM Harness

A hosted service that runs product management as layered agents, modeled on the "How to Build Agentic Product Management" infographic (Strategy, Roadmap, Business Case, Define, Build, Measure, Run). The full plan is in [docs/plan.md](docs/plan.md).

**Status:** Phase 0 scaffold. The Strategy layer (market research, customer signal and portfolio agents, plus a merge step) is wired end to end. Later layers have schemas but no agents yet.

## How it works

- Each agent is one Claude call (`claude-opus-5-5`) with a structured output, so every artifact is schema-valid JSON (`app/schemas.py`).
- A layer runs its agents in parallel, then merges them into the layer artifact (`app/agents/strategy.py`).
- Artifacts are versioned in SQLite. Gated layers create a `pending` gate the PM approves with `POST /gates/{artifact_id}`; the next layer refuses to run until it is approved.
- If `NOTION_TOKEN` and `NOTION_PARENT_PAGE_ID` are set, each artifact is also published as a Notion page.
- Refusals: requests opt into server-side fallback (`fallbacks: "default"`), and a final refusal returns HTTP 502 rather than a partial artifact.

All data in `context/` and `signals/` is synthetic (a fictional invoicing SaaS called Tallyo).

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # set ANTHROPIC_API_KEY, and optionally the Notion values
set -a && . ./.env && set +a
uvicorn app.main:app --reload
curl -X POST localhost:8000/layers/strategy/run
```

Tests use a fake model and need no API key: `pytest`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness and available layers |
| POST | `/layers/{layer}/run` | Run a layer, store and (optionally) publish its artifact |
| GET | `/artifacts?layer=` | List artifacts, newest first |
| GET | `/artifacts/{id}` | One artifact |
| POST | `/gates/{id}` | `{"approve": true, "decision": "..."}` to approve or reject a gate |

## Layout

```
app/
  main.py        FastAPI routes
  layers.py      layer registry and gate enforcement
  agents/        one module per layer; base.py holds shared agent rules
  llm.py         Claude call with structured output and refusal handling
  schemas.py     artifact contracts between layers
  store.py       SQLite artifacts + gates
  notion.py      Notion page publisher
context/         company, OKRs, portfolio, personas, competitors, capacity
signals/         interviews and support tickets
tests/
```
