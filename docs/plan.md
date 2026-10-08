# Agentic PM Harness: Build Plan

Modeled on the "How to Build Agentic Product Management" infographic (7 layers: Strategy, Roadmap, Business Case, Define, Build, Measure, Run). Date: 2026-10-08. Updated with decisions the same day.

## 1. Goal and decisions

Build a harness where a Product Lead runs the product cycle with agents, layer by layer. Each layer turns the previous layer's output into a sharper decision, and a human signs off where the infographic puts a person in the loop.

**Decisions (Son, 2026-10-08):**

| Question | Answer | What it means for the build |
|---|---|---|
| PM tools | Notion | Notion is the PM's workspace: artifacts publish there as pages, sources can be read from it |
| Shape | Hosted service | A Python web service calls the Claude API directly; no Claude Code dependency at runtime |
| Pilot data | Synthetic sample | A fictional product ("Tallyo", a B2B invoicing SaaS) with generated interviews, tickets, OKRs, capacity |
| Users | Single PM | No auth roles or multi-tenant data model in v1; one API key / one login |
| Repo | Create new | Scaffold lives in `/mnt/project-files/pm-harness/` until a GitHub repo is attached |
| Data | No customer data | Synthetic only, so no PII handling is needed in v1 |

**Stack (default picked):** Python 3.12+, FastAPI, Anthropic Python SDK, Pydantic for artifact schemas, SQLite for artifacts and gate state (Postgres when hosted for real), Notion API for publishing. Agents use `claude-opus-5-5` with structured outputs so every artifact is schema-valid JSON, plus server-side refusal fallback. Deploy target: a single container (Fly.io, Railway or Cloud Run).

## 2. Architecture

```
                 ┌──────────── FastAPI service ─────────────┐
 Notion / files →│ Orchestrator: run layer, enforce gates   │→ Notion pages
 synthetic data  │  ├─ Layer 1 Strategy  (3 agents + merge) │   (one per artifact)
                 │  ├─ Layer 2 Roadmap   (3 agents + merge) │
                 │  ├─ Layer 3 Business Case ...            │
                 │  └─ Layer 4 Define ...                   │
                 │ Artifact store (SQLite) · Gate table     │
                 └──────────────────────────────────────────┘
                       metrics + run findings feed back into Layer 1
```

| Component | v1 implementation |
|---|---|
| **Agents** | One Python class per named agent: a system prompt, the inputs it reads, and a Pydantic output schema. One Claude call per agent with structured output |
| **Layer runner** | Runs a layer's agents in parallel, then a merge step that writes the layer artifact |
| **Orchestrator** | `POST /layers/{layer}/run` checks the upstream gate is approved, runs the layer, stores the artifact |
| **Artifact store** | SQLite table `artifacts(id, layer, kind, version, json, created_at)`; every run is a new version, so history is the audit log |
| **Context** | `context/` folder (company, OKRs, personas, competitors, capacity) plus `signals/` (interviews, tickets). Synthetic in v1 |
| **Gates** | Table `gates(layer, artifact_id, status, decision, decided_at)`. Approved through the API (and later a Notion status property) |
| **Notion** | After each run the artifact is rendered to Markdown-like blocks and published as a page under one "PM Harness" parent page |

Design rules:
- **Artifacts, not chat, are the hand-off.** Each layer reads only approved upstream artifacts plus context, so any layer can be re-run alone.
- **Every claim cites a source** (signal id, ticket id, metric). Unsourced claims are flagged, not dropped.
- **Agents propose, the PM decides** at the gates below.

## 3. Layers, agents, and hand-offs

### Layer 1: Strategy, "turn every signal into options"
| Agent | Does | Inputs |
|---|---|---|
| Market research agent | Tracks competitors and trends | Web search, competitor list |
| Customer signal agent | Reads interviews, support tickets, reviews; clusters pains | Interview notes, support desk export |
| Portfolio agent | Maps signals to goals and strategic bets | OKRs, current portfolio |

**Output:** `strategy/options`, a list of opportunities, each with evidence, linked goal, and confidence.
**Gate:** none required (runs "around the clock"); Product Lead skims a weekly digest.

### Layer 2: Roadmap, "draft scenarios with capacity impact"
| Agent | Does |
|---|---|
| Backlog agent | Merges options, requests, and tech debt into one ranked backlog |
| Engineering agent | Estimates effort and drafts capacity scenarios against team capacity |
| Analytics agent | Adds usage and drop-off findings to each item |

**Output:** `roadmap/scenarios`, 2 to 3 scenarios, each a ranked list with capacity use.
**Gate A (Product Lead):** pick the scenario / shortlist to cost.

### Layer 3: Business Case, "cost every option, linked to the KPI"
| Agent | Does |
|---|---|
| Business case agent | Cost per option (€, weeks, delta), weighted by strategic fit |
| Forecast agent | Forecasts conversion, LTV, churn impact with stated assumptions |

**Output:** `cases/<option>`, one case per shortlisted option, plus a comparison table.
**Gate B (Product Lead):** pick one ("Feature 1"). This is the key decision in the cycle.

