"""Hosted trace exporters for LangSmith and Langfuse.

The local JSON trace remains the source artifact for the lab. These exporters mirror the same
run into hosted observability tools when credentials are configured.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


@dataclass(frozen=True)
class HostedTraceExport:
    """Result for one hosted tracing provider."""

    run_name: str
    provider: str
    status: str
    message: str
    run_id: str | None = None
    url: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "run_name": self.run_name,
            "provider": self.provider,
            "status": self.status,
            "message": self.message,
            "run_id": self.run_id,
            "url": self.url,
        }


def export_hosted_traces(
    state: ResearchState,
    run_name: str,
    settings: Settings | None = None,
) -> list[HostedTraceExport]:
    """Export a completed research state to configured hosted trace providers."""

    active_settings = settings or get_settings()
    return [
        export_langsmith_trace(state, run_name, active_settings),
        export_langfuse_trace(state, run_name, active_settings),
    ]


def export_langsmith_trace(
    state: ResearchState,
    run_name: str,
    settings: Settings,
    client_factory: Callable[..., Any] | None = None,
) -> HostedTraceExport:
    """Create one LangSmith parent run with child runs for each agent."""

    if not settings.langsmith_api_key:
        return HostedTraceExport(
            run_name,
            "langsmith",
            "skipped",
            "LANGSMITH_API_KEY is not configured",
        )

    try:
        if client_factory is None:
            from langsmith import Client

            client_factory = Client
        client = client_factory(api_key=settings.langsmith_api_key)
        parent_id = uuid4()
        start_time, end_time = _workflow_times(state)
        client.create_run(
            id=parent_id,
            name=run_name,
            run_type="chain",
            project_name=settings.langsmith_project,
            inputs={"query": state.request.query},
            outputs={
                "final_answer": state.final_answer,
                "route_history": state.route_history,
                "source_count": len(state.sources),
            },
            start_time=start_time,
            end_time=end_time,
            extra={
                "metadata": {
                    "app": "multi-agent-research-lab",
                    "trace_event_count": len(state.trace),
                }
            },
        )

        for result in state.agent_results:
            metadata = dict(result.metadata)
            child_start, child_end = _agent_times(state, str(result.agent), end_time)
            client.create_run(
                id=uuid4(),
                parent_run_id=parent_id,
                name=str(result.agent),
                run_type="chain",
                project_name=settings.langsmith_project,
                inputs={"query": state.request.query},
                outputs={"content": result.content},
                start_time=child_start,
                end_time=child_end,
                extra={"metadata": metadata},
            )

        flush = getattr(client, "flush", None)
        if callable(flush):
            flush()

        url = _langsmith_run_url(client, parent_id)
        return HostedTraceExport(
            run_name,
            "langsmith",
            "exported",
            f"Exported to LangSmith project {settings.langsmith_project}",
            run_id=str(parent_id),
            url=url,
        )
    except Exception as exc:  # pragma: no cover - defensive for optional external SDK/network.
        return HostedTraceExport(
            run_name,
            "langsmith",
            "failed",
            f"{type(exc).__name__}: {exc}",
        )


def export_langfuse_trace(
    state: ResearchState,
    run_name: str,
    settings: Settings,
    client_factory: Callable[..., Any] | None = None,
) -> HostedTraceExport:
    """Create one Langfuse trace with child observations for each agent."""

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return HostedTraceExport(
            run_name,
            "langfuse",
            "skipped",
            "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not configured",
        )

    try:
        if client_factory is None:
            from langfuse import Langfuse

            client_factory = Langfuse
        base_url = settings.langfuse_base_url or settings.langfuse_host
        langfuse = client_factory(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=base_url,
        )
        trace_id = None
        with langfuse.start_as_current_observation(
            as_type="span",
            name=run_name,
            input={"query": state.request.query},
            metadata={
                "route_history": state.route_history,
                "source_count": len(state.sources),
                "trace_event_count": len(state.trace),
            },
        ) as root:
            trace_id = getattr(root, "trace_id", None) or _safe_call(
                langfuse,
                "get_current_trace_id",
            )
            for result in state.agent_results:
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name=str(result.agent),
                    input={"query": state.request.query},
                    metadata=dict(result.metadata),
                ) as span:
                    _safe_update(span, output={"content": result.content})
            _safe_update(root, output={"final_answer": state.final_answer})

        flush = getattr(langfuse, "flush", None)
        if callable(flush):
            flush()

        url = _langfuse_trace_url(base_url, trace_id)
        return HostedTraceExport(
            run_name,
            "langfuse",
            "exported",
            "Exported to Langfuse",
            run_id=str(trace_id) if trace_id else None,
            url=url,
        )
    except Exception as exc:  # pragma: no cover - defensive for optional external SDK/network.
        return HostedTraceExport(
            run_name,
            "langfuse",
            "failed",
            f"{type(exc).__name__}: {exc}",
        )


def _workflow_times(state: ResearchState) -> tuple[datetime, datetime]:
    end_time = datetime.now(UTC)
    total_duration = sum(
        float(event["payload"].get("duration_seconds", 0))
        for event in state.trace
        if event.get("name") == "agent.end"
    )
    return end_time - timedelta(seconds=total_duration), end_time


def _agent_times(
    state: ResearchState,
    agent_name: str,
    workflow_end_time: datetime,
) -> tuple[datetime, datetime]:
    duration = 0.0
    for event in state.trace:
        if event.get("name") != "agent.end":
            continue
        payload = event.get("payload", {})
        if payload.get("agent") == agent_name:
            duration = float(payload.get("duration_seconds", 0))
            break
    return workflow_end_time - timedelta(seconds=duration), workflow_end_time


def _langsmith_run_url(client: Any, run_id: Any) -> str | None:
    get_run_url = getattr(client, "get_run_url", None)
    if not callable(get_run_url):
        return None
    try:
        return str(get_run_url(run_id))
    except Exception:
        return None


def _langfuse_trace_url(base_url: str, trace_id: Any) -> str | None:
    if not trace_id:
        return None
    return f"{base_url.rstrip('/')}/trace/{trace_id}"


def _safe_update(observation: Any, **kwargs: Any) -> None:
    update = getattr(observation, "update", None)
    if callable(update):
        update(**kwargs)


def _safe_call(target: Any, method_name: str) -> Any:
    method = getattr(target, method_name, None)
    if callable(method):
        return method()
    return None
