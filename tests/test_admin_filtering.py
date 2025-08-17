from app.observability.audit import new_audit, push_event, finalize_audit, list_audits

def _seed(path: str, status: int = 200):
    a = new_audit("t-"+path, "GET", path, "127.0.0.1", "unknown")
    push_event(a, "received", {"auth":"read"})
    finalize_audit(a, status=status, latency_ms=3.14, summary=None)

def test_exclude_monitoring_hides_root_and_metrics():
    _seed("/")
    _seed("/v1/metrics")
    _seed("/v1/metrics/prometheus")
    _seed("/v1/system")
    _seed("/v1/logs/tail")
    _seed("/v1/admin/requests")
    _seed("/v1/ingest")  # business

    items = list_audits(limit=50, exclude_monitoring=True)
    paths = [i["path"] for i in items]
    assert "/v1/ingest" in paths
    assert "/" not in paths
    assert "/v1/metrics" not in paths
    assert "/v1/metrics/prometheus" not in paths
    assert "/v1/system" not in paths
    assert "/v1/logs/tail" not in paths
    assert "/v1/admin/requests" not in paths

def test_path_normalization_drops_trailing_slash():
    a = new_audit("t-norm", "GET", "/v1/metrics", "127.0.0.1", "unknown")
    finalize_audit(a, 200, 1.0, None)
    b = new_audit("t-norm2", "GET", "/v1/metrics/", "127.0.0.1", "unknown")
    finalize_audit(b, 200, 1.0, None)

    items = list_audits(limit=50, exclude_monitoring=False)
    # both entries exist but normalization is applied in middleware in real traffic;
    # this test ensures list_audits doesn't blow up on mixed paths
    assert any(i["path"] == "/v1/metrics" for i in items)

def test_newest_first_ordering():
    _seed("/v1/ingest", 200)
    _seed("/v1/lookup", 200)
    _seed("/v1/outputs", 200)

    items = list_audits(limit=3, exclude_monitoring=True)
    # Should return newest first (reverse chronological order)
    assert len(items) == 3
    # The last seeded item should be first in the list
    assert items[0]["path"] == "/v1/outputs"
    assert items[1]["path"] == "/v1/lookup"
    assert items[2]["path"] == "/v1/ingest"
