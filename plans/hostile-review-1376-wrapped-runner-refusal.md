---
propagation-deferred: published with the PR that closes #1376; the PR body summarizes this record and the hub relays it
---

# Independent review record: #1376 opaque-runner refusal through command wrappers

Reviewers: read-only subagents, given the code, the issue and probe tools, not
the author's conclusions. Pass 1 was a first reviewer. Passes 2-4 (re-review,
fix verification, targeted confirm of the final delta, and a confirm of the
python floor narrowing made after merging develop 0b6c13ce) were a second
reviewer, fresh to pass 1. Passes 5-6 (a targeted confirm of the python
floor narrowing on the tree merged with develop dbd78db3, and a confirm of
the F1/F3 delta made in response to it) were a third reviewer, fresh to
passes 1-4. Pass 7 (a targeted confirm after the fix was replayed onto
develop ec4d1645, whose task_actions.py had changed) was a fourth reviewer,
fresh to passes 1-6. All reviewers were the same model family as the author
(same-family independence, not cross-provider). The reports below are
verbatim except that non-ASCII punctuation is normalized to ASCII; author
notes are marked as such. Paths such as WT/debug/... refer to the author's
ignored scratch folder and are not committed.

Final verdict: CLEAN (task_actions.py blob f830db8d, the committed code: the
fix replayed onto develop ec4d1645, hunk-identical to the reviewed blob
2d1df348). Earlier verdicts: APPROVE at aa4d021e, APPROVE at 0f746e72 after
the python floor narrowing, CLEAN at 2d1df348 (passes 5-6). Pass 5 found no regression at 0f746e72 and three gaps
that develop also admits; F1 and F3 were fixed with red rows (blob 2d1df348),
and F2 is a residual. Remaining class (iii) findings, which develop also
admits, are documented as residuals in the PR.

## Pass 1: first review

### Hostile review: #1376 wrapped opaque-runner refusal

**Verdict: CHANGES REQUESTED.** The change is a real improvement: 310 rows that fail on develop now pass, and no crash showed up across 30 degenerate argv. But the loop still admits wrapped runners in three ways (findings 1-3). It trusts `_wrapped_command` even when that function guesses where the command starts.

Probe: `python3 -I <wt>/debug/probe/probe.py <LIB> <wt>/debug/review/casesN.txt <wt>`. D = develop, P = patched.

## Verified (probe run)

1. **P1 bypass: xargs supplies the command.** `supplied` is only checked for Python. Admitted on both D and P:
   - `echo 'bash -c true' | xargs env`
   - `xargs nohup`
   - `printf 'sh -c true' | xargs timeout 5`
   - `xargs sudo`
   - `xargs command`
   - `xargs -I X X -c 'touch /tmp/x'`
   - `echo sh | xargs -J % % -c true`

   Fix (in the loop, after `inner` is computed):
   ```python
   if supplied and not inner:
       raise UnknownShape(f'xargs supplies the command {name} runs; {_OPAQUE}')
   ```
   Also refuse when the command word contains xargs' `-I`/`-J`/`-i`/`--replace` string.

2. **P1 bypass: long-option abbreviations (getopt_long).** These were admitted on both D and P:
   - `timeout --sig KILL 5 bash -c 'touch /tmp/x'` (`KILL` is taken as the command; Homebrew GNU timeout is installed)
   - `timeout --k 1 5 sh`
   - `nice --adj 5 bash -c ...`
   - `xargs --max-a 1 bash -c ...`
   - `stdbuf --out L sh`
   - `nohup env --split='bash -c true'` and `nohup env --split-str='sh -c true'`
   - `flock /tmp/l --comm='touch /tmp/x'` (the full `--command=` spelling is refused)
   - `sudo --sh ls`, `sudo --sh`, `sudo --log`, `sudo --shel` (only the exact `--shell`/`--login` are refused)

   Fix: refuse any `--opt` before the wrapped command that is not an exact known long option but is a prefix of one of that wrapper's modelled long options (values, strings, stops, sudo `--shell`/`--login`, watch `--exec`). For sudo, match `opt` against the prefixes `--sh...`/`--lo...`.

