from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.fact_search import FactQueryGenerator, WikipediaClient, extract_queries
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, response: LLMResponse):
        self.provider_name = name
        self.model = f"{name}-model"
        self.response = response

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return self.response


def test_build_prompt_includes_original_request_and_query_instructions():
    generator = FactQueryGenerator(max_tokens=100, max_queries=3)
    prompt = generator.build_prompt("¿Quién fue Alan Turing?")
    assert "¿Quién fue Alan Turing?" in prompt
    assert "one per line" in prompt


@pytest.mark.asyncio
async def test_run_returns_providers_generated_content():
    provider = FakeProvider("openai", LLMResponse(provider="openai", model="gpt", content="Alan Turing"))
    generator = FactQueryGenerator(max_tokens=100)
    response = await generator.run(provider, "original request")
    assert response.content == "Alan Turing"


def test_extract_queries_splits_by_line_and_strips_bullets():
    content = "- Alan Turing born date\n2. Alan Turing Enigma\n\nAlan Turing death"
    queries = extract_queries(content, max_queries=5)
    assert queries == ["Alan Turing born date", "Alan Turing Enigma", "Alan Turing death"]


def test_extract_queries_respects_max_queries():
    content = "a\nb\nc\nd"
    assert extract_queries(content, max_queries=2) == ["a", "b"]


def test_extract_queries_returns_empty_list_for_no_content():
    assert extract_queries(None, max_queries=3) == []
    assert extract_queries("", max_queries=3) == []


@pytest.mark.asyncio
async def test_search_and_summarize_returns_result_on_success():
    search_payload = {"query": {"search": [{"title": "Alan Turing"}]}}
    summary_payload = {
        "title": "Alan Turing",
        "extract": "Alan Turing fue un matemático británico.",
        "content_urls": {"desktop": {"page": "https://es.wikipedia.org/wiki/Alan_Turing"}},
    }

    search_response = MagicMock()
    search_response.raise_for_status = MagicMock()
    search_response.json.return_value = search_payload

    summary_response = MagicMock()
    summary_response.raise_for_status = MagicMock()
    summary_response.json.return_value = summary_payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[search_response, summary_response])
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("app.core.fact_search.httpx.AsyncClient", return_value=mock_client):
        client = WikipediaClient(language="es", timeout_seconds=5.0)
        result = await client.search_and_summarize("Alan Turing")

    assert result.succeeded
    assert result.title == "Alan Turing"
    assert result.extract == "Alan Turing fue un matemático británico."
    assert result.url == "https://es.wikipedia.org/wiki/Alan_Turing"


@pytest.mark.asyncio
async def test_search_and_summarize_handles_no_search_results():
    search_response = MagicMock()
    search_response.raise_for_status = MagicMock()
    search_response.json.return_value = {"query": {"search": []}}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=search_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("app.core.fact_search.httpx.AsyncClient", return_value=mock_client):
        client = WikipediaClient(language="es", timeout_seconds=5.0)
        result = await client.search_and_summarize("consulta sin resultados xyz123")

    assert not result.succeeded
    assert result.error is not None


@pytest.mark.asyncio
async def test_search_and_summarize_degrades_on_exception():
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=RuntimeError("network boom"))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("app.core.fact_search.httpx.AsyncClient", return_value=mock_client):
        client = WikipediaClient(language="es", timeout_seconds=5.0)
        result = await client.search_and_summarize("Alan Turing")

    assert not result.succeeded
    assert "network boom" in result.error
