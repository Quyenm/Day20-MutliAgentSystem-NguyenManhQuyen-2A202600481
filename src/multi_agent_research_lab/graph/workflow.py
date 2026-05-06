"""LangGraph workflow skeleton."""

from time import perf_counter

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def build(self) -> dict[str, BaseAgent]:
        """Create the minimal runnable workflow nodes.

        This deliberately avoids a hard LangGraph dependency for the MVP path. The
        same node contract can be moved into a compiled graph later.
        """

        return {
            "supervisor": SupervisorAgent(),
            "researcher": ResearcherAgent(),
            "analyst": AnalystAgent(),
            "writer": WriterAgent(),
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.

        Run supervisor-directed nodes until the supervisor emits `done`.
        """

        nodes = self.build()
        state.add_trace_event("workflow.start", {"query": state.request.query})

        while True:
            state = nodes["supervisor"].run(state)
            route = state.route_history[-1]
            state.add_trace_event("workflow.route", {"next": route})

            if route == "done":
                state.add_trace_event("workflow.end", {"status": "ok"})
                return state

            node = nodes.get(route)
            if node is None:
                raise AgentExecutionError(f"Supervisor selected unknown route: {route}")
            state = self._run_agent_node(route, node, state)

    def _run_agent_node(self, route: str, node: BaseAgent, state: ResearchState) -> ResearchState:
        state.add_trace_event("agent.start", {"agent": route})
        started = perf_counter()
        before_results = len(state.agent_results)
        try:
            state = node.run(state)
        except Exception as exc:
            state.add_trace_event(
                "agent.end",
                {
                    "agent": route,
                    "status": "error",
                    "duration_seconds": perf_counter() - started,
                    "error": str(exc),
                },
            )
            raise

        payload = {
            "agent": route,
            "status": "ok",
            "duration_seconds": perf_counter() - started,
        }
        if len(state.agent_results) > before_results:
            payload["metadata"] = state.agent_results[-1].metadata
        state.add_trace_event("agent.end", payload)
        return state