3. **P1 bypass on this host: value options that are not modelled.** The macOS `/usr/bin/env` man page lists `-P altpath`, and BSD `/usr/bin/xargs` lists `-J`, `-R` and `-S`. Admitted on both D and P:
   - `nohup env -P /usr/bin bash -c 'touch /tmp/x'`
   - `timeout 5 env -S '-P /usr/bin bash -c true'`
   - `xargs -J % bash -c ...`
   - `xargs -R 1 bash -c ...`
   - `xargs -S 255 bash -c ...`
   - `doas -a style bash -c ...`
   - GNU optional-argument options read as taking a separate value: `xargs --replace bash -c ...`, `--eof`, `--max-lines`

   Fix: add env `-P`, xargs `-J`/`-R`/`-S` and doas `-a` to `_WRAPPER_VALUES`. Drop `--replace`, `--eof` and `--max-lines` as separate-value options (accept only `=value`), or refuse them.

4. **P3 over-refusal: Python options read after the script.** `python3 ./tool.py -vc` and `python3 ./tool.py -xc`: D ADMITTED, P REFUSED. `_python_inline_option` scans every word. Fix: stop at the first word that is not an option (or `-`), skip the values of `-W`/`-X`, and stop after `-m`.

5. **P3 over-refusal: sudo letter clusters.** `sudo -usroot ls` and `sudo -Dsrc ls`: D ADMITTED, P REFUSED. Fix: in the cluster loop, stop at the first letter `l` where `'-' + l` is in `_WRAPPER_VALUES['sudo']`.

6. **P3 regressions to accept and document.**
   - `watch ls` and `watch -n 1 git status`: D ADMITTED, P REFUSED. This is justified because watch runs `sh -c`. But it contradicts the "keep current outcome" clause, so state it in the PR.
   - `script -p ./typescript` is refused. On macOS `-p` is playback and runs no shell.
   - `timeout 5 env -uS` is refused.
   - `nohup /usr/bin/python3 -I -c 'print(1)'` is refused (a tightening). The code comment says the read-only Python program behind a wrapper keeps its old outcome. That is false for absolute and versioned spellings, because `_python_read` matches the literal name.

7. **P3: the test is red on develop and green on P, but some rows prove nothing.** I ran a copy of the test against develop (`debug/review/wrapped_opaque_runner_1376_on_develop.py`): 310 failures; on P all 10 tests pass. In the wrapper-by-runner matrix, the 36 `env`, `command` and `exec` rows already pass on develop. They are refused by `_project_execution_wrapper` or by `exec` itself, so they never exercise `refuse_opaque_runner`. Add rows for findings 1-3.

## Suspicions (not reported as defects)

- None of these are refused, bare or wrapped, on either D or P: `ash`, `fish`, `csh`, `tcsh`, `bash5`, `perl -e`, `node -e`, and Python reading code from stdin (`python3 -`, `nohup python3`). The gh merge model already treats `ash` as a shell, so the shell lists disagree.
- macOS env `-S` semantics are BSD, while `_env_split_string` models GNU env.
- Depth bound: `nohup x17 ls` is refused. No crash or IndexError path was found.

## Passes 2-4: fresh re-review, fix verification and targeted confirms

### Re-review: #1376 wrapped opaque-runner refusal (revised patch)

**Verdict: CHANGES REQUESTED.** All seven earlier findings are fixed or documented. Conditions (a), (b) and (c) hold. One new P1 bypass class remains (N1).

**Baseline.** While I was reviewing, `WT/hooks/lib/task_actions.py` was overwritten with the patch: `git diff HEAD` now equals `debug/fix.diff`. So for develop (D) I used `git show HEAD:hooks/lib/task_actions.py`, copied to `debug/rereview/devlib/`. P is `debug/dev/hooks/lib`. Comparison script: `debug/rereview/cmp.py`. Case files: `prior.txt`, `new.txt` and `sub.txt`.

## Conditions
- **(a) Holds.** The four shared tables compare equal, and their source bytes are identical. I compared 4,574,367 non-strict `_wrapped_command` calls (with and without `preserve_shell`) plus `ssh_invocation` calls between D and P (`nonstrict.py`): 0 differences.
- **(b) Holds.** No row is refused on D and admitted on P across all cases (96 tightenings, 0 loosenings). `python3 ./tool.py -vc`, `python3 -m mod -xc`, `python3 -X dev ./tool.py -Ic` and `python3 -W ignore ./tool.py -bc` stay ADMITTED.
- **(c) Holds.** Every earlier P1 probe row is REFUSED on P.
- **Crashes:** 400k random fuzz argv (`fuzz.py`) raised only `UnknownShape`.
- **Tests:** the regression test passes on P (14 OK) and failed on develop (370 failures).

