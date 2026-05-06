from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.hosted import (
    export_hosted_traces,
    export_langfuse_trace,
    export_langsmith_trace,
)


def _state() -> ResearchState:
    state = ResearchState(request=ResearchQuery(query="Summarize LLM agent guardrails"))
    state.route_history = ["researcher", "analyst", "writer", "done"]
    state.final_answer = "Final answer"
    state.add_trace_event("agent.end", {"agent": "analyst", "duration_seconds": 1.2})
    state.add_trace_event("agent.end", {"agent": "writer", "duration_seconds": 2.3})
    state.agent_results = [
        AgentResult(agent=AgentName.ANALYST, content="Analysis", metadata={"input_tokens": 10}),
        AgentResult(agent=AgentName.WRITER, content="Report", metadata={"output_tokens": 20}),
    ]
    return state


def test_hosted_export_skips_when_credentials_missing() -> None:
    results = export_hosted_traces(
        _state(),
        "test run",
        Settings(
            langsmith_api_key="",
            langfuse_public_key="",
            langfuse_secret_key="",
        ),
    )

    assert [item.provider for item in results] == ["langsmith", "langfuse"]
    assert [item.run_name for item in results] == ["test run", "test run"]
    assert [item.status for item in results] == ["skipped", "skipped"]


def test_langsmith_export_creates_parent_and_agent_runs() -> None:
    calls: list[dict[str, Any]] = []

    class FakeLangSmithClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def create_run(self, **kwargs: Any) -> None:
            calls.append(kwargs)

        def flush(self) -> None:
            calls.append({"flushed": True})

        def get_run_url(self, run_id: Any) -> str:
            return f"https://smith.langchain.com/r/{run_id}"

    result = export_langsmith_trace(
        _state(),
        "test run",
        Settings(langsmith_api_key="ls-test", langsmith_project="lab-project"),
        client_factory=FakeLangSmithClient,
    )

    assert result.status == "exported"
    assert result.run_name == "test run"
    assert result.url and "smith.langchain.com" in result.url
    run_calls = [item for item in calls if "run_type" in item]
    assert [item["name"] for item in run_calls] == ["test run", "analyst", "writer"]
    assert run_calls[1]["parent_run_id"] == run_calls[0]["id"]
    assert run_calls[2]["extra"]["metadata"] == {"output_tokens": 20}


def test_langfuse_export_creates_root_and_agent_observations() -> None:
    observations: list[dict[str, Any]] = []

    class FakeObservation:
        trace_id = "1234567890abcdef1234567890abcdef"

        def __init__(self, record: dict[str, Any]) -> None:
            self.record = record

        def update(self, **kwargs: Any) -> None:
            self.record.setdefault("updates", []).append(kwargs)

    class FakeLangfuse:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.flushed = False

        @contextmanager
        def start_as_current_observation(self, **kwargs: Any):
            observations.append(kwargs)
            yield FakeObservation(kwargs)

        def flush(self) -> None:
            self.flushed = True

    result = export_langfuse_trace(
        _state(),
        "test run",
        Settings(
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
            langfuse_host="https://cloud.langfuse.com",
        ),
        client_factory=FakeLangfuse,
    )

    assert result.status == "exported"
    assert result.run_name == "test run"
    assert result.url == "https://cloud.langfuse.com/trace/1234567890abcdef1234567890abcdef"
    assert [item["name"] for item in observations] == ["test run", "analyst", "writer"]
    assert observations[1]["metadata"] == {"input_tokens": 10}
