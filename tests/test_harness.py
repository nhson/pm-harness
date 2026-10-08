from fastapi.testclient import TestClient

from app import main
from app.notion import to_blocks
from app.schemas import (
    CustomerPain,
    CustomerSignals,
    Evidence,
    GoalMapping,
    MarketFinding,
    MarketResearch,
    Opportunity,
    PortfolioMap,
    StrategyOptions,
)
from app.store import Store

EV = [Evidence(source_id="interviews/INT-01.md", quote_or_fact="reminders all sound the same")]

CANNED = {
    MarketResearch: MarketResearch(findings=[MarketFinding(competitor_or_trend="Invoicely Pro", finding="AI reminders", implication="parity risk", evidence=EV)]),
    CustomerSignals: CustomerSignals(pains=[CustomerPain(pain="Generic reminders", segment="Team", frequency=5, evidence=EV)]),
    PortfolioMap: PortfolioMap(goals=[GoalMapping(goal_id="G1", goal="NRR 106%", bets=[], gaps=["Team churn"])]),
    StrategyOptions: StrategyOptions(
        summary="One option",
        opportunities=[
            Opportunity(
                id="OPP-1", title="Personal reminders", problem="Ignored reminders", target_segment="Team",
                linked_goal_id="G2", evidence=EV, confidence="medium", unsourced_claims=[],
            )
        ],
    ),
}


class FakeLLM:
    def __init__(self):
        self.calls = []

    def structured(self, system, prompt, schema):
        self.calls.append((system, prompt, schema))
        return CANNED[schema]


def make_client(tmp_path):
    fake = FakeLLM()
    store = Store(str(tmp_path / "test.db"))
    main.app.dependency_overrides = {
        main.get_store: lambda: store,
        main.get_llm: lambda: fake,
        main.get_publisher: lambda: None,
    }
    return TestClient(main.app), fake, store


def test_strategy_run_calls_three_agents_then_merge(tmp_path):
    client, fake, store = make_client(tmp_path)
    resp = client.post("/layers/strategy/run")
    assert resp.status_code == 200, resp.text
    assert resp.json()["artifact"]["opportunities"][0]["id"] == "OPP-1"
    schemas = [c[2] for c in fake.calls]
    assert set(schemas[:3]) == {MarketResearch, CustomerSignals, PortfolioMap}
    assert schemas[3] is StrategyOptions
    # Signals reach the customer signal agent with citable ids
    signal_prompt = next(c[1] for c in fake.calls if c[2] is CustomerSignals)
    assert 'source id="interviews/INT-01.md"' in signal_prompt
    assert "T-001" in signal_prompt
    assert store.latest("strategy", "options")["id"] == resp.json()["artifact_id"]


def test_unknown_layer_is_404(tmp_path):
    client, _, _ = make_client(tmp_path)
    assert client.post("/layers/nope/run").status_code == 404


def test_gate_approval_flow(tmp_path):
    store = Store(str(tmp_path / "g.db"))
    aid = store.save("roadmap", "scenarios", CANNED[StrategyOptions], gated=True)
    assert store.latest_approved("roadmap") is None
    store.decide(aid, approve=True, decision="Scenario B")
    assert store.latest_approved("roadmap")["id"] == aid


def test_notion_blocks_render_artifact():
    blocks = to_blocks(CANNED[StrategyOptions].model_dump())
    kinds = {b["type"] for b in blocks}
    assert {"heading_2", "heading_3", "bulleted_list_item"} <= kinds