## Earlier findings
| # | Status | Evidence |
|---|---|---|
| 1 xargs supplies command | Fixed | `xargs nohup`, `xargs sudo`, `echo sh \| xargs -J % % -c true` and others: D ADMITTED, P REFUSED |
| 2 long-option abbreviations | Fixed | `timeout --sig`, `nice --adj`, `sudo --sh`/`--shel`/`--log`, `env --split=`: P REFUSED. Only `flock /tmp/l --comm=...` is still ADMITTED; util-linux matches the word after FILE against exactly `-c`/`--command`, so I do not count it as a bypass |
| 3 unmodelled value options | Fixed | env `-P`, xargs `-J/-R/-S`, doas `-a`, `xargs --replace/--eof/--max-lines`: P REFUSED |
| 4 Python options after script | Fixed | `python3 ./tool.py -vc` / `-xc`: P ADMITTED |
| 5 sudo clusters | Fixed | `sudo -usroot ls`, `sudo -Dsrc ls`: P ADMITTED |
| 6 regressions | Accepted as documented | `watch ls` and `script -p` are refused and listed in the self-review. `timeout 5 env -uS` is now ADMITTED (fixed). The code comment about `/usr/bin/python3` is now accurate |
| 7 test rows | Fixed | Rows for findings 1-3 added (test lines 141-169) |

## New findings (verified)

**N1 - P1 bypass.** An xargs replacement string or an env `-S` `${VAR}` in a word the wrapper consumes itself (an option, a value or a positional) can change where the command starts at run time. The patch only checks `command[0]`. Every row below is ADMITTED on both D and P:
- `echo -- | xargs -I X timeout X 5 sh -c 'touch /tmp/x'` (runs `timeout -- 5 sh -c ...`)
- `echo -v | xargs -I X timeout X 1 sh -c 'touch /tmp/x'`; `xargs -iX ...`; `xargs --replace=X ...`
- `echo '5 sh' | xargs -J % timeout % -c 'touch /tmp/x'`. BSD `-J` inserts several words.
- `xargs -J % nice -n % ls` and `xargs -J % sudo -u % ls`. With input `5 sh -c '...'` the first becomes `nice -n 5 sh -c '...' ls`.
- `echo -n | xargs -I X flock X /tmp/l sh -c ...`; `echo -a | xargs -I X taskset X 1 sh -c ...`
- `X=-- nohup env -S 'timeout ${X} 5 sh -c true'`; `nohup env -S 'chrt ${X} 5 sh -c true'`

I confirmed the runtime reshaping with harmless commands. `echo '5 echo' | xargs -J % timeout % rereview-demo-J` printed `rereview-demo-J`, and `echo -- | xargs -I X timeout X 5 echo rereview-demo-I` printed `rereview-demo-I`. In both, the model took `5` or `rereview-demo-J` as the command, but `echo` ran.

**Fix.** In `refuse_opaque_runner`, after the `supplied and not inner` check and before `replace` is updated:
```python
cut = len(command) - len(inner)
head = command[1:cut] if inner and command[cut:] == inner else command[1:]
if any(_ENV_DYNAMIC_WORD in word or replace is not None and replace in word for word in head):
    raise UnknownShape(f'{name} options or operands are supplied at run time; {_OPAQUE}')
```
I applied this to a scratch copy (`debug/rereview/fixlib`). It refuses every N1 row. The only other new refusals are the unboundable shapes `xargs -J % timeout % ls`, `xargs -I X timeout X ls` and `xargs -I X sudo -uX ls`. Ordinary rows such as `xargs --replace=@ cp @ ./a` and `xargs -I X touch ./a/X` are unchanged, and no expected-admitted test row contains a replacement string. Add the N1 rows to the test.

**N2 - P3 over-refusal.** `xargs python3 ./tool.py` and `xargs -n 1 python3 ./tool.py`: D ADMITTED, P REFUSED. Python stops reading options at the script name, so arguments that xargs appends cannot add `-c`. The self-review's reason ("xargs may supply -c") only applies when no script or module is given. Fix: with `supplied`, refuse only when the `_python_inline` option scan reaches the end without finding a script, `-m` or `-`.

**N3 - P3, undocumented outcome changes.** `sudo -s ls`, `sudo -i ls`, `sudo -a type ls` and `sudo -c class ls`: D ADMITTED, P REFUSED. These fail closed, which is defensible, but the self-review does not list them. Add them to the PR's outcome-change list.

