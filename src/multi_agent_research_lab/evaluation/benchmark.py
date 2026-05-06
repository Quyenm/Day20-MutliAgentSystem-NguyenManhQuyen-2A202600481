import re
from collections.abc import Callable
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]

GPT_4O_MINI_INPUT_PER_1M = 0.15
GPT_4O_MINI_OUTPUT_PER_1M = 0.60


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency and return benchmark metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=estimate_cost_usd(state),
        quality_score=score_quality(state),
        citation_coverage=calculate_citation_coverage(state),
        notes=run_notes(state),
    )
    return state, metrics


def calculate_citation_coverage(state: ResearchState) -> float | None:
    """Return the fraction of collected sources cited in the final answer."""

    if not state.sources:
        return None
    if not state.final_answer:
        return 0.0

    cited_indexes = {int(match) for match in re.findall(r"\[(\d+)\]", state.final_answer)}
    covered = sum(1 for index in range(1, len(state.sources) + 1) if index in cited_indexes)
    return covered / len(state.sources)


def token_totals(state: ResearchState) -> dict[str, int]:
    """Return known input/output token totals across baseline trace and agent metadata."""

    totals = {"input_tokens": 0, "output_tokens": 0}
    used_agent_metadata = False
    for event in state.trace:
        payload = event.get("payload", {})
        if event.get("name") == "baseline.complete":
            _add_token_payload(totals, payload)
    for result in state.agent_results:
        used_agent_metadata = True
        _add_token_payload(totals, result.metadata)
    if not used_agent_metadata and totals == {"input_tokens": 0, "output_tokens": 0}:
        for event in state.trace:
            payload = event.get("payload", {})
            metadata = payload.get("metadata")
            if isinstance(metadata, dict):
                _add_token_payload(totals, metadata)
    return totals


def estimate_cost_usd(state: ResearchState) -> float:
    """Estimate OpenAI model cost from known token metadata.

    Uses gpt-4o-mini public pricing assumptions: $0.15 / 1M input tokens and
    $0.60 / 1M output tokens. Web-search tool pricing is not included because the
    OpenAI Responses metadata exposed here does not provide per-search billing data.
    """

    totals = token_totals(state)
    cost = (
        totals["input_tokens"] / 1_000_000 * GPT_4O_MINI_INPUT_PER_1M
        + totals["output_tokens"] / 1_000_000 * GPT_4O_MINI_OUTPUT_PER_1M
    )
    return round(cost, 6)


def score_quality(state: ResearchState) -> float:
    """Return a deterministic rubric score for benchmark comparison."""

    score = 0.0
    if state.final_answer:
        score += 4.0
    if state.sources:
        score += min(2.0, len(state.sources) * 0.4)
    citation_coverage = calculate_citation_coverage(state)
    if citation_coverage is not None:
        score += citation_coverage * 2.0
    if state.route_history == ["researcher", "analyst", "writer", "done"]:
        score += 1.5
    if not state.errors:
        score += 1.0
    return min(10.0, round(score, 1))


def run_notes(state: ResearchState) -> str:
    """Return compact benchmark notes without blank fields."""

    totals = token_totals(state)
    return (
        f"routes={len(state.route_history)} sources={len(state.sources)} "
        f"input_tokens={totals['input_tokens']} output_tokens={totals['output_tokens']}"
    )


def _add_token_payload(totals: dict[str, int], payload: dict[str, Any]) -> None:
    for key in ("input_tokens", "output_tokens"):
        value = payload.get(key)
        if isinstance(value, int):
            totals[key] += value
