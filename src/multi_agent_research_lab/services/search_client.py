"""Search client abstraction for ResearcherAgent."""

from typing import Any, cast

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import SourceDocument

_UNSET = object()


class SearchClient:
    """Provider-agnostic search client skeleton."""

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

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Use OpenAI hosted web search when an API key is configured. Return deterministic
        local results when no key is available so the lab can run offline.
        """

        if self.api_key:
            return self._search_with_openai(query, max_results)

        return self._local_search(query, max_results)

    def _search_with_openai(self, query: str, max_results: int) -> list[SourceDocument]:
        client = self._openai_client or self._build_openai_client()
        response = client.responses.create(
            model=self.model,
            input=f"Find reliable sources for: {query}",
            tools=[{"type": "web_search_preview"}],
        )

        documents = self._extract_cited_documents(response, max_results)
        if documents:
            return documents
        raise AgentExecutionError("OpenAI web search returned no URL citations")

    def _build_openai_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AgentExecutionError(
                "OPENAI_API_KEY is set, but the `openai` package is not installed. "
                "Run `pip install -e \"[llm]\"` or install `openai`."
            ) from exc

        return OpenAI(api_key=cast(str | None, self.api_key))

    def _extract_cited_documents(self, response: Any, max_results: int) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        seen_urls: set[str] = set()
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", "") or ""
                for annotation in getattr(content, "annotations", []) or []:
                    if getattr(annotation, "type", None) != "url_citation":
                        continue
                    url = getattr(annotation, "url", None)
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    documents.append(
                        SourceDocument(
                            title=getattr(annotation, "title", None) or url,
                            url=url,
                            snippet=self._snippet_for_annotation(text, annotation),
                            metadata={
                                "provider": "openai_web_search",
                                "rank": len(documents) + 1,
                            },
                        )
                    )
                    if len(documents) >= max_results:
                        return documents
        return documents

    def _snippet_for_annotation(self, text: str, annotation: Any) -> str:
        start = getattr(annotation, "start_index", None)
        end = getattr(annotation, "end_index", None)
        if isinstance(start, int) and isinstance(end, int) and end > start:
            return text[start:end].strip()
        return text[:500].strip()

    def _local_search(self, query: str, max_results: int) -> list[SourceDocument]:
        return [
            SourceDocument(
                title=f"Local source {index + 1}: {query}",
                url=None,
                snippet=(
                    f"Reference note {index + 1} for '{query}'. Focus on role clarity, "
                    "state handoffs, guardrails, tracing, and measurable evaluation."
                ),
                metadata={"provider": "local", "rank": index + 1},
            )
            for index in range(max_results)
        ]