## Suspicions (not verified on Linux)
- `script ./out -qc 'touch /tmp/x'`, `script ./out -q -c ...` and `script ./out --comm=...` are ADMITTED on D and P. If util-linux `script` reorders options it finds after FILE (the model already handles `script FILE -c CMD`, which suggests it does), these run a shell on Linux. On macOS (BSD `script`) the shell does not run. Fix: in strict mode, refuse any option-looking word after `script`'s FILE.
- Unchanged from the earlier review: `ash`, `fish`, `csh`, `bash5`, `perl -e`, `node -e` and `python3 -` are not refused.

## Verification of N1-N3 fixes

**Verdict: CHANGES REQUESTED** (one new P1, caused by the N2 change).

Cases: `debug/rereview/verify.txt` and `verify2.txt`. D = `debug/devbase`. "Previous P" = the earlier patch plus my N1 patch (`debug/rereview/fixlib`). The regression test passes: 16 tests OK.

- **(1) Fixed.** All 16 N1 rows are REFUSED, including the `env -S ${X}` rows and the nested `nohup timeout` row.
- **(2) Fixed.** `xargs python3 ./tool.py`, `xargs -n 1 python3 ./tool.py`, `-m pytest` and `-- ./tool.py` are ADMITTED. `xargs python3`, `-m`, `-W x`, `--`, `-I`, `-X dev` and `-Im` are REFUSED.
- **(3) One unwanted new admission.** Condition (b) holds: no row is refused on D and admitted now. But a new P1 bypass appears: rows refused by the previous P are now ADMITTED (D admitted them too):
  - `echo '-cimport os' | xargs -I X python3 X`
  - `xargs -J % python3 %`, `xargs -J % python3 -I %`
  - `xargs -I X nohup python3 X`, `xargs --replace=X python3 X`

  `_python_options` reads the replacement word `X`/`%` as the script name and returns 'program'. At run time it becomes `-cCODE`, or with `-J` several words such as `-c CODE`, so Python runs inline code.

  Fix: pass `replace` into `_opaque_runner` and treat Python as opaque when a word up to and including the program word contains it. The coarse form is: `if supplied and replace is not None and any(replace in w for w in args[1:]): return True`. Add these rows to the test.
- **(4) Holds.** No crash: `inner` is always a list in strict mode, and none of the roughly 70 probe rows raised. No ordinary row is over-refused: `xargs --replace=@ cp @ ./a`, `xargs -I X touch ./a/X`, `xargs -I X timeout 5 touch ./a/X`, `xargs -J % cp % ./a` and `nohup env -S 'timeout 5 make ${X}'` stay ADMITTED.
- **Script fix (P3 over-refusal).** It refuses all Linux `-c`-after-FILE rows. It also refuses `script -q ./out ls --color` and `script -q ./out cc -c foo.c` (D ADMITTED), because the scan covers the command's own arguments on macOS. Accept and document this, or limit the scan to the option words that come right after FILE.

## Targeted confirm (final delta)

**Verdict: APPROVE.** There are no class (i) or class (ii) findings.

Code checked: blob aa4d021e (`hooks/lib`, identical to `debug/dev`). Cases: `debug/rereview/final.txt`. The regression test passes: 16 tests OK.

- **No class (i) regression.** On the full case set (`allcases2.txt`, about 400 rows), nothing refused by develop is admitted now, and nothing raised an exception.
- **No class (ii) broken row.** All 7 new refused rows are REFUSED. All 5 keep-outcome rows are ADMITTED, as on develop. The earlier N1 rows, the N2 rows, `xargs --replace=@ cp @ ./a` and `xargs -I X touch ./a/X` are unchanged.
- **(iii) Residual, develop also admits.** `xargs -J % python3 -W % ./tool.py` (also `-X %`, `--check-hash-based-pycs %`, and the same behind `nohup`) is ADMITTED. `_python_options` skips the value of `-W`, `-X` and `--check-hash-based-pycs` without checking it for the replacement string. BSD `-J` inserts several words, so input `x -c CODE` gives `python3 -W x -c CODE ./tool.py`. Optional fix: return 'open' when the skipped value word contains `replace`.
- **(iii) Residual, Linux only, unverified.** `script ./out ls -c 'touch /tmp/x'` and `script ./out -q ls -c ...` are ADMITTED, because the scan stops at `ls`. This matters only if util-linux script reads options after a word that is not an option and accepts the extra operand.

