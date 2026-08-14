from scripts.evaluate_sandbox_requirement import evaluate_policy, parse_codeowners


def event(labels: list[str] | None = None) -> dict:
    return {
        "repository": {"full_name": "chiendz11/face-detector-app"},
        "sender": {"login": "chiendz11"},
        "pull_request": {
            "draft": False,
            "head": {
                "ref": "feature/change",
                "repo": {"full_name": "chiendz11/face-detector-app"},
            },
            "labels": [{"name": name} for name in labels or []],
            "user": {"login": "chiendz11"},
        },
    }


def trusted_label(name: str) -> dict[str, dict]:
    return {name: {"present": True, "actor": "chiendz11", "trusted": True}}


def test_regular_application_change_stays_fast() -> None:
    report = evaluate_policy(event(), ["backend/app/services/recognition_service.py"])

    assert report["decision"] == "pass"
    assert report["classification"] == "fast"


def test_database_migration_requires_validated_sandbox() -> None:
    report = evaluate_policy(event(), ["backend/alembic/versions/0003_change.py"])

    assert report["decision"] == "fail"
    assert report["requiresSandboxValidation"] is True


def test_trusted_sandbox_validation_satisfies_critical_gate() -> None:
    report = evaluate_policy(
        event(["sandbox-validated"]),
        ["backend/alembic/versions/0003_change.py"],
        label_trust=trusted_label("sandbox-validated"),
    )

    assert report["decision"] == "pass"
    assert report["sandboxValidatedTrusted"] is True


def test_trusted_owner_waiver_is_explicit() -> None:
    report = evaluate_policy(
        event(["skip-sandbox-approved"]),
        [".github/workflows/ci.yml"],
        label_trust=trusted_label("skip-sandbox-approved"),
    )

    assert report["decision"] == "pass"
    assert report["skipSandboxTrusted"] is True


def test_team_codeowners_are_not_used_for_solo_self_approval(tmp_path) -> None:
    codeowners = tmp_path / "CODEOWNERS"
    codeowners.write_text("* @org/team\n/backend/ @chiendz11\n", encoding="utf-8")

    parsed = parse_codeowners(codeowners)

    assert parsed == {"/backend/": ["chiendz11"]}
