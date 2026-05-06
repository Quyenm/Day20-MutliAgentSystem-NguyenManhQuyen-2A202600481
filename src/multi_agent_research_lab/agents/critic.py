"""Optional critic agent for lightweight final-answer review."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import calculate_citation_coverage


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final-answer evidence and append review metadata."""

        citation_coverage = calculate_citation_coverage(state)
        has_final_answer = bool(state.final_answer)
        notes = [
            f"Final answer present: {has_final_answer}",
            f"Sources available: {len(state.sources)}",
        ]
        if citation_coverage is not None:
            notes.append(f"Citation coverage: {citation_coverage:.0%}")
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content="\n".join(notes),
                metadata={
                    "source_count": len(state.sources),
                    "citation_coverage": citation_coverage,
                    "has_final_answer": has_final_answer,
                },
            )
        )
        return state