## Confirm (python floor narrowing)

**Verdict: APPROVE.** Code checked: blob 0f746e72, compared with develop in `debug/mergedbase`. Cases: `debug/rereview/floor.txt`, plus all earlier case files (`allcases3.txt`). The regression test passes: 16 tests OK.

- **(i) None.** No row that develop refuses is admitted now, and no row raised an exception. The literal `python`/`python3` floor is unchanged: `python3 -m pytest -c setup.cfg` and `python3 ./tool.py -c` are still REFUSED.
- **(ii) None.** Both new refused rows are REFUSED. All 3 keep-outcome rows are ADMITTED, as on develop.
- **(iii) No new bypass from path spellings.** With a path, case or version spelling, `-c` in the option region is REFUSED in every form I tried: after a `-W`/`-X` value given separately or attached, after `--check-hash-based-pycs always` or `=always`, in clusters (`-bIc`, `-Ic`), attached (`-cimport os`), after `-u -O -OO`, and behind `nohup`, `timeout` or xargs `-I`.
  - `/usr/bin/python3 -- -c ...` and `-W -c ./tool.py` are ADMITTED. That is correct: Python runs a file named `-c` after `--`, and `-W` takes `-c` as its value.
  - The earlier `xargs -J % python3 -W % ...` residual is unchanged.

## Passes 5-6: third reviewer, on the tree merged with develop dbd78db3

### Pass 5: targeted confirm (python/python3-only -c floor + 5 path-spelled rows)

Tree: merge 5a2b9c31 (develop dbd78db3) + fix; lib blob 0f746e72, test b40268b0; develop lib 7347e750.

**Verdict: CLEAN for the delta's goals. Three findings outside the floor, none of them regressions.**

**Q1. Develop's floor is kept.** Develop only refused the literal names (`debug/base-5a2b9c31/hooks/lib/task_actions.py:3016`): `args[0] in {'python','python3'}` and any word starting with `-c`. It made no allowance for paths, case or versions, and it did not look through wrappers. The fix gets the same `args` at the same call site (`hooks/lib/task_actions.py:3221`). For a literal name at depth 0, nothing returns False before the floor at `:1289`:
- the regex at `:1276` matches,
- `_python_read` is skipped because `wrapped=False`,
- stripping assignments can only refuse more.

I found no command that develop refused and the fix lets through. `python3 -m pytest -c x` is refused on both.

**Q2. Probes against the fix (`refuse_opaque_runner`).** All of these are refused: `/opt/venv/bin/python -Ic 1`, `Python3 -IScprint`, `/x/python3.12 -Wd -c 1`, `-X dev -c`, `-Xdev -c`, `--check-hash-based-pycs always -c 1`, `-IW error -c 1`, `-IWX -c 1`, `-E -W ignore -X utf8 -c 1`, `-OO -c1`, `/x/PYTHON -E -s -c1`.

