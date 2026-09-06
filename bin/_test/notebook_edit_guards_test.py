#!/usr/bin/env python3
"""The write guards must see NotebookEdit's payload, not just Write's (#703).

Wiring a guard for the NotebookEdit matcher closes nothing on its own. Claude
Code sends the target as tool_input.notebook_path for NotebookEdit and as
tool_input.file_path for Write and Edit, and all three guards read only the
latter until this change. A settings file that wires them for NotebookEdit
without this fix reports a guard that cannot fire, which is worse than the
open gap it replaces.

Each case asserts both shapes against the same guard and the same target, so a
guard that stops blocking altogether fails here rather than passing by symmetry.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FAILURES = []


def run_guard(guard: str, payload: dict) -> int:
    proc = subprocess.run(
        [str(REPO_ROOT / "hooks" / "write" / guard)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode


def check(name, condition, detail=""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}\n         {detail}")


def both_shapes(guard: str, target: str, cwd: str | None) -> tuple[int, int]:
    codes = []
    for key, tool in (("file_path", "Write"), ("notebook_path", "NotebookEdit")):
        payload = {"tool_name": tool, "tool_input": {key: target, "content": "x"}}
        if cwd:
            payload["cwd"] = cwd
        codes.append(run_guard(guard, payload))
    return tuple(codes)


def make_repo_on_protected_branch(tmp: str) -> str:
    repo = Path(tmp) / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e.test",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e.test"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "f.txt").write_text("seed\n")
    subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "--no-verify", "-m", "seed"],
        check=True,
        env={**dict(**env), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    return str(repo)


def main():
    # write-guard blocks on the pydantic schema rule, which needs no git state.
    blocked, notebook = both_shapes("write-guard.sh", "parsers/schemas/models.py", None)
    check("write-guard still blocks the Write shape", blocked == 2, f"exit {blocked}")
    check("write-guard blocks the NotebookEdit shape", notebook == 2, f"exit {notebook}")

    # branch-guard needs a real repo on a protected branch to have anything to say.
    with tempfile.TemporaryDirectory() as tmp:
        repo = make_repo_on_protected_branch(tmp)
        target = str(Path(repo) / "f.txt")
        blocked, notebook = both_shapes("branch-guard.sh", target, repo)
        check("branch-guard still blocks the Write shape", blocked == 2, f"exit {blocked}")
        check("branch-guard blocks the NotebookEdit shape", notebook == 2, f"exit {notebook}")

    # All three guards must read the key, including the one whose block
    # conditions are content-dependent and not exercised above.
    for guard in ("write-guard.sh", "branch-guard.sh", "ticket-propagation-guard.sh"):
        source = (REPO_ROOT / "hooks" / "write" / guard).read_text()
        check(
            f"{guard} reads tool_input.notebook_path",
            "tool_input.notebook_path" in source,
            "extractor chain does not list notebook_path",
        )

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        sys.exit(1)
    print("All NotebookEdit guard fixtures passed.")


if __name__ == "__main__":
    main()
