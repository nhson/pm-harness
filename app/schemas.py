"""Artifact schemas: the contract between layers."""

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["low", "medium", "high"]


class Evidence(BaseModel):
    source_id: str = Field(description="Id of the signal, ticket, interview or context file")
    quote_or_fact: str


# ---- Layer 1: Strategy ----
class MarketFinding(BaseModel):
    competitor_or_trend: str
    finding: str
    implication: str
    evidence: list[Evidence]


class MarketResearch(BaseModel):
    findings: list[MarketFinding]


class CustomerPain(BaseModel):
    pain: str
    segment: str
    frequency: int = Field(description="Number of distinct signals mentioning this pain")
    evidence: list[Evidence]


class CustomerSignals(BaseModel):
    pains: list[CustomerPain]


class GoalMapping(BaseModel):
    goal_id: str
    goal: str
    bets: list[str]
    gaps: list[str]


class PortfolioMap(BaseModel):
    goals: list[GoalMapping]


class Opportunity(BaseModel):
    id: str = Field(description="Short slug, e.g. OPP-1")
    title: str
    problem: str
    target_segment: str
    linked_goal_id: str
    evidence: list[Evidence]
    confidence: Confidence
    unsourced_claims: list[str] = Field(description="Claims made without a source, flagged for the PM")


class StrategyOptions(BaseModel):
    summary: str
    opportunities: list[Opportunity]


# ---- Later layers (schemas defined now so hand-offs are fixed) ----
class BacklogItem(BaseModel):
    opportunity_id: str
    title: str
    effort_weeks: float
    rank: int
    notes: str


class Scenario(BaseModel):
    name: str
    items: list[BacklogItem]
    capacity_used_weeks: float
    tradeoffs: str


class RoadmapScenarios(BaseModel):
    capacity_weeks: float
    scenarios: list[Scenario]


class BusinessCase(BaseModel):
    opportunity_id: str
    cost_eur: float
    effort_weeks: float
    kpi: str
    forecast_delta: str
    assumptions: list[str]
    strategic_fit: Confidence


class Story(BaseModel):
    id: str
    title: str
    user_story: str
    acceptance_criteria: list[str] = Field(description="Given/When/Then statements")


class Epic(BaseModel):
    title: str
    problem: str
    goal_kpi: str
    scope: list[str]
    non_goals: list[str]
    stories: list[Story]
