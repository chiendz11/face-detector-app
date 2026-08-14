from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return document


def test_ci_exposes_one_stable_gateway() -> None:
    workflow = load_yaml(REPO_ROOT / ".github/workflows/ci.yml")

    assert "pull_request" in workflow["on"]
    assert "gateway" in workflow["jobs"]
    assert "verify-app" in workflow["jobs"]


def test_sandbox_dispatch_is_trusted_and_has_no_aws_permission() -> None:
    workflow = load_yaml(REPO_ROOT / ".github/workflows/sandbox-dispatch.yml")
    permissions = workflow["permissions"]

    assert "pull_request_target" in workflow["on"]
    assert "id-token" not in permissions
    assert permissions == {"contents": "read"}


def test_sandbox_image_build_is_isolated_from_registry_credentials() -> None:
    workflow = load_yaml(REPO_ROOT / ".github/workflows/sandbox-image-publish.yml")
    build_job = workflow["jobs"]["build-untrusted-source"]
    publish_job = workflow["jobs"]["publish"]

    assert build_job["permissions"] == {"contents": "read"}
    assert "packages" not in build_job["permissions"]
    assert publish_job["permissions"]["packages"] == "write"
    assert publish_job["needs"] == "build-untrusted-source"


def test_app_release_dispatches_immutable_metadata_to_gitops() -> None:
    text = (REPO_ROOT / ".github/workflows/app-release.yml").read_text(encoding="utf-8")

    assert "promote-staging-v1" in text
    assert "published_images" in text
    assert "GITOPS_DISPATCH_APP_PRIVATE_KEY" in text


def test_repository_contains_no_terraform_or_argocd_desired_state() -> None:
    assert not (REPO_ROOT / "terraform").exists()
    assert not (REPO_ROOT / "deploy" / "argocd").exists()
    assert not (REPO_ROOT / "deploy" / "helm").exists()