### Layer 4: Define, "shape the Epic and its stories"
| Agent | Does |
|---|---|
| Epic agent | Drafts the Epic from the approved case (problem, goal, KPI, scope, non-goals) |
| Story agent | Proposes stories, grounded in the actual codebase |
| Acceptance agent | Writes testable acceptance criteria (Given/When/Then) |

**Output:** `define/epic` + `define/stories`, ready to push to the Notion backlog database.
**Gate C (Architect + Product Lead):** shape the slice, approve stories before they land in the Notion backlog.

### Layer 5: Build, "code, review, test and release"
| Agent | Does |
|---|---|
| Coding agent | Implements a story with tests on a branch |
| Review agent | Reviews every change against acceptance criteria |
| Release agent | Release notes, flags, rollout plan |

**Gate D (Engineer):** merges and ships. Agents never merge to main on their own.

### Layer 6: Measure, "conversion, retention, LTV"
| Agent | Does |
|---|---|
| Analytics agent | Tracks the KPIs named in the business case |
| Metrics agent | Compares actual vs forecast for the last release |

**Output:** `measure/<release>`, fed back to Layer 1 as a signal. Product Lead reviews.

### Layer 7: Run, "upgrades, incidents and tech debt"
| Agent | Does |
|---|---|
| Upgrade agent | Keeps dependencies and stack current |
| Incident agent | Triages incidents, links to affected features |
| Tech debt agent | Proposes debt fixes, which enter the Layer 2 backlog |

**Feedback loop:** Measure and Run outputs land in `signals/`, which Layers 1 and 2 read next cycle ("every release feeds the next cycle").

## 4. Human checkpoints (summary)

| Gate | After layer | Who | Decision |
|---|---|---|---|
| A | Roadmap | Product Lead | Which scenario / shortlist to cost |
| B | Business Case | Product Lead | Which option to build |
| C | Define | Architect + Product Lead | Epic and stories approved for the tracker |
| D | Build | Engineer | Merge and release |
| (review) | Measure | Product Lead | Read actual vs forecast |

Anything that writes outside the repo (creating tickets, posting to Slack, merging) is behind a gate or an explicit confirm.

## 5. Integrations needed (by phase)

| Need | Choice | Phase |
|---|---|---|
| LLM | Anthropic API, `claude-opus-5-5`, structured outputs | 0 |
| Signals | Synthetic files in `signals/` | 0 to 1 |
| Publishing | Notion API (integration token + one shared parent page) | 1 |
| Reading sources from Notion | Notion database of interview notes / requests | 2 |
| Web research (Market research agent) | Claude web search server tool | 2 |
| Codebase (Story agent) | GitHub read access to a sample repo | 3 |
| Analytics | Synthetic event table first; real tool later | 4 |
| Tracker | Notion database as the backlog, so no Jira/Linear needed | 3 |

## 6. Phased build order

**Phase 0: Foundations (scaffolded now)**
- Service skeleton (FastAPI), Claude helper with structured output and refusal handling, SQLite store, gate table.
- Artifact schemas for options, scenarios, case, epic, story.
- Synthetic "Tallyo" product: company brief, OKRs, personas, competitors, capacity, 8 interviews, 30 support tickets.
- Done when: tests pass with a fake model and `POST /layers/strategy/run` works against the real API.

**Phase 1: Strategy layer end to end + Notion publishing**
- Market research, customer signal, portfolio agents and the merge step (scaffolded now).
- Publish `strategy/options` to Notion.
- Done when: a run on the synthetic data gives sourced options you would keep with light edits.

**Phase 2: Roadmap layer + Gate A**
- Backlog, engineering, analytics agents; capacity scenarios; PM approves one scenario.
- Read signals from a Notion database instead of files; web search for market research.

**Phase 3: Business Case + Define (Gates B and C)**
- Business case + forecast agents with explicit assumption tables; PM picks one option.
- Epic, story, acceptance agents; approved stories land in a Notion backlog database.
- Done when: one option goes from signal to backlog stories end to end.

**Phase 4: Measure loop**
- Synthetic analytics; metrics agent compares forecast vs actual; results feed the next Strategy run.

**Phase 5: Build + Run, hardening**
- Build/Run layers reuse coding agents and CI; eval set per layer; cost tracking; scheduled weekly Strategy run; deploy and add a simple login.

## 7. Quality and evaluation

- Per-layer rubric: sourced claims, consistency with `context/`, actionable output, schema-valid.
- Keep a small golden set (one sample product) and re-run after prompt changes.
- Track PM edit distance on gated artifacts as the main usefulness signal.

## 8. Open questions

1. **Repo:** please create an empty GitHub repo (for example `pm-harness`) and add it to this project, so I can push the scaffold. I can't create repos from here.
2. **Notion:** create an internal integration, share one "PM Harness" parent page with it, and set `NOTION_TOKEN` and `NOTION_PARENT_PAGE_ID` in the service environment.
3. **Hosting:** default is a single container on Fly.io or Railway; say if you prefer another host.

## 9. Scaffold

Phase 0 code is in `/mnt/project-files/pm-harness/` (see its README). Tests pass with a fake model. A live run needs an `ANTHROPIC_API_KEY`, and Notion publishing needs a token and a parent page id; neither has been exercised against the live services yet.
