#!/usr/bin/env python3
"""Fixtures for compare_settings_to_snippet (bin/validate-hooks.py, #703).

Each fixture asserts on the returned problem strings and not only on their
count, because a comparison that fails for an unrelated reason produces the
same count as one that fails for the right reason. The pre-mortem's T3 is the
reason: MIN_HOOK_COUNT looked like a guard and passed at 24 wired hooks while
5 were missing, so replacing one vacuous assertion with another is the default
outcome here.
"""

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

spec = importlib.util.spec_from_file_location(
    "validate_hooks", REPO_ROOT / "bin" / "validate-hooks.py"
)
validate_hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_hooks)

compare = validate_hooks.compare_settings_to_snippet
extract_triples = validate_hooks.extract_hook_triples

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}\n         {detail}")


def write(tmpdir, filename, data):
    path = Path(tmpdir) / filename
    path.write_text(json.dumps(data, indent=2))
    return path


def main():
    snippet_path = REPO_ROOT / "hooks" / "settings-snippet.json"
    settings_path = REPO_ROOT / ".claude" / "settings.json"
    snippet = json.loads(snippet_path.read_text())
    settings = json.loads(settings_path.read_text())

    # The live tree must agree, or every fixture below is comparing against a
    # baseline that is already broken.
    check(
        "live settings and snippet agree",
        compare(settings_path, snippet_path) == [],
        compare(settings_path, snippet_path),
    )

    # The set size is asserted over triples and not over hooks, so an empty-set
    # comparison cannot masquerade as agreement, and so the two granularities
    # stay visibly distinct (pre-mortem M3).
    triples = extract_triples(snippet)
    paths = {t[2] for t in triples}
    check(
        "snippet has 38 triples over 29 distinct hooks",
        (len(triples), len(paths)) == (38, 29),
        f"got {len(triples)} triples over {len(paths)} hooks",
    )

    with tempfile.TemporaryDirectory() as tmp:
        # Fixture 1: delete one hook entirely. The validator must name it.
        one_hook_gone = copy.deepcopy(settings)
        target = "hooks/git/vergil-quote.sh"
        for groups in one_hook_gone["hooks"].values():
            for group in groups:
                group["hooks"] = [
                    h for h in group.get("hooks", []) if h.get("command") != target
                ]
        problems = compare(write(tmp, "s1.json", one_hook_gone), snippet_path)
        check(
            "deleting one hook is reported and the hook is named",
            len(problems) == 1 and target in problems[0],
            problems,
        )

        # Fixture 2: delete a single matcher from a hook that stays wired on its
        # others. This is the live NotebookEdit case and the one a path-keyed
        # comparison passes, so it is the fixture that distinguishes the two
        # comparison keys.
        one_matcher_gone = copy.deepcopy(settings)
        victim = "hooks/write/write-guard.sh"
        for groups in one_matcher_gone["hooks"].values():
            for group in groups:
                if group.get("matcher") == "NotebookEdit":
                    group["hooks"] = [
                        h for h in group.get("hooks", []) if h.get("command") != victim
                    ]
        s2 = write(tmp, "s2.json", one_matcher_gone)
        problems = compare(s2, snippet_path)
        still_wired = {
            t[1] for t in extract_triples(one_matcher_gone) if t[2] == victim
        }
        check(
            "deleting one matcher is reported and the triple is named",
            len(problems) == 1
            and victim in problems[0]
            and "NotebookEdit" in problems[0],
            problems,
        )
        check(
            "the victim hook is still wired on its other matchers",
            still_wired == {"Write", "Edit", "MultiEdit"},
            still_wired,
        )
        check(
            "a path-keyed comparison passes this fixture, which is why the key is a triple",
            {t[2] for t in extract_triples(one_matcher_gone)}
            == {t[2] for t in extract_triples(snippet)},
            "path sets differ, so the fixture does not isolate the comparison key",
        )

        # Fixture 3: fail closed on an empty side rather than reporting agreement.
        empty = write(tmp, "empty.json", {"hooks": {}})
        problems = compare(empty, empty)
        check(
            "two empty files are not reported as agreement",
            problems and all("zero hook wirings" in p for p in problems),
            problems,
        )

        # Fixture 4: fail closed on an unreadable file.
        missing = Path(tmp) / "does-not-exist.json"
        problems = compare(missing, snippet_path)
        check(
            "a missing settings file is reported, not skipped",
            len(problems) == 1 and "Cannot read settings" in problems[0],
            problems,
        )

        # Fixture 5: an entry in settings that the snippet does not have is
        # drift in the other direction and must not be silently tolerated.
        extra = copy.deepcopy(settings)
        extra["hooks"]["PreToolUse"].append(
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "hooks/invented.sh"}]}
        )
        problems = compare(write(tmp, "s5.json", extra), snippet_path)
        check(
            "an entry absent from the snippet is reported",
            len(problems) == 1 and "hooks/invented.sh" in problems[0],
            problems,
        )

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        sys.exit(1)
    print("All settings-drift fixtures passed.")


if __name__ == "__main__":
    main()
