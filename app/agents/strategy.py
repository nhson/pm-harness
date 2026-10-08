"""Layer 1, Strategy: turn every signal into options."""

from concurrent.futures import ThreadPoolExecutor

from app.agents.base import Agent
from app.llm import LLM
from app.schemas import CustomerSignals, MarketResearch, PortfolioMap, StrategyOptions

market_research = Agent(
    "Market research agent",
    "Track competitors and market trends. Report what competitors shipped or changed and what it implies for us.",
    MarketResearch,
)
customer_signal = Agent(
    "Customer signal agent",
    "Read interviews and support tickets. Cluster them into distinct customer pains, counting how many signals mention each.",
    CustomerSignals,
)
portfolio = Agent(
    "Portfolio agent",
    "Map the company goals to current strategic bets and name the gaps where no bet covers a goal.",
    PortfolioMap,
)
merge = Agent(
    "Strategy lead",
    "Combine the research, customer pains and portfolio map into 3 to 6 distinct opportunities. "
    "Each must link to one goal id, carry the evidence from the inputs, and state a confidence.",
    StrategyOptions,
)


def run(llm: LLM, context: str, signals: str) -> StrategyOptions:
    jobs = {
        market_research: f"<context>\n{context}\n</context>",
        customer_signal: f"<signals>\n{signals}\n</signals>",
        portfolio: f"<context>\n{context}\n</context>",
    }
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {agent.name: pool.submit(agent.run, llm, prompt) for agent, prompt in jobs.items()}
        results = {name: f.result() for name, f in futures.items()}

    merged_inputs = "\n\n".join(
        f'<agent_output name="{name}">\n{out.model_dump_json(indent=2)}\n</agent_output>' for name, out in results.items()
    )
    return merge.run(llm, f"<context>\n{context}\n</context>\n\n{merged_inputs}")
