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