These pass, and that is correct CPython behaviour: `-W -c 1` and `-X -c 1` (the `-c` is the option's value), `-- -c 1` (a script file named `-c`) and `-I -m -c` (a module named `-c`).

**Findings (none are regressions; develop gives `mutation` for each):**

- **F1, `:1276`. Some interpreter names don't match the regex, so `-c` is never refused.** `python3.13t -c 1` gets `mutation` on both develop and the fix. The same holds for `python3t`, `python3.7m` and other ABI-suffixed names. The python.org macOS installer ships `python3.13t`/`python3t` for free-threaded builds. This misses the goal of refusing any spelling.
- **F2, `:1297`. Python 2's `-Q` takes a value but isn't modelled.** `python2.7 -Q new -c 1` passes: the scan reads `new` as the script, but Python 2 runs the `-c` code. `python2 -Qnew -c 1` is refused. Low impact (Python 2 is end-of-life).
- **F3, `:1289`. The literal-name floor also fires behind wrappers, where develop never refused anything.** `nohup python3 -m pytest -c x` is now refused (develop: `mutation`), while `nohup /usr/bin/python3 -m pytest -c pytest.ini` stays `mutation`. That inconsistency contradicts the "wrappers keep their outcome" goal of `test_wrappers_in_front_of_ordinary_commands_keep_their_outcome`. It is stricter, not weaker. Limiting the floor to `not wrapped` would fix it.

**Q3. The five rows behave as claimed.** I called `task_actions.action()` directly against both libs; I didn't run the unittest because its fixture writes files.

| Row | Develop | Fix |
|---|---|---|
| `/opt/venv/bin/python -Ic 1` | mutation (row fails) | refused |
| `nohup /usr/bin/python3 -W error -c 1` | mutation (row fails) | refused |
| `/absolute/venv/bin/python -m pytest -c pyproject.toml ./test_app.py` | mutation | mutation |
| `nohup /usr/bin/python3 -m pytest -c pytest.ini` | mutation | mutation |
| `/opt/venv/bin/python ./tool.py -c x` | mutation | mutation |

The last three pass on develop as they should, since they assert develop's outcome. They guard the delta: the earlier any-word `-c` check would have refused them. Note that the second refused row in the test uses `'print(1)'`; I probed with `1`, which follows the same path.

The checks are `_opaque_runner`/`_python_options` at `hooks/lib/task_actions.py:1265-1327`. The test rows are at `hooks/_test/wrapped_opaque_runner_1376.py:76` (refused) and `:250-252` (mutation).

Author note: the coordinator ruled F1 and F3 fixed in this PR (lib blob 2d1df348, test 4488b6a7, with red rows) and F2 a residual under #1450. Before reporting, the author confirmed F1 (:1276) and F3 (:1289) by reading the code.

### Pass 6: confirm of the F1/F3 delta (same reviewer)

Tree: merge 5a2b9c31 + fix; lib blob 2d1df348, test 4488b6a7; compared with develop 7347e750 and the previous lib 0f746e72.

**Verdict: CLEAN.** I checked the blobs (lib 2d1df348, test 4488b6a7, previous lib 0f746e72) and ran `task_actions.action()` against develop, the previous lib and the new lib, read-only.

**(1) Nothing develop refused is let through.** Develop's refusal (`debug/base-5a2b9c31/hooks/lib/task_actions.py:3016`) only ever saw the top-level argv, which is depth 0 with `wrapped=False`. So F3's `not wrapped` floor at `hooks/lib/task_actions.py:1290` keeps the bare literal forms exactly. Every bare form develop refused is still refused:
- `python3 -W x -c 1`
- `python3 ./t.py -c x`
- `python3 -- -c`
- `python3 -m -c`
- `python -X -c 1`
- `python3 -I -c 'open("x","w")'`
- `env python3 -c 1`
- `env -i python3 -m pytest -c x`
- `command python3 -c 1`

The `-I -c 'print(1)'` read-only admission is unchanged on all three libs. The only changes from the previous lib are in wrapped forms, where develop gave `mutation`: `nohup python3 -m pytest -c x` and `timeout 5 python3 ./tool.py -c x` go back to `mutation`. Inline wrapped forms (`xargs python3 -c 1`, `nohup python3 -c 1`, `timeout 5 python -Ic 1`) stay refused.

**(2) F1 only adds refusals.** `_python_read` uses its own narrower name test (`:2305`, `python(?:3(?:\.[0-9]+)?)?`), so names with ABI flags can never come out `read_only`. `python3.13t -I -c 'print(1)'`, `/usr/bin/python3.13t -I -c 'print(1)'` and `timeout 5 python3.13t -I -c 'print(1)'` went from `mutation` to refused. Script and module forms stay `mutation`: `python3.13t ./x.py`, `python3.7m ./x.py`, `python3.13t -m pytest -c pytest.ini`, `xargs python3.13t ./x.py`.

**(3) Every new row is correct.** The refused rows at test `:78-80` (python3.13t, python3t, python3.7m, python3.13d -Ic, python3.2mu, nohup python3.13t, timeout 5 python3.7dm) are refused on the new lib and `mutation` on develop. The keep-outcome rows at `:259-262` match the new outcomes: the two `mutation` rows are develop's outcome, and the two refused rows are refused on both the previous and new libs.

A side note outside this delta: `timeout 5 /usr/bin/python3.12 -I -c 'print(1)'` is refused, but `timeout 5 python3 -I -c 'print(1)'` is `mutation`. This was already true on the previous lib, and it is stricter, not a regression.

Author note: the `:2305` citation in (2) is wrong; that regex belongs to a pytest-detection helper. The operative check is `_python_read` at `hooks/lib/task_actions.py:251`, which accepts only the literal `args[0] in {"python", "python3"}`. The author verified this by reading the code; the conclusion is unchanged. The coordinator ruled the side note a known residual (over-refusal) in the PR body, with the lib unchanged.

## Pass 7: fourth reviewer, after replaying the fix onto develop ec4d1645

Tree: develop ec4d1645 + cherry-picked bbbe71f0 (test) and the fix commit; lib blob f830db8d, test 4488b6a7; develop lib 9895ffb8 (adds #1473 child credential-helper removal in `_action`, ahead of the opaque-runner check, and commit 8e65484e, which makes `git --version` read-only).

**Verdict: CLEAN.** I found no regression and no way around the check. One caveat: I couldn't run any Python probes. The live mutation gate refused both `python3 -I -B -c ...` ("opaque inline execution") and the heredoc form ("shell group requires mutation handling"). I did not pipe the code through stdin to get past the gate. So (a) and (b) rest on reading the code, and (c) on comparing the diffs.

**(c) Replay is correct.** In both `git diff 7347e750 2d1df348` and `git diff 9895ffb8 f830db8d`, the added and removed lines hash the same (`58a40b34...`). The hunk bodies, context lines included, also hash the same (`409e1456...`). The eight hunks differ only in their line offsets (+54 or +65). `HEAD:hooks/lib/task_actions.py` is f830db8d and the debug copy is 9895ffb8, as stated.

**(a) The #1473 interaction is safe.** `child_helper_removal` (`hooks/lib/task_actions.py:33`) only acts when the command starts with `env -u`. Any `env -u` shape other than exactly `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 git clone ...` is refused with "unsupported child Git environment removals", in both develop and the fix.
- The stripped argv is `git clone ...`, which is what `env -u` actually runs. `refuse_opaque_runner(args)` at :3289 checks it, and no runner can sit behind the prefix.
- The prefix followed by `sh -c`, `timeout 5 sh -c`, `nohup python3 -c` or `git -c core.pager=... clone` is refused by the removal itself, in both versions.
- With the prefix inside a wrapper (`timeout 5 env -u ... git clone`, or `nohup`/`sudo`/`FOO=1`), the removal does not apply because the command starts with the wrapper. The fix then unwraps (env's `-u` is in `_WRAPPER_VALUES` at :939), reaches `git clone`, and gives the same outcome as develop. `timeout 5 env -u ... sh -c x` is now refused, where develop did not refuse it.
- Clone options such as `--upload-pack` and `-c core.sshCommand` are handled by `git_command.prefix`, which the fix does not touch. Whatever they do, the outcome is the same as develop.

**(b) No regression.** The fix only adds refusals at the call site:
- Develop refused when the command name is exactly one of the shell runners or eval/exec, or is `python`/`python3` with a word starting `-c`. `_opaque_runner` at depth 0 refuses every such case: the name is matched by basename and case-insensitively, and the bare `python`/`python3` `-c` rule is kept explicitly. Stripping a leading `VAR=` word never removes a runner name.
- The fix's other changes (`strict=` and the new tables) are only active inside `refuse_opaque_runner`. Other callers of `_wrapped_command` (:1460, :2799, :2866) don't pass `strict`, and the strict path builds a new set rather than changing the shared tables.
- `git --version` goes through `reader()` and never reaches :3289. Wrapped forms unwrap to `git` and are left alone. `git --version; sh -c x` is split into two commands, and `sh -c x` is refused in both versions.

If you want the probe matrix run, it needs a channel the gate allows, such as a Task binding or an existing script file.

Author note: because the reviewer could not probe, the author ran the probe matrix through a script file (`WT/debug/probe1473.py`, with exactly one inherited credential-helper entry, as #1473 requires), once per library, calling `task_actions.action()`. Over 22 commands, every command develop 9895ffb8 refuses is also refused by f830db8d. The fix newly refuses `timeout 5 env -u ... sh -c`, `nohup env -u ... python3 -c`, `FOO=1 env -u ... sh -c`, `timeout 5 sh -c`, `nohup python3 -c` and `/usr/bin/python3.13t -c`. `git --version` and `timeout 5 git --version` stay read_only on both. Wrapped `env -u ... git clone` (behind `timeout` or `sudo`) is mutation on both libraries; that is the existing residual #1453 (wrapped git skips its own policy model), not a change. Outputs: `WT/debug/v2-probe1473-{develop-9895ffb8,fix-f830db8d}.txt`.
