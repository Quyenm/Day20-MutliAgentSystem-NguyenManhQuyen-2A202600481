"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Extract a compact analysis from the research notes and sources.
        """

        response = self.llm_client.complete(
            system_prompt=(
                "You are the analyst agent in a multi-agent research workflow. "
                "Extract key claims, compare viewpoints, flag weak evidence, and "
                "keep source numbers like [1] when referring to evidence."
            ),
            user_prompt=self._build_user_prompt(state),
        )
        state.analysis_notes = response.content
        metadata = {
            key: value
            for key, value in {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            }.items()
            if value is not None
        }
        state.agent_results.append(
            AgentResult(agent=AgentName.ANALYST, content=state.analysis_notes, metadata=metadata)
        )
        return state

    def _build_user_prompt(self, state: ResearchState) -> str:
        sources = "\n".join(
            f"[{index + 1}] {source.title}: {source.snippet}"
            for index, source in enumerate(state.sources)
        )
        if not sources:
            sources = "No sources collected."

        return "\n\n".join(
            [
                f"Query: {state.request.query}",
                f"Audience: {state.request.audience}",
                f"Research notes:\n{state.research_notes or 'No research notes.'}",
                f"Sources:\n{sources}",
                (
                    "Return concise analysis with sections: Key claims, "
                    "Evidence strength, Weak or missing evidence, Suggested answer angle."
                ),
            ]
        )
