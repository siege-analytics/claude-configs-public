#!/usr/bin/env python3
"""Hostile billing diagnostic fixtures. Never provide a bypass success path."""
import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("billing", ROOT / "scripts/ci/verify-billing-block.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHA = "a" * 40
BILLING = M.BILLING


def fixture():
    pr = {"headRefOid": SHA, "baseRefName": "develop", "reviewDecision": "APPROVED"}
    run = {"id": 5, "name": "required", "app": {"id": 100}, "status": "completed", "conclusion": "failure", "started_at": "2026-10-14T10:00:00Z", "completed_at": "2026-10-14T10:00:02Z", "output": {"summary": BILLING}}
    return pr, {"check_runs": [run], "total_count": 1}, {"contexts": [], "checks": [{"context": "required", "app_id": 100}]}, {"sha": SHA, "statuses": []}, {5: []}, dict(pr)


def main():
    baseline = fixture()
    assert M.evaluate(*baseline) == []  # Bare full documented message, evidence not authorization.
    assert BILLING == M.BILLING_REASON + " Please check the 'Billing & plans' section in your settings."
    for prefix in M.BILLING_PREFIXES:
        assert M.billing_message(prefix + BILLING)
    realistic = copy.deepcopy(fixture())
    realistic[1]["check_runs"][0]["output"] = {"summary": None, "title": None, "text": None}
    realistic[4][5] = [{"message": f"Error: {BILLING}", "title": None, "raw_details": None}]
    assert M.evaluate(*realistic) == []  # Real GitHub annotation prefix + null optional fields.
    negatives = []
    def case(name, change):
        args = copy.deepcopy(fixture())
        change(args)
        gaps = M.evaluate(*args)
        assert gaps, (name, gaps)
        negatives.append(name)
    case("missing required check", lambda a: a[2]["checks"].append({"context": "absent", "app_id": 100}))
    case("incomplete pagination", lambda a: a[1].update(total_count=2))
    case("no checks", lambda a: a[1].update(check_runs=[]))
    case("changed head", lambda a: a[5].update(headRefOid="b"*40))
    case("reviewer block", lambda a: a[0].update(reviewDecision="CHANGES_REQUESTED"))
    case("nonbilling failure", lambda a: a[1]["check_runs"][0]["output"].update(summary="tests failed"))
    case("partial billing reason alone", lambda a: a[1]["check_runs"][0]["output"].update(summary=M.BILLING_REASON))
    case("mixed billing and test failure", lambda a: a[1]["check_runs"][0]["output"].update(summary=BILLING + " tests failed"))
    case("prefixed billing with test failure", lambda a: a[1]["check_runs"][0]["output"].update(summary=f"Error: {BILLING} tests failed"))
    case("declared prefix with mixed suffix", lambda a: a[1]["check_runs"][0]["output"].update(summary=f"GitHub Actions: {BILLING} tests failed"))
    case("malformed output field", lambda a: a[1]["check_runs"][0]["output"].update(text={"unexpected": True}))
    case("billing summary with test failure annotation", lambda a: a[4][5].append({"message": "tests failed"}))
    case("billing annotation with conflicting title", lambda a: a[4][5].append({"message": BILLING, "title": "tests failed"}))
    case("billing annotation with conflicting details", lambda a: a[4][5].append({"message": BILLING, "raw_details": "tests failed"}))
    case("malformed annotations", lambda a: a[4].update({5: ["not an annotation"]}))
    case("cancelled with billing text", lambda a: a[1]["check_runs"][0].update(conclusion="cancelled"))
    case("negative duration", lambda a: a[1]["check_runs"][0].update(completed_at="2026-10-14T09:59:59Z"))
    case("malformed duration", lambda a: a[1]["check_runs"][0].update(started_at="not a date"))
    case("pending required check", lambda a: a[1]["check_runs"][0].update(status="queued", conclusion=None))
    case("wrong required app", lambda a: a[2]["checks"][0].update(app_id=999))
    case("status failure", lambda a: a[3].update(statuses=[{"context": "legacy", "state": "failure"}]))
    case("missing protection", lambda a: a[2].clear())
    assert M.main(["bad/owner", "enterprise", "1"]) == 1
    assert M.main(["electinfo", "enterprise", "-1"]) == 1
    # The generic entry point has no project host/path policy or approval/grant
    # input: neither can authorize a merge. Scoped-policy negatives require a
    # separate future project implementation; do not claim they run here.
    # Even billing-looking evidence MUST return 1, for any owner/repo identity.
    for owner, repo in (("electinfo", "enterprise"), ("wrong", "repo")):
        pr, runs, required, statuses, annotations, latest = copy.deepcopy(realistic)
        replies = [pr, [runs], required, statuses, latest]
        def fake_gh(*args):
            if "annotations" in " ".join(args):
                return [annotations[5]]
            return replies.pop(0)
        with patch.object(M, "gh", side_effect=fake_gh):
            assert M.main([owner, repo, "123"]) == 1 and not replies
    source = (ROOT / "skills/ci-billing-failure-merge/SKILL.md").read_text()
    assert "gh pr merge --admin" in source and "Do not issue" in source
    assert "standing" in source and "out-of-scope" in source and "specific PR" in source
    implementation = (ROOT / "scripts/ci/verify-billing-block.py").read_text()
    assert '"gh", *args' in implementation
    assert "gh pr merge" not in implementation
    assert "return 1" in implementation and "return 0" not in implementation
    print(f"billing diagnostic: {len(negatives)} evidence negatives + two repo identities never authorize PASS; approval/grant/path policies absent by design")


if __name__ == "__main__":
    main()
