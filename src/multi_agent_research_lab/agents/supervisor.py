"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        Route through a minimal linear MVP: researcher -> analyst -> writer -> done.
        """

        if state.iteration >= get_settings().max_iterations:
            raise AgentExecutionError("Supervisor stopped: max iterations exceeded")

        if state.research_notes is None:
            route = "researcher"
        elif state.analysis_notes is None:
            route = "analyst"
        elif state.final_answer is None:
            route = "writer"
        else:
            route = "done"

        state.record_route(route)
        return state
