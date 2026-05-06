import json
from pathlib import Path

from typer.testing import CliRunner

from multi_agent_research_lab.cli import app
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
    SourceDocument,
)
from multi_agent_research_lab.core.state import ResearchState


def _baseline_state(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    state.final_answer = "Baseline answer"
    state.add_trace_event("baseline.complete", {"input_tokens": 12, "output_tokens": 24})
    return state


def _multi_state(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    state.route_history = ["researcher", "analyst", "writer", "done"]
    state.sources = [
        SourceDocument(
            title="OpenAI Guardrails",
            url="https://example.com/guardrails",
            snippet="Guardrails source",
            metadata={"provider": "openai_web_search"},
        )
    ]
    state.final_answer = "Multi-agent answer [1]"
    state.agent_results = [
        AgentResult(
            agent=AgentName.RESEARCHER,
            content="Research notes",
            metadata={"source_count": 1},
        ),
        AgentResult(
            agent=AgentName.ANALYST,
            content="Analysis notes",
            metadata={"input_tokens": 30, "output_tokens": 40},
        ),
        AgentResult(
            agent=AgentName.WRITER,
            content="Writer answer",
            metadata={"input_tokens": 50, "output_tokens": 60},
        ),
    ]
    agent_names = ["researcher", "analyst", "writer"]
    for agent, duration in [("researcher", 0.5), ("analyst", 0.7), ("writer", 0.9)]:
        state.add_trace_event(
            "agent.end",
            {
                "agent": agent,
                "status": "ok",
                "duration_seconds": duration,
                "metadata": state.agent_results[agent_names.index(agent)].metadata,
            },
        )
    return state


def test_build_demo_payload_compares_baseline_and_multi_agent(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    from multi_agent_research_lab.web.backend import build_demo_payload

    payload = build_demo_payload(
        "Summarize production guardrails for LLM agents",
        baseline_runner=_baseline_state,
        multi_runner=_multi_state,
        export_hosted=False,
    )

    assert payload["query"] == "Summarize production guardrails for LLM agents"
    assert payload["runs"]["baseline"]["answer"] == "Baseline answer"
    assert payload["runs"]["baseline"]["flow"]["nodes"][1]["label"] == "Baseline LLM"
    assert payload["runs"]["baseline"]["tools"][0]["name"] == "OpenAI Responses API"
    assert payload["runs"]["multi_agent"]["answer"] == "Multi-agent answer [1]"
    assert [node["id"] for node in payload["runs"]["multi_agent"]["flow"]["nodes"]] == [
        "query",
        "researcher",
        "analyst",
        "writer",
        "answer",
    ]
    assert payload["runs"]["multi_agent"]["tools"][0]["name"] == "OpenAI web_search_preview"
    assert payload["comparison"]["source_delta"] == 1
    assert payload["comparison"]["citation_coverage_delta"] == 1.0
    assert Path("reports/web_demo_last_run.json").exists()
    assert Path("reports/benchmark_report.md").exists()
    get_settings.cache_clear()


def test_static_index_contains_demo_ui_sections() -> None:
    from multi_agent_research_lab.web.server import load_frontend_asset

    html = load_frontend_asset("index.html")

    assert "Baseline" in html
    assert "Multi-Agent" in html
    assert "Flow Graph" in html
    assert "Benchmark" in html


def test_web_cli_command_is_registered() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["web", "--help"])

    assert result.exit_code == 0
    assert "localhost web demo" in result.output


def test_demo_payload_is_json_serializable(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    from multi_agent_research_lab.web.backend import build_demo_payload

    payload = build_demo_payload(
        "Summarize production guardrails for LLM agents",
        baseline_runner=_baseline_state,
        multi_runner=_multi_state,
        export_hosted=False,
    )

    encoded = json.dumps(payload)

    assert "multi_agent" in encoded
    get_settings.cache_clear()
