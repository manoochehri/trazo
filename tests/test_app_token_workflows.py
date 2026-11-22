"""#252: workflows mint GitHub App tokens from the main-only environment `trazo-apps`.

GitHub matches an environment's deployment branch rule against the run's GITHUB_REF
(https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
A `pull_request` run uses refs/pull/N/merge, which a main-only rule does not match, and the owner
decided not to weaken that rule. So only jobs of workflows that run from the default branch
(schedule, workflow_dispatch) may name the environment; review.yml (pull_request) must not.
"""

import re
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
ACTION = "actions/create-github-app-token@f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc"  # v3.4.0
KEY = re.compile(r"secrets\.(BUILDER|REVIEWER)_APP_PRIVATE_KEY")


def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text())


def uses(step, prefix):
    return str(step.get("uses", "")).startswith(prefix)


def mints(job):
    return [
        s
        for s in job.get("steps", [])
        if str(s.get("uses", "")).startswith("actions/create-github-app-token@")
    ]


def test_token_action_pinned_to_verified_commit():
    for path in WORKFLOWS.glob("*.yml"):
        for ref in re.findall(r"uses:\s*(actions/create-github-app-token@\S+)", path.read_text()):
            assert ref == ACTION, f"{path.name}: {ref}"


def test_publish_mints_builder_token_and_uses_it():
    publish = load("drive.yml")["jobs"]["publish"]
    steps = mints(publish)
    assert len(steps) == 1
    w = steps[0]["with"]
    assert "BUILDER_APP_ID" in str(w) and "BUILDER_APP_PRIVATE_KEY" in str(w)
    assert "REVIEWER" not in str(w)
    gh_tokens = [s["env"]["GH_TOKEN"] for s in publish["steps"] if "GH_TOKEN" in s.get("env", {})]
    assert gh_tokens and all(".outputs.token" in t for t in gh_tokens)
    # checkout keeps no credential (persist-credentials false); the push passes the token
    push = [ln for ln in (WORKFLOWS / "drive.yml").read_text().splitlines() if "git push" in ln]
    assert len(push) == 1 and "x-access-token:${GH_TOKEN}@" in push[0]


def test_every_token_minting_job_declares_the_environment():
    for path in WORKFLOWS.glob("*.yml"):
        for name, job in load(path.name)["jobs"].items():
            if mints(job) or KEY.search(yaml.safe_dump(job)):
                env = job.get("environment")
                env = env.get("name") if isinstance(env, dict) else env
                assert env == "trazo-apps", f"{path.name}:{name}"


def test_keys_only_read_by_the_minting_step():
    for path in WORKFLOWS.glob("*.yml"):
        for name, job in load(path.name)["jobs"].items():
            for step in job.get("steps", []):
                if KEY.search(yaml.safe_dump(step)):
                    assert str(step.get("uses", "")).startswith(
                        "actions/create-github-app-token@"
                    ), f"{path.name}:{name}"
        assert "secrets: inherit" not in path.read_text()


def test_agent_job_never_holds_an_app_token():
    work = load("drive.yml")["jobs"]["work"]
    assert not mints(work)
    assert "environment" not in work
    assert "APP_PRIVATE_KEY" not in yaml.safe_dump(work)


def test_review_path_never_exposes_the_key_to_pr_controlled_code():
    wf = load("review.yml")
    triggers = wf.get("on") or wf.get(True)
    assert "pull_request" in triggers
    text = (WORKFLOWS / "review.yml").read_text()
    assert "APP_PRIVATE_KEY" not in text
    assert "create-github-app-token" not in text
    assert not any("environment" in job for job in wf["jobs"].values())


def test_report_mints_the_reviewer_token_from_the_main_only_environment():
    # workflow_run runs the default branch's file with the default branch as GITHUB_REF (#291).
    wf = load("report.yml")
    job = wf["jobs"]["report"]
    assert "workflow_run" in (wf.get("on") or wf.get(True))
    assert job["environment"] == "trazo-apps"
    assert len(mints(job)) == 1
    assert "REVIEWER_APP_PRIVATE_KEY" in yaml.safe_dump(mints(job)[0])


def test_minted_token_is_narrow_and_scoped_to_this_repo():
    w = mints(load("drive.yml")["jobs"]["publish"])[0]["with"]
    assert w.get("repositories") == "${{ github.event.repository.name }}"
    perms = {k for k in w if k.startswith("permission-")}
    assert perms == {"permission-contents", "permission-pull-requests", "permission-issues"}
    assert all(w[k] == "write" for k in perms)


def test_app_token_checkout_does_not_persist_credentials():
    publish = load("drive.yml")["jobs"]["publish"]
    checkout = [s for s in publish["steps"] if uses(s, "actions/checkout")][0]
    assert checkout["with"].get("persist-credentials") is False
    # the push then needs the token passed explicitly, not read from .git/config
    text = (WORKFLOWS / "drive.yml").read_text()
    assert "git push" in text and "x-access-token" in text


def test_host_copy_of_drive_is_in_sync():
    root = WORKFLOWS.parents[1]
    host = root / "src" / "harness" / ".github" / "workflows" / "drive.yml"
    assert host.read_bytes() == (WORKFLOWS / "drive.yml").read_bytes()
