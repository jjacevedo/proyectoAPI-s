from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.providers.base import LLMProvider, LLMResponse


class FactQueryGenerator:
    """Genera hasta N consultas de busqueda cortas y especificas a partir de
    la solicitud original, ANTES de ver ninguna respuesta candidata, para
    que la busqueda no este sesgada hacia la afirmacion de ningun candidato
    en particular (mismo principio que TestCaseGenerator/
    SolverScriptGenerator). Mismo patron: arma un prompt y llama a
    provider.generate().
    """

    def __init__(self, max_tokens: int, max_queries: int = 3) -> None:
        self.max_tokens = max_tokens
        self.max_queries = max_queries

    def build_prompt(self, original_prompt: str) -> str:
        return "\n".join([
            f"You are generating up to {self.max_queries} short, specific Wikipedia search "
            "queries to fact-check the request below, BEFORE seeing any candidate answer.",
            "Return ONLY the queries, one per line, no numbering, no bullet points, no "
            "explanation, no extra text.",
            "Each query should target a single verifiable fact (a name, date, place, or "
            "quantity), not the whole request verbatim.",
            "\nREQUEST:\n" + original_prompt,
        ])

    async def run(self, provider: LLMProvider, original_prompt: str) -> LLMResponse:
        prompt = self.build_prompt(original_prompt)
        return await provider.generate(prompt, max_tokens=self.max_tokens)


def extract_queries(content: str | None, max_queries: int) -> list[str]:
    """Parsea las consultas generadas (una por linea, tolerando vinetas o
    numeracion accidental). Lista vacia si no hay contenido."""
    if not content:
        return []
    queries = []
    for line in content.splitlines():
        cleaned = line.strip(" -*\t0123456789.)")
        if cleaned:
            queries.append(cleaned)
    return queries[:max_queries]


class FactCheckResult(BaseModel):
    query: str
    title: str | None = None
    extract: str | None = None
    url: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.extract is not None


class WikipediaClient:
    """Cliente de la API publica de Wikipedia (sin API key, sin cuenta):
    busca la pagina mas relevante para una consulta y devuelve su resumen
    como evidencia externa independiente de los candidatos. Nunca lanza:
    cualquier fallo de red/parseo se traduce en un FactCheckResult con
    `error` (mismo principio de degradacion elegante que el resto del
    sistema).
    """

    def __init__(self, language: str, timeout_seconds: float) -> None:
        self.language = language
        self.timeout_seconds = timeout_seconds

    async def search_and_summarize(self, query: str) -> FactCheckResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                search_response = await client.get(
                    f"https://{self.language}.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "format": "json",
                        "srlimit": 1,
                        "srsearch": query,
                    },
                )
                search_response.raise_for_status()
                results = search_response.json().get("query", {}).get("search", [])
                if not results:
                    return FactCheckResult(query=query, error="no se encontraron resultados en Wikipedia")
                title = results[0]["title"]

                summary_response = await client.get(
                    f"https://{self.language}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                )
                summary_response.raise_for_status()
                summary = summary_response.json()
                content_urls = summary.get("content_urls") or {}
                desktop = content_urls.get("desktop") or {}
                return FactCheckResult(
                    query=query,
                    title=summary.get("title", title),
                    extract=summary.get("extract"),
                    url=desktop.get("page"),
                )
        except Exception as exc:
            return FactCheckResult(query=query, error=f"{type(exc).__name__}: {exc}")
