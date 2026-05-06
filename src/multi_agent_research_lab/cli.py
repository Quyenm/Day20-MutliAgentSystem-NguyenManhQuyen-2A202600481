"""Command-line entrypoint for the lab starter."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.hosted import export_hosted_traces
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore
from multi_agent_research_lab.web.server import serve

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline."""

    _init()
    state = _run_baseline(query)
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Workflow Error", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run baseline and multi-agent benchmarks, then write report artifacts."""

    _init()
    baseline_state, baseline_metrics = run_benchmark("baseline", query, _run_baseline)
    multi_state, multi_metrics = run_benchmark("multi-agent", query, _run_multi_agent)

    store = LocalArtifactStore()
    report_path = store.write_text(
        "benchmark_report.md",
        render_markdown_report([baseline_metrics, multi_metrics], trace_state=multi_state),
    )
    trace_path = store.write_text(
        "last_trace.json",
        json.dumps(
            {
                "run_name": "multi-agent",
                "route_history": multi_state.route_history,
                "trace": multi_state.trace,
                "agent_results": [item.model_dump() for item in multi_state.agent_results],
            },
            indent=2,
        ),
    )
    hosted_exports = [
        *export_hosted_traces(baseline_state, "baseline benchmark"),
        *export_hosted_traces(multi_state, "multi-agent benchmark"),
    ]
    hosted_path = store.write_text(
        "hosted_trace_exports.json",
        json.dumps([item.as_dict() for item in hosted_exports], indent=2),
    )

    console.print(Panel.fit(str(report_path), title="Benchmark Report"))
    console.print(Panel.fit(str(trace_path), title="Trace Export"))
    console.print(Panel.fit(str(hosted_path), title="Hosted Trace Export"))
    console.print(baseline_state.final_answer or "")
    console.print(multi_state.final_answer or "")


@app.command()
def web(
    host: Annotated[
        str,
        typer.Option("--host", help="Host for the localhost web demo"),
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Port for the localhost web demo")] = 8000,
) -> None:
    """Run the localhost web demo for side-by-side benchmark comparison."""

    _init()
    url = f"http://{host}:{port}"
    console.print(Panel.fit(url, title="Localhost Web Demo"))
    serve(host=host, port=port)


def _run_baseline(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    response = LLMClient().complete(
        system_prompt=(
            "You are a single-agent research baseline. Answer directly and concisely. "
            "Do not claim external sources unless provided."
        ),
        user_prompt=query,
    )
    state.final_answer = response.content
    state.add_trace_event(
        "baseline.complete",
        {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens},
    )
    return state


def _run_multi_agent(query: str) -> ResearchState:
    return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))


if __name__ == "__main__":
    app()
