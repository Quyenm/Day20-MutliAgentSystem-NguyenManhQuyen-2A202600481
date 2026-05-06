"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from typing import Any

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError

_UNSET = object()

@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client skeleton."""

    def __init__(
        self,
        api_key: str | None | object = _UNSET,
        model: str | None = None,
        openai_client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key if api_key is _UNSET else api_key
        self.model = model or settings.openai_model
        self._openai_client = openai_client

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        Return a deterministic local completion by default.

        Keep provider retry, timeout, and token logging here rather than inside agents
        when replacing this with OpenAI, Azure OpenAI, or another provider.
        """

        if self.api_key:
            return self._complete_with_openai(system_prompt, user_prompt)

        return self._local_complete(system_prompt, user_prompt)

    def _complete_with_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        client = self._openai_client or self._build_openai_client()
        response = client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )

        content = getattr(response, "output_text", None) or self._extract_output_text(response)
        if not content:
            raise AgentExecutionError("OpenAI response did not contain output text")

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
        output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _build_openai_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AgentExecutionError(
                "OPENAI_API_KEY is set, but the `openai` package is not installed. "
                "Run `pip install -e \"[llm]\"` or install `openai`."
            ) from exc

        return OpenAI(api_key=self.api_key)

    def _extract_output_text(self, response: Any) -> str:
        parts: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(parts)

    def _local_complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        content = "\n".join(
            [
                "Local LLM draft.",
                f"System: {system_prompt.strip()}",
                f"User: {user_prompt.strip()}",
            ]
        )
        return LLMResponse(content=content)
