import json
import re

import pytest
import yaml
from support import Render


def test_cloudflare_infrastructure_is_component_owned(render: Render) -> None:
    astro = render(
        "AstroCloudflare",
        {"frontend_variant": "astro", "cloudflare_project_id": "site"},
    )
    hono = render(
        "HonoCloudflare",
        {
            "components": ["backend"],
            "backend_variants": ["hono"],
            "cloudflare_project_id": "api",
        },
    )

    for environment in ("staging", "production"):
        astro_root = (
            astro / "frontend" / "infrastructure" / "environments" / environment
        )
        hono_root = (
            hono / "backend" / "hono" / "infrastructure" / "environments" / environment
        )
        assert 'backend "s3" {}' in (astro_root / "main.tf").read_text()
        assert 'backend "s3" {}' in (hono_root / "main.tf").read_text()
        assert f"site-astro-{environment}" in (astro_root / "main.tf").read_text()
        assert f"api-hono-{environment}" in (hono_root / "main.tf").read_text()

    astro_package = json.loads((astro / "frontend" / "package.json").read_text())
    hono_package = json.loads((hono / "backend" / "hono" / "package.json").read_text())
    assert (
        astro_package["devDependencies"]["wrangler"]
        == hono_package["devDependencies"]["wrangler"]
    )
    assert "versions upload --env staging" in hono_package["scripts"]["release:staging"]
    devbox_packages = json.loads((astro / "devbox.json").read_text())["packages"]
    opentofu_version = next(
        package.partition("@")[2]
        for package in devbox_packages
        if package.startswith("opentofu@")
    )
    terraform_versions: set[str] = set()
    provider_versions: set[str] = set()
    for rendered_project in (astro, hono):
        for path in rendered_project.rglob("*.tf"):
            text = path.read_text()
            terraform_versions.update(
                re.findall(r'required_version = "= ([^"]+)"', text)
            )
            provider_versions.update(
                re.findall(r'^\s+version = "= ([^"]+)"', text, re.MULTILINE)
            )
    assert terraform_versions == {opentofu_version}
    assert len(provider_versions) == 1
    assert 'output: "static"' in (astro / "frontend" / "astro.config.mjs").read_text()
    assert not (astro / "backend").exists()
    assert not (hono / "frontend").exists()


def test_cloudflare_workflow_is_explicit_and_environment_scoped(render: Render) -> None:
    project = render(
        "CloudflareWorkflow",
        {
            "frontend_variant": "astro",
            "components": ["frontend", "backend"],
            "backend_variants": ["hono"],
            "cloudflare_project_id": "application",
        },
    )
    workflow = (project / ".github" / "workflows" / "cloudflare-deploy.yml").read_text()
    workflow_data = yaml.safe_load(workflow)
    job = workflow_data["jobs"]["deploy"]
    steps = {step["name"]: step for step in job["steps"]}

    assert "pull_request:" not in workflow
    assert "contents: read" in workflow
    assert "environment: ${{ startsWith" in workflow
    assert "R2_ACCESS_KEY_ID" in workflow
    assert "R2_SECRET_ACCESS_KEY" in workflow
    assert "tofu -chdir=backend/hono/infrastructure" in workflow
    assert "tofu -chdir=frontend/infrastructure" in workflow
    assert workflow.index("apply -auto-approve") < workflow.index("Release Hono Worker")
    assert "devbox run build" in workflow
    assert job["env"].keys() == {"DEPLOYMENT_ENV"}
    assert re.fullmatch(
        r"actions/checkout@[0-9a-f]{40}",
        steps["Check out repository"]["uses"],
    )
    assert re.fullmatch(
        r"jetify-com/devbox-install-action@[0-9a-f]{40}",
        steps["Install Devbox"]["uses"],
    )
    assert "env" not in steps["Initialize project"]
    assert "env" not in steps["Build project artifacts"]
    assert steps["Apply Hono infrastructure"]["env"].keys() >= {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "R2_STATE_BUCKET",
    }
    assert steps["Provision Hono infrastructure"]["env"].keys() == {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "CLOUDFLARE_API_TOKEN",
        "TF_VAR_cloudflare_account_id",
    }
    assert "key=hono.tfstate" in steps["Apply Hono infrastructure"]["run"]
    assert "key=astro.tfstate" in steps["Apply Astro infrastructure"]["run"]


@pytest.mark.parametrize(
    ("project_name", "expected_id"),
    [
        ("Legacy_App!", "legacy-app"),
        ("Über Project", "ber-project"),
        ("项目", "project"),
        ("a" * 60, "a" * 46),
    ],
)
def test_cloudflare_default_identifier_is_safe(
    render: Render, project_name: str, expected_id: str
) -> None:
    project = render(project_name, {"frontend_variant": "astro"})
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert answers["cloudflare_project_id"] == expected_id


def test_non_cloudflare_components_omit_deployment_residue(render: Render) -> None:
    project = render(
        "FastAPIOnly",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )

    assert not (project / ".github" / "workflows" / "cloudflare-deploy.yml").exists()
    assert "opentofu" not in (project / "devbox.json").read_text()
    assert "OpenTofu" not in (project / ".gitignore").read_text()
    assert "cloudflare_project_id" not in yaml.safe_load(
        (project / ".copier-answers.yml").read_text()
    )
