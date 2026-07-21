from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_certification_evidence_portfolio_covers_requested_additions() -> None:
    evidence = ROOT / "docs" / "evidence_portfolio.md"
    assert (
        evidence.exists()
    ), "docs/evidence_portfolio.md must map the requested additions to proofs"
    text = evidence.read_text(encoding="utf-8").lower()

    required_markers = [
        "rgpd",
        "pseudonymisation",
        "bronze",
        "silver",
        "gold",
        "api",
        "cli",
        "docker",
        "ci",
        "psi",
        "model card",
        "threat model",
        "c1",
        "c9",
    ]
    for marker in required_markers:
        assert marker in text


def test_ci_builds_docker_image_in_addition_to_quality_checks() -> None:
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8").lower()

    assert "docker" in text
    assert "docker/build-push-action" in text or "docker build" in text


def test_run_profile_provisions_dashboard_and_scheduler() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8").lower()
    dashboard = ROOT / "monitoring/grafana/provisioning/dashboards/json/decrochage-run.json"
    provider = ROOT / "monitoring/grafana/provisioning/dashboards/provider.yml"

    assert "scheduler:" in compose
    assert '["decrochage", "schedule"]' in compose
    assert dashboard.exists()
    assert provider.exists()
    assert "http_request_duration_seconds_bucket" in dashboard.read_text(encoding="utf-8")


def test_evidence_portfolio_cites_operational_proofs() -> None:
    text = (ROOT / "docs/evidence_portfolio.md").read_text(encoding="utf-8").lower()

    for marker in ["mlflow", "apscheduler", "dashboard", "x-request-id", "limitation de débit"]:
        assert marker in text
