import json
from pathlib import Path

from typer.testing import CliRunner

from multi_agent_research_lab.cli import app
from multi_agent_research_lab.core.config import get_settings


def test_benchmark_command_writes_report_and_trace(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["benchmark", "--query", "Summarize production guardrails for LLM agents"],
    )

    assert result.exit_code == 0
    report_path = Path("reports/benchmark_report.md")
    trace_path = Path("reports/last_trace.json")
    hosted_path = Path("reports/hosted_trace_exports.json")
    assert report_path.exists()
    assert trace_path.exists()
    assert hosted_path.exists()

    report = report_path.read_text(encoding="utf-8")
    assert "Benchmark Report" in report
    assert "baseline" in report
    assert "multi-agent" in report
    assert "Citation Coverage" in report
    assert "N/A" in report
    assert "Agent Trace Summary" in report
    assert "researcher" in report
    assert "analyst" in report
    assert "writer" in report

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["run_name"] == "multi-agent"
    assert trace["route_history"] == ["researcher", "analyst", "writer", "done"]
    assert trace["trace"][-1] == {"name": "workflow.end", "payload": {"status": "ok"}}
    hosted_exports = json.loads(hosted_path.read_text(encoding="utf-8"))
    assert hosted_exports == [
        {
            "run_name": "baseline benchmark",
            "provider": "langsmith",
            "status": "skipped",
            "message": "LANGSMITH_API_KEY is not configured",
            "run_id": None,
            "url": None,
        },
        {
            "run_name": "baseline benchmark",
            "provider": "langfuse",
            "status": "skipped",
            "message": "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not configured",
            "run_id": None,
            "url": None,
        },
        {
            "run_name": "multi-agent benchmark",
            "provider": "langsmith",
            "status": "skipped",
            "message": "LANGSMITH_API_KEY is not configured",
            "run_id": None,
            "url": None,
        },
        {
            "run_name": "multi-agent benchmark",
            "provider": "langfuse",
            "status": "skipped",
            "message": "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not configured",
            "run_id": None,
            "url": None,
        },
    ]
    get_settings.cache_clear()
