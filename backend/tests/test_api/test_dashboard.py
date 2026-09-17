import pytest

from app.api.deps import get_db
from app.models.evaluation_log import EvaluationLog
from app.models.request_log import RequestLog


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalars(self._items)


class FakeSession:
    def __init__(self, request_logs, evaluation_logs):
        self._queue = [request_logs, evaluation_logs]

    async def execute(self, query):
        return FakeResult(self._queue.pop(0))


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_aggregates_real_models(client):
    from app.main import app

    request_logs = [
        RequestLog(
            tokens=100,
            cost_usd=0.01,
            latency_ms=500.0,
            task_type="code",
            complexity="low",
            code_verifications=[{"passed": True}],
            calculation_verifications=[],
            fact_search_results=[],
        )
    ]
    evaluation_logs = [
        EvaluationLog(
            single_tokens=10,
            single_cost_usd=0.001,
            single_latency_ms=100.0,
            multi_tokens=40,
            multi_cost_usd=0.004,
            multi_latency_ms=400.0,
            judge_verdict="multi",
        )
    ]

    async def _fake_db():
        yield FakeSession(request_logs, evaluation_logs)

    app.dependency_overrides[get_db] = _fake_db
    response = await client.get("/api/dashboard/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 1
    assert data["total_tokens"] == 100
    assert data["by_task_type"][0]["task_type"] == "code"
    assert data["verification"]["code_verification_pass_rate"] == 1.0
    assert data["evaluation"]["multi_wins"] == 1


@pytest.mark.asyncio
async def test_dashboard_stats_endpoint_handles_empty_tables(client):
    from app.main import app

    async def _fake_db():
        yield FakeSession([], [])

    app.dependency_overrides[get_db] = _fake_db
    response = await client.get("/api/dashboard/stats")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 0
    assert data["total_cost_estimated_usd"] is None
    assert data["by_task_type"] == []
