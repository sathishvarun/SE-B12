"""Health check and app-level wiring."""

from fastapi.testclient import TestClient

from app.services import scheduler


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unknown_route_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/nope").status_code == 404


def test_lifespan_starts_and_stops_scheduler(monkeypatch, client: TestClient) -> None:
    """Using the client as a context manager runs the lifespan hooks (patched to no-ops)."""
    calls: list[str] = []
    monkeypatch.setattr("app.main.start_scheduler", lambda: calls.append("start"))
    monkeypatch.setattr("app.main.shutdown_scheduler", lambda: calls.append("stop"))
    with client as c:
        assert c.get("/health").status_code == 200
    assert calls == ["start", "stop"]


def test_scheduler_start_is_idempotent_and_shutdown_clears() -> None:
    scheduler.start_scheduler()
    try:
        first = scheduler._scheduler
        assert first is not None and first.running
        assert first.get_job("task_reminders") is not None
        scheduler.start_scheduler()  # second call is a no-op
        assert scheduler._scheduler is first
    finally:
        scheduler.shutdown_scheduler()
    assert scheduler._scheduler is None
    scheduler.shutdown_scheduler()  # safe when not running
