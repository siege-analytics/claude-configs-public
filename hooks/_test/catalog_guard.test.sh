#!/bin/bash
# Test: hooks/infrastructure/catalog-guard.sh and its raw-command classifier.
#
# The classifier tests intentionally bypass extract-json.py. Consumer tests use
# full hook JSON and assert that the hook's actual extractor returns the exact,
# nonempty command before interpreting an allow/block result.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/infrastructure/catalog-guard.sh"
CLASSIFIER="$REPO_ROOT/hooks/lib/classify-catalog-command.py"
EXTRACTOR="$REPO_ROOT/hooks/lib/extract-json.py"

PASS=0
FAIL=0
CONSUMER_CASES=0
EXTRACTION_CONTROLS=0
FAILED_NAMES=()

record_pass() {
    PASS=$((PASS + 1))
    printf '  [PASS] %s\n' "$1"
}

record_fail() {
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("$1")
    printf '  [FAIL] %s%s\n' "$1" "${2:+: $2}"
}

make_payload() {
    python3 - "$1" <<'PY'
import json
import sys
print(json.dumps({"tool_input": {"command": sys.argv[1]}}))
PY
}

assert_nonempty_extraction() {
    local name="$1" payload="$2" expected="$3" extracted status
    extracted=$(printf '%s' "$payload" | python3 "$EXTRACTOR" tool_input.command 2>/dev/null)
    status=$?
    if [[ "$status" -ne 0 || -z "$extracted" || "$extracted" != "$expected" ]]; then
        record_fail "$name extraction control" "actual extractor returned status $status and ${#extracted} bytes"
        return 1
    fi
    EXTRACTION_CONTROLS=$((EXTRACTION_CONTROLS + 1))
    return 0
}

expect_classifier() {
    local expected="$1" name="$2" command="$3" reason_pattern="${4:-}"
    local out actual
    out=$(printf '%s' "$command" | python3 "$CLASSIFIER" 2>&1)
    actual=$?
    if [[ "$actual" -eq "$expected" ]] && {
        [[ -z "$reason_pattern" ]] || printf '%s' "$out" | grep -qE "$reason_pattern"
    }; then
        record_pass "classifier: $name (exit $actual)"
    else
        record_fail "classifier: $name" "expected exit $expected${reason_pattern:+ matching /$reason_pattern/}, got $actual: ${out:0:240}"
    fi
}

expect_consumer() {
    local expected="$1" name="$2" command="$3" reason_pattern="${4:-}"
    local payload out actual
    payload=$(make_payload "$command")
    CONSUMER_CASES=$((CONSUMER_CASES + 1))
    if ! assert_nonempty_extraction "$name" "$payload" "$command"; then
        return
    fi
    out=$(printf '%s' "$payload" | bash "$HOOK" 2>&1)
    actual=$?
    if [[ "$actual" -eq "$expected" ]] && {
        [[ -z "$reason_pattern" ]] || printf '%s' "$out" | grep -qE "$reason_pattern"
    }; then
        record_pass "consumer: $name (exit $actual)"
    else
        record_fail "consumer: $name" "expected exit $expected${reason_pattern:+ matching /$reason_pattern/}, got $actual: ${out:0:240}"
    fi
}

expect_block() {
    expect_consumer 2 "$1" "$2" "$3"
}

expect_pass() {
    expect_consumer 0 "$1" "$2"
}

WRITE='.write.parquet("s3a://gold/table/")'
OBJECT_REASON='Direct S3 copy into catalog-managed bucket'
RAW_REASON='Python/Spark raw-path write'
FORMAT_REASON='Spark write.format.*bypasses catalog'
KUBECTL_REASON='kubectl exec.*catalog bypass'
DEPTH_REASON='Command nesting exceeds catalog-guard classifier depth'

printf '\nRaw classifier source (no JSON extractor dependency)\n'
expect_classifier 2 "direct aws copy" \
    'aws s3 cp ./out s3a://hive-warehouse/table/' "$OBJECT_REASON"
expect_classifier 2 "pipeline consumer executes copy" \
    "printf '%s\\n' ./out | xargs aws s3 cp s3://gold/table/" "$OBJECT_REASON"
expect_classifier 2 "python payload executes write" \
    "python3 -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_classifier 0 "grep only consumes quoted write prose" \
    "grep '$WRITE' notes.md"
expect_classifier 0 "quoted heredoc is documentation" \
    $'cat <<\'EOF\'\naws s3 cp ./out s3://gold/table/\nEOF'
expect_classifier 0 "malformed quoted prose cannot execute" \
    "grep '$WRITE"
DEEP_COMMAND=$(python3 - <<'PY'
import shlex
command = "aws s3 cp ./out s3://gold/table/"
for _ in range(10):
    command = "sh -c " + shlex.quote(command)
print(command)
PY
)
expect_classifier 2 "excessive nesting fails closed" \
    "$DEEP_COMMAND" "$DEPTH_REASON"
DEEP_EVAL_COMMAND=$(python3 - <<'PY'
print("eval " * 400 + "echo safe")
PY
)
expect_classifier 2 "literal stdout recursion limit fails closed" \
    "$DEEP_EVAL_COMMAND" "$DEPTH_REASON"
if python3 - "$CLASSIFIER" <<'PY'
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("catalog_guard_classifier", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    module._process_command_consumes_stdin(
        "cat", depth=module.MAX_RECURSION + 1
    )
except module.ClassificationDepthError as error:
    if str(error) == module.DEPTH_REASON:
        raise SystemExit(0)
raise SystemExit(1)
PY
then
    record_pass "classifier: stdin-consumption depth fails closed"
else
    record_fail "classifier: stdin-consumption depth fails closed"
fi

printf '\nPreserved Python, Spark, and kubectl block paths\n'
expect_block "python raw write" \
    "python3 -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python whitespace around attribute dot" \
    "python3 -c 'df.write .parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python whitespace after receiver dot" \
    "python3 -c 'df. write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python writer mode chain" \
    "python3 -c 'df.write.mode(\"overwrite\").parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python concatenated literal path" \
    "python3 -c 'df.write.parquet(\"s3\" + \"a://gold/table/\")'" "$RAW_REASON"
expect_block "python assigned static path" \
    "python3 -c 'path = \"s3a://gold/table/\"; df.write.parquet(path)'" "$RAW_REASON"
expect_block "python named expression static path" \
    "python3 -c 'df.write.parquet(path := \"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python f-string static path" \
    "python3 -c 'path = \"s3a://gold/table/\"; df.write.parquet(f\"{path}\")'" "$RAW_REASON"
expect_block "python assigned path used before overwrite" \
    "python3 -c 'path = \"s3a://gold/table/\"; df.write.parquet(path); path = \"/tmp/local\"'" "$RAW_REASON"
expect_block "python assigned writer alias" \
    "python3 -c 'writer = df.write; writer.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python assigned chained writer alias" \
    "python3 -c 'writer = df.write.mode(\"overwrite\"); writer.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python getattr writer method" \
    "python3 -c 'getattr(df.write, \"parquet\")(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python getattr writer root" \
    "python3 -c 'getattr(df, \"write\").parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python writer path option" \
    "python3 -c 'df.write.option(\"path\", \"s3a://gold/table/\").save()'" "$RAW_REASON"
expect_block "python writer unpacked path options" \
    "python3 -c 'df.write.options(**{\"path\": \"s3a://gold/table/\"}).save()'" "$RAW_REASON"
expect_block "python writer starred literal path" \
    "python3 -c 'df.write.parquet(*[\"s3a://gold/table/\"])'" "$RAW_REASON"
expect_block "python os system shell payload" \
    "python3 -c 'import os; os.system(\"aws s3 cp ./out s3://gold/table/\")'" "$OBJECT_REASON"
expect_block "python imported subprocess executor" \
    "python3 -c \"from subprocess import run; run('aws s3 cp ./out s3://gold/table/', shell=True)\"" "$OBJECT_REASON"
expect_block "python aliased subprocess module executor" \
    "python3 -c \"import subprocess as sp; sp.run('aws s3 cp ./out s3://gold/table/', shell=True)\"" "$OBJECT_REASON"
expect_block "python assigned subprocess module alias" \
    "python3 -c 'import subprocess; sp = subprocess; sp.run([\"aws\", \"s3\", \"cp\", \"./out\", \"s3://gold/table/\"])'" "$OBJECT_REASON"
expect_block "python assigned imported executor alias" \
    "python3 -c 'from subprocess import run; invoke = run; invoke([\"aws\", \"s3\", \"cp\", \"./out\", \"s3://gold/table/\"])'" "$OBJECT_REASON"
expect_block "python imported os system executor" \
    "python3 -c \"from os import system; system('aws s3 cp ./out s3://gold/table/')\"" "$OBJECT_REASON"
expect_block "python aliased os module executor" \
    "python3 -c \"import os as o; o.system('aws s3 cp ./out s3://gold/table/')\"" "$OBJECT_REASON"
expect_block "python subprocess literal split argv" \
    "python3 -c \"import subprocess; subprocess.check_call('aws s3 cp ./out s3://gold/table/'.split())\"" "$OBJECT_REASON"
expect_block "python subprocess literal split separator argv" \
    "python3 -c \"import subprocess; subprocess.run('aws s3 cp ./out s3://gold/table/'.split(' '))\"" "$OBJECT_REASON"
expect_block "python subprocess assigned literal argv" \
    "python3 -c \"import subprocess; argv = 'aws s3 cp ./out s3://gold/table/'.split(); subprocess.run(argv)\"" "$OBJECT_REASON"
expect_block "python subprocess concatenated literal argv" \
    "python3 -c 'import subprocess; subprocess.run([\"aws\", \"s3\", \"cp\", \"./out\"] + [\"s3://gold/table/\"])'" "$OBJECT_REASON"
expect_block "python os execlp shell argv" \
    "python3 -c \"import os; os.execlp('sh', 'sh', '-c', 'aws s3 cp ./out s3://gold/table/')\"" "$OBJECT_REASON"
expect_block "python os execle shell argv" \
    "python3 -c \"import os; os.execle('/bin/sh', 'sh', '-c', 'aws s3 cp ./out s3://gold/table/', {})\"" "$OBJECT_REASON"
expect_block "python subprocess argv payload" \
    "python3 -c 'import subprocess; subprocess.run([\"aws\", \"s3\", \"cp\", \"./out\", \"s3://gold/table/\"])'" "$OBJECT_REASON"
expect_block "python subprocess args keyword payload" \
    "python3 -c 'import subprocess; subprocess.run(args=[\"aws\", \"s3\", \"cp\", \"./out\", \"s3://gold/table/\"])'" "$OBJECT_REASON"
expect_block "python subprocess shell payload" \
    "python3 -c 'import subprocess; subprocess.run(\"aws s3 cp ./out s3://gold/table/\", shell=True)'" "$OBJECT_REASON"
expect_block "python subprocess shell list payload" \
    "python3 -c 'import subprocess; subprocess.run([\"aws s3 cp ./out s3://gold/table/\"], shell=True)'" "$OBJECT_REASON"
expect_block "python exec static write payload" \
    "python3 -c 'exec(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'" "$RAW_REASON"
expect_block "python exec inherits static path" \
    "python3 -c 'path = \"s3a://gold/table/\"; exec(\"df.write.parquet(path)\")'" "$RAW_REASON"
expect_block "python exec inherits writer method alias" \
    "python3 -c 'save = df.write.parquet; exec(\"save(\\\"s3a://gold/table/\\\")\")'" "$RAW_REASON"
expect_block "python imported builtins exec alias" \
    "python3 -c 'from builtins import exec as invoke; invoke(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'" "$RAW_REASON"
expect_block "python aliased builtins eval module" \
    "python3 -c 'import builtins as b; b.eval(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'" "$RAW_REASON"
expect_block "python loop body static path" \
    "python3 -c 'for _ in [0]: path = \"s3a://gold/table/\"; df.write.parquet(path)'" "$RAW_REASON"
expect_block "python invoked lambda static path" \
    "python3 -c 'path = \"s3a://gold/table/\"; (lambda: df.write.parquet(path))()'" "$RAW_REASON"
expect_block "python assigned invoked lambda write" \
    "python3 -c 'f = lambda: df.write.parquet(\"s3a://gold/table/\"); f()'" "$RAW_REASON"
expect_block "python aliased invoked lambda write" \
    "python3 -c 'f = lambda: df.write.parquet(\"s3a://gold/table/\"); g = f; g()'" "$RAW_REASON"
expect_block "python invoked instance method write" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\nJob().run()\'' "$RAW_REASON"
expect_block "python instantiated constructor executor" \
    $'python3 -c \'class Job:\n    def __init__(self):\n        import os\n        os.system("aws s3 cp ./out s3://gold/table/")\nJob()\'' "$OBJECT_REASON"
expect_block "python assigned instance method write" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\njob = Job()\njob.run()\'' "$RAW_REASON"
expect_block "python restored class method write" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\noriginal = Job.run\nJob.run = lambda self: None\nJob.run = original\nJob().run()\'' "$RAW_REASON"
expect_block "python bound method alias write" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\njob = Job()\ncallback = job.run\ncallback()\'' "$RAW_REASON"
expect_block "python constructor method alias write" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\ncallback = Job().run\ncallback()\'' "$RAW_REASON"
expect_block "python static argv function argument" \
    "python3 -c 'import subprocess; invoke = lambda argv: subprocess.run(argv); invoke(\"aws s3 cp ./out s3://gold/table/\".split())'" "$OBJECT_REASON"
expect_block "python Spark foreachBatch callback write" \
    "python3 -c 'stream_df.writeStream.foreachBatch(lambda b, i: b.write.parquet(\"s3a://gold/events/\")).start()'" "$RAW_REASON"
expect_block "python Spark foreachBatch aliased callback write" \
    $'python3 -c \'def save(batch, index):\n    batch.write.parquet("s3a://gold/events/")\ncallback = save\nstream_df.writeStream.foreachBatch(callback).start()\'' "$RAW_REASON"
expect_block "python invoked function write" \
    $'python3 -c \'def run(): df.write.parquet("s3a://gold/table/")\nrun()\'' "$RAW_REASON"
expect_block "python bound writer method alias" \
    "python3 -c 'save = df.write.parquet; save(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python chained bound writer method alias" \
    "python3 -c 'save = df.write.parquet; alias = save; alias(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python function resolves later global path" \
    $'python3 -c \'def run():\n    df.write.parquet(path)\npath = "s3a://gold/table/"\nrun()\'' "$RAW_REASON"
expect_block "python function static default path" \
    $'python3 -c \'def run(path="s3a://gold/table/"):\n    df.write.parquet(path)\nrun()\'' "$RAW_REASON"
expect_block "python function static keyword path" \
    $'python3 -c \'def run(path):\n    df.write.parquet(path)\nrun(path="s3a://gold/table/")\'' "$RAW_REASON"
expect_block "python function named static default path" \
    $'python3 -c \'path = "s3a://gold/table/"\ndef run(target=path):\n    df.write.parquet(target)\nrun()\'' "$RAW_REASON"
expect_block "python function default retains definition value" \
    $'python3 -c \'path = "s3a://gold/table/"\ndef run(target=path):\n    df.write.parquet(target)\npath = "/tmp/local"\nrun()\'' "$RAW_REASON"
expect_block "python format save" \
    "python3 -c 'df.write.format(\"delta\").save(\"s3a://gold/table/\")'" "$FORMAT_REASON"
expect_block "python format save with attribute whitespace" \
    "python3 -c 'df.write . format(\"delta\") . save(\"s3a://gold/table/\")'" "$FORMAT_REASON"
expect_block "python format save with writer mode chain" \
    "python3 -c 'df.write.mode(\"overwrite\").format(\"delta\").save(\"s3a://gold/table/\")'" "$FORMAT_REASON"
expect_block "spark submit visible write payload" \
    "spark-submit --conf 'job=$WRITE' app.py" "$RAW_REASON"
expect_block "kubectl exec original format path" \
    "kubectl exec pod -- python3 -c 'df.write.format(\"delta\")'" "$KUBECTL_REASON"
expect_block "kubectl exec python raw write" \
    "kubectl exec pod -- python3 -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python heredoc write" \
    $'python3 <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY' "$RAW_REASON"
expect_block "python explicit stdin script write" \
    $'python3 - <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY' "$RAW_REASON"
expect_block "fd zero self duplication preserves heredoc" \
    $'sh <<\'EOF\' 0<&0\naws s3 cp ./out s3://gold/table/\nEOF' "$OBJECT_REASON"
expect_block "nonzero heredoc duplicated onto Python stdin" \
    $'python3 3<<\'PY\' 0<&3\ndf.write.parquet("s3a://gold/table/")\nPY' "$RAW_REASON"
expect_block "later Python heredoc overrides file stdin" \
    $'python3 < /dev/null <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY' "$RAW_REASON"
expect_block "leading python heredoc redirection" \
    $'<<\'PY\' python3\ndf.write.parquet("s3a://gold/table/")\nPY' "$RAW_REASON"
expect_block "python script from nonzero fd here string" \
    "python3 /dev/fd/3 3<<<'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python script from pipeline duplicated fd" \
    "printf '%s\\n' 'df.write.parquet(\"s3a://gold/table/\")' | python3 /dev/fd/3 3<&0" "$RAW_REASON"

printf '\nDirect and wrapped object copies (direction remains conservative)\n'
expect_block "direct aws cp" \
    'aws s3 cp ./out s3a://hive-warehouse/table/' "$OBJECT_REASON"
expect_block "direct aws cp to managed bucket root" \
    'aws s3 cp ./out s3://gold' "$OBJECT_REASON"
expect_block "aws stdin upload expected size keeps managed operand" \
    "aws s3 cp - --expected-size 123 s3://gold/table/" "$OBJECT_REASON"
expect_block "aws global cli binary format before s3 copy" \
    "aws --cli-binary-format raw-in-base64-out s3 cp ./out s3://gold/table/" "$OBJECT_REASON"
expect_block "aws global cli binary format inside s3 copy" \
    "aws s3 --cli-binary-format raw-in-base64-out cp ./out s3://gold/table/" "$OBJECT_REASON"
expect_block "leading output redirection before copy" \
    '>/dev/null aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "leading numeric redirection before copy" \
    '2>/dev/null aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "redirection after copy program" \
    'aws >/dev/null s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "redirection between copy subcommands" \
    'aws s3 >/dev/null cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "aws split by shell line continuation" \
    $'aw\\\ns s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "direct aws sync" \
    'aws --profile dev s3 sync ./out "s3://silver/table/"' "$OBJECT_REASON"
expect_block "direct mc cp" \
    'mc cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "direct mc mirror" \
    'mc --quiet mirror ./out s3://bronze/table/' "$OBJECT_REASON"
expect_block "managed source copy remains blocked" \
    'aws s3 cp s3://gold/table/part-0 ./local' "$OBJECT_REASON"
expect_block "sudo wrapper" \
    'sudo -u operator aws s3 cp ./out s3://bullion/table/' "$OBJECT_REASON"
expect_block "timeout wrapper" \
    'timeout 300 aws s3 sync ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "timeout value options wrapper" \
    'timeout --signal KILL --kill-after=10s 300s aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "nice wrapper" \
    'nice -n 10 mc cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "stdbuf wrapper" \
    'stdbuf -oL aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "setsid wrapper" \
    'setsid --fork aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "mid-word hash remains in copy argument" \
    'aws s3 cp ./a#b s3://gold/table/' "$OBJECT_REASON"
# This substitution must remain literal test input for the hook classifier.
# shellcheck disable=SC2016
expect_block "escaped whitespace keeps hash inside executable word" \
    'echo foo\ #$(aws s3 cp ./out s3://gold/table/)' "$OBJECT_REASON"
expect_block "leading assignment" \
    'AWS_PROFILE=dev mc cp ./out s3://platinum/table/' "$OBJECT_REASON"
expect_block "env wrapper" \
    'env AWS_PROFILE=dev aws s3 cp ./out s3://quicksilver/table/' "$OBJECT_REASON"
expect_block "env split-string wrapper" \
    "env -S 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "xargs wrapper" \
    "printf '%s\\n' ./out | xargs aws s3 cp s3://gold/table/" "$OBJECT_REASON"
expect_block "xargs options and nested wrappers" \
    "printf '%s\\0' ./out | xargs -0 -n1 sudo env AWS_PROFILE=dev aws s3 cp s3://gold/table/" "$OBJECT_REASON"
expect_block "xargs replacement injects literal shell payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | xargs -I{} sh -c '{}'" "$OBJECT_REASON"
expect_block "NUL xargs preserves shell c payload item" \
    "printf '%s\\0' 'aws s3 cp ./out s3://gold/table/' | xargs -0 sh -c" "$OBJECT_REASON"
expect_block "xargs max-args exposes later shell payload" \
    "printf '%s\\0' 'echo safe' 'aws s3 cp ./out s3://gold/table/' | xargs -0 -n1 sh -c" "$OBJECT_REASON"
expect_block "copy in later pipeline segment" \
    'printf payload | aws s3 cp - s3://gold/table/' "$OBJECT_REASON"
expect_block "copy in middle of three segments" \
    'printf payload | aws s3 cp - s3://gold/table/ | cat' "$OBJECT_REASON"
expect_block "literal printf payload piped to shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh" "$OBJECT_REASON"
expect_block "dev stdin alias preserves pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh < /dev/stdin" "$OBJECT_REASON"
expect_block "fd zero alias preserves pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh < /dev/fd/0" "$OBJECT_REASON"
expect_block "fd zero duplication preserves pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh 0<&0" "$OBJECT_REASON"
expect_block "nonzero input fd redirect leaves stdin pipeline" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh 3</dev/null" "$OBJECT_REASON"
expect_block "inline shell program forwards outer stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'cat | sh'" "$OBJECT_REASON"
expect_block "later compound shell inherits outer stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'echo safe; sh'" "$OBJECT_REASON"
expect_block "inline shell stdout feeds downstream shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'cat' | sh" "$OBJECT_REASON"
expect_block "producer stderr redirect preserves pipeline" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' 2>/dev/null | sh" "$OBJECT_REASON"
expect_block "literal payload passes through cat to shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | cat | sh" "$OBJECT_REASON"
expect_block "literal payload passes through mixed cat stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | cat - /dev/null | sh" "$OBJECT_REASON"
expect_block "literal payload passes through tee to shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | tee /tmp/catalog.log | sh" "$OBJECT_REASON"
expect_block "tee output process substitution feeds shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | tee >(sh)" "$OBJECT_REASON"
expect_block "printf assembles shell payload from literals" \
    "printf '%s %s\\n' 'aws' 's3 cp ./out s3://gold/table/' | sh" "$OBJECT_REASON"
expect_block "printf percent b decodes octal shell payload" \
    "printf '%b\\n' '\\0141ws s3 cp ./out s3://gold/table/' | sh" "$OBJECT_REASON"
expect_block "printf reuses consuming format for later command" \
    "printf '%s\\n' 'echo safe' 'aws s3 cp ./out s3://gold/table/' | sh" "$OBJECT_REASON"
expect_block "literal echo payload piped through env to shell" \
    "echo 'aws s3 cp ./out s3://gold/table/' | env sh" "$OBJECT_REASON"
expect_block "echo escape payload piped to shell" \
    "echo -e '\\x61ws s3 cp ./out s3://gold/table/' | sh" "$OBJECT_REASON"
expect_block "quoted heredoc producer piped to shell" \
    $'cat <<\'EOF\' | sh\naws s3 cp ./out s3://gold/table/\nEOF' "$OBJECT_REASON"
expect_block "literal payload forwarded to kubectl shell stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec -i pod -- sh" "$OBJECT_REASON"
expect_block "literal payload forwarded with combined kubectl flags" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec -it pod -- sh" "$OBJECT_REASON"
expect_block "literal payload forwarded with kubectl boolean stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec --stdin=true pod -- sh" "$OBJECT_REASON"
expect_block "literal Python payload piped to interpreter" \
    "printf '%s\\n' 'df.write.parquet(\"s3a://gold/table/\")' | python3" "$RAW_REASON"
expect_block "copy after control-list segment" \
    'printf safe; aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "copy after then keyword" \
    'if true; then aws s3 cp ./out s3://gold/table/; fi' "$OBJECT_REASON"
expect_block "copy in while condition" \
    'while aws s3 cp ./out s3://gold/table/; do break; done' "$OBJECT_REASON"
expect_block "commented heredoc marker does not hide next line" \
    $'echo ok # <<EOF\naws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "heredoc marker in multiline quote does not hide copy" \
    $'echo \'hello\n<<EOF\nworld\'\naws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "backslash-quoted heredoc delimiter terminates correctly" \
    $'cat <<\\EOF\nprose\nEOF\naws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "complete command before malformed tail" \
    $'aws s3 cp ./out s3://gold/table/\necho \'unterminated' "$OBJECT_REASON"
expect_block "complete copy before malformed heredoc substitution" \
    $'aws s3 cp ./out s3://gold/table/\ncat <<EOF\n$(\nEOF' "$OBJECT_REASON"
expect_block "complete copy before malformed heredoc declaration" \
    $'aws s3 cp ./out s3://gold/table/\ncat <<\'unterminated' "$OBJECT_REASON"
expect_block "kubectl exec direct copy" \
    'kubectl exec pod -- aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "kubectl global option before exec copy" \
    'kubectl --context dev exec pod -- aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"

printf '\nShell payloads and active substitutions\n'
expect_block "sh -c object copy" \
    "sh -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash ANSI-C quoted object copy" \
    "bash -c \$'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash ANSI-C quoted multiline copy" \
    "bash -c \$'echo safe\\naws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "invalid ANSI Unicode cannot hide later copy" \
    "echo \$'\\U00110000'; aws s3 cp ./out s3://gold/table/" "$OBJECT_REASON"
expect_block "ANSI-C escaped quote before managed copy operand" \
    "aws s3 cp \$'./bob\\'s.parquet' s3://gold/table/" "$OBJECT_REASON"
expect_block "ANSI-C escaped quote before later copy" \
    "x=\$'it\\'s'; aws s3 cp ./out s3://gold/table/" "$OBJECT_REASON"
expect_block "arithmetic shift before later copy" \
    'echo $((1<<2)); aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "multiline arithmetic shift before later copy" \
    $'echo $((1 << 2))\naws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "parameter length array before later copy" \
    'files=(a b); [ ${#files[@]} -gt 0 ] && aws s3 sync ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "parameter length assignment before later copy" \
    'n=${#x}; aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "positional count expansion before later copy" \
    'echo ${#}; aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "hash after parameter expansion before later copy" \
    'echo ${x}#; aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "hash after brace expansion before later copy" \
    'echo a{b,c}#d; aws s3 cp ./out s3://gold/table/' "$OBJECT_REASON"
expect_block "shell sources process substitution script" \
    "bash -c 'source <(printf \"%s\\n\" \"aws s3 cp ./out s3://gold/table/\")'" "$OBJECT_REASON"
expect_block "dot sources process substitution script" \
    "bash -c '. <(printf \"%s\\n\" \"aws s3 cp ./out s3://gold/table/\")'" "$OBJECT_REASON"
expect_block "source dev stdin consumes pipeline script" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | bash -c 'source /dev/stdin'" "$OBJECT_REASON"
expect_block "dot fd zero consumes pipeline script" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | bash -c '. /dev/fd/0'" "$OBJECT_REASON"
expect_block "source proc fd zero consumes here string" \
    "source /proc/self/fd/0 <<< 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "source script from nonzero fd here string" \
    "source /dev/fd/3 3<<<'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "source script from pipeline duplicated fd" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | source /dev/fd/3 3<&0" "$OBJECT_REASON"
expect_block "noexec can be reset before shell payload" \
    "bash -n +n -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "named noexec can be reset before shell payload" \
    "bash -o noexec +o noexec -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "eval object copy" \
    "eval 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "eval executes command substitution stdout" \
    "eval \"\$(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')\"" "$OBJECT_REASON"
expect_block "sh c executes command substitution stdout" \
    "sh -c \"\$(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')\"" "$OBJECT_REASON"
expect_block "eval substitution consumes pipeline stdin" \
    "printf 'aws s3 cp ./out s3://gold/table/\\n' | eval \"\$(cat)\"" "$OBJECT_REASON"
expect_block "eval consumes inherited shell payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | eval 'cat | sh'" "$OBJECT_REASON"
expect_block "eval stdout feeds downstream shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | eval 'cat' | sh" "$OBJECT_REASON"
expect_block "bash -lc python write" \
    "bash -lc 'python3 -c '\"'\"'df.write.parquet(\"s3a://gold/table/\")'\"'\"''" "$RAW_REASON"
expect_block "bash combined flags with c before final flag" \
    "bash -ce 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash all-letter valid flag cluster" \
    "bash -ctrue 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash value option before c payload" \
    "bash -o pipefail -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash clustered o option before c payload" \
    "bash -euo pipefail -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "bash clustered eo option before c payload" \
    "bash -eo pipefail -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "kubectl bash clustered o option payload" \
    "kubectl exec -i spark-0 -- bash -euo pipefail -c 'aws s3 cp /data/out s3://gold/table/'" "$OBJECT_REASON"
expect_block "python combined flags payload" \
    "python3 -Bc 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python option value before inline payload" \
    "python3 -X dev -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python warning option containing c before payload" \
    "python3 -Wignore::DeprecationWarning -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python implementation option containing c before payload" \
    "python3 -Xtracemalloc -c 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python attached -c payload" \
    "python3 -c'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "python here-string payload" \
    "python3 <<< 'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "fd zero Python here-string payload" \
    "python3 0<<<'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "attached python here-string operator" \
    "python3 <<<'df.write.parquet(\"s3a://gold/table/\")'" "$RAW_REASON"
expect_block "shell here-string payload" \
    "bash <<< 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "shell explicit stdin source payload" \
    "bash -s arg <<< 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "kubectl shell payload" \
    "kubectl exec pod -- sh -c 'aws s3 cp ./out s3://gold/table/'" "$OBJECT_REASON"
expect_block "kubectl shell preserves legacy format-only block" \
    "kubectl exec pod -- sh -c 'python3 -c '\"'\"'df.write.format(\"delta\")'\"'\"''" "$KUBECTL_REASON"
# These substitutions must remain literal test inputs; the hook, not this test
# process, classifies them.
# shellcheck disable=SC2016
expect_block "active dollar command substitution" \
    'echo "$(aws s3 cp ./out s3://gold/table/)"' "$OBJECT_REASON"
expect_block "unquoted substitution output forms invocation" \
    "\$(printf 'aws s3 cp ./out s3://gold/table/')" "$OBJECT_REASON"
expect_block "command substitution retains nested heredoc body" \
    $'echo $(python3 <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY\n)' "$RAW_REASON"
# shellcheck disable=SC2016
expect_block "active backtick substitution" \
    'echo `mc cp ./out s3://gold/table/`' "$OBJECT_REASON"
expect_block "input process substitution feeds shell source" \
    "sh < <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')" "$OBJECT_REASON"
expect_block "nonzero input fd does not override process stdin" \
    "sh < <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/') 3</dev/null" "$OBJECT_REASON"
expect_block "process substitution cat forwards heredoc" \
    $'sh < <(cat <<\'EOF\'\naws s3 cp ./out s3://gold/table/\nEOF\n)' "$OBJECT_REASON"
expect_block "later process stdin overrides earlier file redirect" \
    "sh < /dev/null < <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')" "$OBJECT_REASON"
expect_block "process substitution occupies shell script path" \
    "sh <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')" "$OBJECT_REASON"
expect_block "process substitution occupies Python script path" \
    "python3 <(printf '%s\\n' 'df.write.parquet(\"s3a://gold/table/\")')" "$RAW_REASON"
expect_block "Python process script consumes inherited stdin" \
    "printf '%s\\n' 'df.write.parquet(\"s3a://gold/table/\")' | bash -c 'python3 <(cat)'" "$RAW_REASON"
expect_block "nonconsuming process script leaves stdin for later shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c \"python3 <(printf '%s\\n' 'print(1)'); sh\"" "$OBJECT_REASON"
expect_block "dangerous command inside process substitution" \
    "cat <(aws s3 cp ./out s3://gold/table/)" "$OBJECT_REASON"
expect_block "output process substitution consumes literal stdout" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(sh)" "$OBJECT_REASON"
expect_block "later stderr redirect does not override process stdout" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(sh) 2>/dev/null" "$OBJECT_REASON"
expect_block "output process xargs injects shell payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(xargs -I{} sh -c '{}')" "$OBJECT_REASON"
expect_block "nested tee output process feeds shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(tee >(sh))" "$OBJECT_REASON"
expect_block "cat redirects pipeline into process shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | cat > >(sh)" "$OBJECT_REASON"
expect_block "unquoted heredoc substitution executes" \
    $'cat <<EOF\n$(aws s3 cp ./out s3://gold/table/)\nEOF' "$OBJECT_REASON"
expect_block "unquoted heredoc comment marker does not suppress expansion" \
    $'cat <<EOF\n# $(aws s3 cp ./out s3://gold/table/)\nEOF' "$OBJECT_REASON"
expect_block "single quotes in unquoted heredoc do not suppress expansion" \
    $'cat <<EOF\n\'$(aws s3 cp ./out s3://gold/table/)\'\nEOF' "$OBJECT_REASON"
expect_block "double quotes in unquoted heredoc do not suppress expansion" \
    $'cat <<EOF\n"$(aws s3 cp ./out s3://gold/table/)"\nEOF' "$OBJECT_REASON"

printf '\nQuoted prose and non-executing consumers\n'
expect_pass "kubectl logs piped to grep" \
    "kubectl logs deploy/app -n ns | grep '$WRITE'"
expect_pass "kubectl option value named exec is not subcommand" \
    "kubectl --context exec get pods -- aws s3 cp ./out s3://gold/table/"
expect_pass "git message names python and write syntax" \
    "git commit -m 'fix python3 -c $WRITE bypass'"
expect_pass "editor search contains write syntax" \
    "vim +'/df$WRITE/' notes.md"
expect_pass "grep argument names object copy" \
    "grep 'aws s3 cp ./out s3://gold/table/' notes.md"
expect_pass "leading redirection before grep remains prose" \
    ">/dev/null grep 'aws s3 cp ./out s3://gold/table/' notes.md"
expect_pass "inline redirection in grep remains prose" \
    "grep >/dev/null 'aws s3 cp ./out s3://gold/table/' notes.md"
expect_pass "echo argument names object copy" \
    "echo 'aws s3 cp ./out s3://gold/table/'"
expect_pass "eval only echoes copy prose" \
    "eval \"echo 'aws s3 cp ./out s3://gold/table/'\""
expect_pass "echo receives command substitution prose" \
    "echo \"\$(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')\""
expect_pass "quoted substitution is one command-name word" \
    "\"\$(printf 'aws s3 cp ./out s3://gold/table/')\""
expect_pass "echo receives pipeline substitution as prose" \
    "printf 'aws s3 cp ./out s3://gold/table/\\n' | echo \"\$(cat)\""
expect_pass "eval substitution only echoes copy prose" \
    "eval \"\$(printf '%s\\n' \"echo 'aws s3 cp ./out s3://gold/table/'\")\""
expect_pass "real shell comment remains nonexecuting" \
    "echo safe # aws s3 cp ./out s3://gold/table/"
expect_pass "real shell comment after control operator remains inert" \
    "echo safe;# aws s3 cp ./out s3://gold/table/"
expect_pass "parameter length expansions without invocation are safe" \
    'files=(a b); echo ${#files[@]} ${#x} ${#}'
expect_pass "hash suffixes without invocation are safe" \
    'echo ${x}# a{b,c}#d'
expect_pass "aws help argument is prose, not cp invocation" \
    "aws help 'aws s3 cp ./out s3://gold/table/'"
expect_pass "aws help positionals are not a cp invocation" \
    "aws help s3 cp s3://gold/table/"
expect_pass "aws metadata managed URI is not copy operand" \
    "aws s3 cp ./out s3://unmanaged/table/ --metadata 'note=s3://gold/table/'"
expect_pass "aws expected size local destination is allowed" \
    "aws s3 cp - --expected-size 123 ./local"
expect_pass "aws cli binary format unmanaged destination is allowed" \
    "aws --cli-binary-format raw-in-base64-out s3 cp ./out s3://unmanaged/table/"
expect_pass "aws cli binary format equals form unmanaged destination is allowed" \
    "aws s3 --cli-binary-format=raw-in-base64-out cp ./out s3://unmanaged/table/"
expect_pass "aws leading metadata managed URI is not copy operand" \
    "aws s3 cp --metadata 'note=s3://gold/table/' ./out s3://unmanaged/table/"
expect_pass "similarly named bucket is unmanaged" \
    "aws s3 cp ./out s3://goldish/table/"
expect_pass "mc help positionals are not a copy invocation" \
    "mc help cp s3://gold/table/"
expect_pass "mc attribute managed URI is not copy operand" \
    "mc cp ./out s3://unmanaged/table/ --attr 'note=s3://gold/table/'"
expect_pass "cat quoted heredoc contains commands" \
    $'cat <<\'EOF\'\naws s3 cp ./out s3://gold/table/\ndf.write.parquet("s3a://gold/table/")\nEOF'
expect_pass "editor heredoc contains commands" \
    $'cat <<\'PATCH\' | sed -n \'1,4p\'\n+ aws s3 cp ./out s3://gold/table/\n+ df.write.parquet("s3a://gold/table/")\nPATCH'
expect_pass "three harmless pipeline consumers" \
    "printf '%s' '$WRITE' | grep write | sed 's/write/read/'"
expect_pass "literal producer piped to grep remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | grep aws"
expect_pass "cat forwarding into grep remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | cat | grep aws"
expect_pass "tee output process substitution into grep remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | tee >(grep aws)"
expect_pass "cat output process substitution into grep remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | cat > >(grep aws)"
expect_pass "tee file stdin overrides pipeline before process shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | tee >(sh) < /dev/null"
expect_pass "tee file stdin overrides pipeline before downstream shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | tee < /dev/null | sh"
expect_pass "xargs converts pipeline input to argv, not shell stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | xargs sh"
expect_pass "xargs replacement into echo remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | xargs -I{} echo '{}'"
expect_pass "NUL xargs shell filename is not stdin payload" \
    "printf '%s\\0' 'aws s3 cp ./out s3://gold/table/' | xargs -0 sh"
expect_pass "assembled printf echo remains non-copy" \
    "printf '%s%s\\n' 'echo ' 'aws s3 cp ./out s3://gold/table/' | sh"
expect_pass "printf ignores args when format consumes none" \
    "printf 'safe\\n' 'aws s3 cp ./out s3://gold/table/' | sh"
expect_pass "printf percent q shell escapes copy text" \
    "printf '%q' 'aws s3 cp ./out s3://gold/table/' | sh"
expect_pass "safe literal command piped to shell" \
    "echo 'grep catalog notes.md' | sh"
expect_pass "echo escape decoding disabled before shell" \
    "echo -E '\\x61ws s3 cp ./out s3://gold/table/' | sh"
expect_pass "inline shell program does not consume outer stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'echo safe'"
expect_pass "earlier cat drains compound shell stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'cat >/dev/null; sh'"
expect_pass "process script cat drains stdin before later shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'python3 <(cat); sh'"
expect_pass "nested inline process shell drains stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'python3 <(sh -c \"cat >/dev/null\"); sh'"
expect_pass "nested process scripts drain stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'python3 <(python3 <(cat)); sh'"
expect_pass "process script drain prevents later output forwarding" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'python3 <(cat); cat' | sh"
expect_pass "inline shell discards stdout before downstream shell" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh -c 'cat >/dev/null' | sh"
expect_pass "file stdin overrides pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh < /dev/null"
expect_pass "closed stdin overrides pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh 0<&-"
expect_pass "producer stdout redirect overrides pipeline" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > /dev/null | sh"
expect_pass "producer stdout duplicated to stderr bypasses pipe" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' 1>&2 | sh"
expect_pass "here-string stdin overrides pipeline payload" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh <<< 'echo safe'"
expect_pass "kubectl exec without stdin forwarding does not consume producer" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec pod -- sh"
expect_pass "kubectl explicit false stdin does not consume producer" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec --stdin=false pod -- sh"
expect_pass "remote shell interactive flag is not kubectl stdin" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | kubectl exec pod -- sh -i"
expect_pass "single-quoted substitution is literal" \
    "grep '\$(aws s3 cp ./out s3://gold/table/)' notes.md"
expect_pass "process substitution input to grep remains prose" \
    "grep aws < <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')"
expect_pass "later file redirect overrides process stdin" \
    "sh < <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/') < /dev/null"
expect_pass "process stdin overrides dangerous pipeline" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' | sh < <(printf '%s\\n' 'echo safe')"
expect_pass "process substitution argument to cat remains prose" \
    "cat <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')"
expect_pass "shell explicit stdin leaves process path as argument" \
    "bash -s <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')"
expect_pass "python explicit stdin leaves process path as argument" \
    "python3 - <(printf '%s\\n' 'df.write.parquet(\"s3a://gold/table/\")')"
expect_pass "local process path is not remote kubectl script" \
    "kubectl exec pod -- sh <(printf '%s\\n' 'aws s3 cp ./out s3://gold/table/')"
expect_pass "quoted process substitution is literal" \
    "echo '<(aws s3 cp ./out s3://gold/table/)'"
expect_pass "output process substitution into grep remains prose" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(grep aws)"
expect_pass "later stdout file overrides process consumer" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(sh) > /dev/null"
expect_pass "nested xargs file stdin overrides process stdout" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(xargs -I{} sh -c '{}' < /dev/null)"
expect_pass "explicit fd1 file overrides process consumer" \
    "printf '%s\\n' 'aws s3 cp ./out s3://gold/table/' > >(sh) 1>/dev/null"
# shellcheck disable=SC2016
expect_pass "command substitution in shell comment is inactive" \
    'echo ok # $(aws s3 cp ./out s3://gold/table/)'
expect_pass "attached shell -c text is an invalid option, not a payload" \
    "bash -c'aws s3 cp ./out s3://gold/table/'"
expect_pass "quoted heredoc substitution is literal" \
    $'cat <<\'EOF\'\n$(aws s3 cp ./out s3://gold/table/)\nEOF'
expect_pass "escaped substitution in unquoted heredoc is literal" \
    $'cat <<EOF\n\\$(aws s3 cp ./out s3://gold/table/)\nEOF'
expect_pass "process substitution syntax in heredoc is literal" \
    $'cat <<EOF\n<(aws s3 cp ./out s3://gold/table/)\nEOF'
expect_pass "shell payload only echoes prose" \
    "sh -c 'echo '\"'\"'aws s3 cp ./out s3://gold/table/'\"'\"''"
expect_pass "shell noexec only syntax-checks payload" \
    "bash -n -c 'aws s3 cp ./out s3://gold/table/'"
expect_pass "clustered shell noexec only syntax-checks payload" \
    "bash -nc 'aws s3 cp ./out s3://gold/table/'"
expect_pass "named shell noexec only syntax-checks payload" \
    "bash -o noexec -c 'aws s3 cp ./out s3://gold/table/'"
expect_pass "shell noexec only syntax-checks heredoc" \
    $'bash -n <<\'EOF\'\naws s3 cp ./out s3://gold/table/\nEOF'
expect_pass "source process script only echoes prose" \
    "bash -c 'source <(printf \"%s\\n\" \"echo aws s3 cp ./out s3://gold/table/\")'"
expect_pass "source dev stdin executes only echo prose" \
    "printf '%s\\n' 'echo aws s3 cp ./out s3://gold/table/' | bash -c 'source /dev/stdin'"
expect_pass "out of range ANSI Unicode alone is harmless" \
    "echo \$'\\U00110000'"
expect_pass "ANSI-C escaped quote alone is harmless" \
    "echo \$'it\\'s safe'"
expect_pass "ANSI-C quoted copy text remains echo data" \
    "echo \$'aws s3 cp ./out s3://gold/table/'"
expect_pass "arithmetic shift alone is harmless" \
    'echo $((1<<2))'
expect_pass "python string literal write syntax is prose" \
    "python3 -c 'print(\"df.write.parquet(s3a://gold/table/)\")'"
expect_pass "python os system only echoes copy prose" \
    "python3 -c 'import os; os.system(\"echo aws s3 cp ./out s3://gold/table/\")'"
expect_pass "python subprocess shell list only echoes prose" \
    "python3 -c 'import subprocess; subprocess.run([\"echo aws s3 cp ./out s3://gold/table/\"], shell=True)'"
expect_pass "python subprocess args keyword only echoes prose" \
    "python3 -c 'import subprocess; subprocess.run(args=[\"echo\", \"aws s3 cp ./out s3://gold/table/\"])'"
expect_pass "python imported executor only echoes copy prose" \
    "python3 -c \"from subprocess import run; run('echo aws s3 cp ./out s3://gold/table/', shell=True)\""
expect_pass "python aliased os executor only echoes copy prose" \
    "python3 -c \"import os as o; o.system('echo aws s3 cp ./out s3://gold/table/')\""
expect_pass "python literal split argv only echoes copy prose" \
    "python3 -c \"import subprocess; subprocess.check_call('echo aws s3 cp ./out s3://gold/table/'.split())\""
expect_pass "python os execlp only echoes copy prose" \
    "python3 -c \"import os; os.execlp('echo', 'echo', 'aws s3 cp ./out s3://gold/table/')\""
expect_pass "python reassigned imported executor is inert" \
    "python3 -c 'import subprocess; subprocess.run = lambda *args, **kwargs: None; subprocess.run([\"aws\", \"s3\", \"cp\", \"./out\", \"s3://gold/table/\"])'"
expect_pass "python unrelated keyword string is not path" \
    "python3 -c 'df.write.parquet(\"/tmp/local\", mode=\"overwrite\" if \"s3a://gold/table/\" else \"append\")'"
expect_pass "python unrelated unpacked option is not path" \
    "python3 -c 'df.write.options(**{\"note\": \"s3a://gold/table/\"}).parquet(\"/tmp/local\")'"
expect_pass "python assigned path overwritten before write" \
    "python3 -c 'path = \"s3a://gold/table/\"; path = \"/tmp/local\"; df.write.parquet(path)'"
expect_pass "python named expression local path is allowed" \
    "python3 -c 'df.write.parquet(path := \"/tmp/local\")'"
expect_pass "python f-string local path is allowed" \
    "python3 -c 'path = \"/tmp/local\"; df.write.parquet(f\"{path}\")'"
expect_pass "python exec inherits overwritten local path" \
    "python3 -c 'path = \"s3a://gold/table/\"; path = \"/tmp/local\"; exec(\"df.write.parquet(path)\")'"
expect_pass "python exec inherits writer method local path" \
    "python3 -c 'save = df.write.parquet; exec(\"save(\\\"/tmp/local\\\")\")'"
expect_pass "python shadowed exec callable is inert" \
    "python3 -c 'exec = lambda code: None; exec(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'"
expect_pass "python shadowed eval callable is inert" \
    "python3 -c 'eval = lambda code: None; eval(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'"
expect_pass "python shadowed exec print alias is prose" \
    "python3 -c 'exec = print; exec(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'"
expect_pass "python shadowed eval print alias is prose" \
    "python3 -c 'eval = print; eval(\"df.write.parquet(\\\"s3a://gold/table/\\\")\")'"
expect_pass "python imported builtins exec safe payload" \
    "python3 -c 'from builtins import exec as invoke; invoke(\"print(\\\"safe\\\")\")'"
expect_pass "python concatenated argv unmanaged destination" \
    "python3 -c 'import subprocess; subprocess.run([\"aws\", \"s3\", \"cp\", \"./out\"] + [\"s3://unmanaged/table/\"])'"
expect_pass "python loop body local path is allowed" \
    "python3 -c 'for _ in [0]: path = \"/tmp/local\"; df.write.parquet(path)'"
expect_pass "python unused function write is nonexecuting" \
    "python3 -c 'def unused(): df.write.parquet(\"s3a://gold/table/\")'"
expect_pass "python uncalled assigned lambda is nonexecuting" \
    "python3 -c 'f = lambda: df.write.parquet(\"s3a://gold/table/\")'"
expect_pass "python uncalled instance method is nonexecuting" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\nJob()\''
expect_pass "python uninstantiated constructor is nonexecuting" \
    $'python3 -c \'class Job:\n    def __init__(self):\n        import os\n        os.system("aws s3 cp ./out s3://gold/table/")\''
expect_pass "python reassigned class method is inert" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\nJob.run = lambda self: None\nJob().run()\''
expect_pass "python overridden instance method is inert" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\njob = Job()\njob.run = lambda: None\njob.run()\''
expect_pass "python instance restore preserves class override" \
    $'python3 -c \'class Job:\n    def run(self):\n        df.write.parquet("s3a://gold/table/")\noriginal = Job.run\nJob.run = lambda self: None\njob = Job()\njob.run = original\nJob().run()\''
expect_pass "python warning option containing c safe payload" \
    "python3 -Wignore::DeprecationWarning -c 'print(\"safe\")'"
expect_pass "python implementation option containing c safe payload" \
    "python3 -Xtracemalloc -c 'print(\"safe\")'"
expect_pass "python call before definition cannot execute body" \
    $'python3 -c \'run()\ndef run(): df.write.parquet("s3a://gold/table/")\''
expect_pass "python reassigned function body is nonexecuting" \
    $'python3 -c \'def run():\n    df.write.parquet("s3a://gold/table/")\nrun = lambda: None\nrun()\''
expect_pass "python bound writer method local path is allowed" \
    "python3 -c 'save = df.write.parquet; save(\"/tmp/local\")'"
expect_pass "python chained bound writer method local path is allowed" \
    "python3 -c 'save = df.write.parquet; alias = save; alias(\"/tmp/local\")'"
expect_pass "python writer object alias is not callable" \
    "python3 -c 'writer = df.write; writer(\"s3a://gold/table/\")'"
expect_pass "python function resolves overwritten local global path" \
    $'python3 -c \'path = "s3a://gold/table/"\ndef run():\n    df.write.parquet(path)\npath = "/tmp/local"\nrun()\''
expect_pass "python function explicit argument overrides dangerous default" \
    $'python3 -c \'def run(path="s3a://gold/table/"):\n    df.write.parquet(path)\nrun("/tmp/local")\''
expect_pass "python function parameter shadows dangerous global" \
    $'python3 -c \'path = "s3a://gold/table/"\ndef run(path):\n    df.write.parquet(path)\nrun("/tmp/local")\''
expect_pass "python unresolved parameter clears stale global annotation" \
    $'python3 -c \'path = "s3a://gold/table/"\ndef run(path):\n    df.write.parquet(path)\nrun(str("/tmp/local"))\''
expect_pass "python function named local default is allowed" \
    $'python3 -c \'path = "/tmp/local"\ndef run(target=path):\n    df.write.parquet(target)\nrun()\''
expect_pass "python writer alias overwritten before call" \
    "python3 -c 'writer = df.write; writer = other; writer.parquet(\"s3a://gold/table/\")'"
expect_pass "python filename argument is not inline payload" \
    "python3 report.py '$WRITE'"
expect_pass "python module -c argument is not interpreter payload" \
    "python3 -m json.tool -c '$WRITE'"
expect_pass "python c payload takes precedence over heredoc stdin" \
    $'python3 -c \'print("safe")\' <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY'
expect_pass "python script file treats heredoc as data" \
    $'python3 report.py <<\'PY\'\ndf.write.parquet("s3a://gold/table/")\nPY'
expect_pass "nonzero fd here-string is not Python stdin" \
    "python3 - 3<<<'df.write.parquet(\"s3a://gold/table/\")'"
expect_pass "later file stdin overrides Python heredoc" \
    $'python3 <<\'PY\' < /dev/null\ndf.write.parquet("s3a://gold/table/")\nPY'
expect_pass "shell c payload takes precedence over heredoc stdin" \
    $'sh -c \'echo safe\' <<\'SH\'\naws s3 cp ./out s3://gold/table/\nSH'
expect_pass "shell script file treats heredoc as data" \
    $'sh ./safe.sh <<\'SH\'\naws s3 cp ./out s3://gold/table/\nSH'
expect_pass "quoted here-string-looking argument is prose" \
    "python3 report.py '<<<$WRITE'"
expect_pass "malformed grep quote does not block" \
    "grep '$WRITE"
expect_pass "malformed aws quote cannot execute" \
    'aws s3 cp ./out "s3://gold/table/'

printf '\nConsumer failure behavior\n'
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$TMP_ROOT/hooks/infrastructure" "$TMP_ROOT/hooks/lib"
cp "$HOOK" "$TMP_ROOT/hooks/infrastructure/catalog-guard.sh"
cp "$REPO_ROOT/hooks/lib/extract-json.py" "$TMP_ROOT/hooks/lib/extract-json.py"
MISSING_CLASSIFIER_COMMAND='printf safe'
MISSING_CLASSIFIER_PAYLOAD=$(make_payload "$MISSING_CLASSIFIER_COMMAND")
CONSUMER_CASES=$((CONSUMER_CASES + 1))
if assert_nonempty_extraction "missing classifier" "$MISSING_CLASSIFIER_PAYLOAD" "$MISSING_CLASSIFIER_COMMAND"; then
    MISSING_OUT=$(printf '%s' "$MISSING_CLASSIFIER_PAYLOAD" | bash "$TMP_ROOT/hooks/infrastructure/catalog-guard.sh" 2>&1)
    MISSING_EXIT=$?
    if [[ "$MISSING_EXIT" -eq 2 ]] && printf '%s' "$MISSING_OUT" | grep -q 'classification failed'; then
        record_pass "consumer: missing classifier fails closed (exit 2)"
    else
        record_fail "consumer: missing classifier fails closed" "got exit $MISSING_EXIT: ${MISSING_OUT:0:240}"
    fi
fi

MISSING_EXTRACTOR_ROOT=$(mktemp -d)
mkdir -p "$MISSING_EXTRACTOR_ROOT/hooks/infrastructure" "$MISSING_EXTRACTOR_ROOT/hooks/lib"
cp "$HOOK" "$MISSING_EXTRACTOR_ROOT/hooks/infrastructure/catalog-guard.sh"
cp "$CLASSIFIER" "$MISSING_EXTRACTOR_ROOT/hooks/lib/classify-catalog-command.py"
MISSING_EXTRACTOR_PAYLOAD=$(make_payload 'aws s3 cp ./out s3://gold/table/')
MISSING_EXTRACTOR_OUT=$(printf '%s' "$MISSING_EXTRACTOR_PAYLOAD" | bash "$MISSING_EXTRACTOR_ROOT/hooks/infrastructure/catalog-guard.sh" 2>&1)
MISSING_EXTRACTOR_EXIT=$?
if [[ "$MISSING_EXTRACTOR_EXIT" -eq 2 ]] && printf '%s' "$MISSING_EXTRACTOR_OUT" | grep -q 'Could not extract'; then
    record_pass "consumer: missing extractor fails closed (exit 2)"
else
    record_fail "consumer: missing extractor fails closed" "got exit $MISSING_EXTRACTOR_EXIT: ${MISSING_EXTRACTOR_OUT:0:240}"
fi
rm -rf "$MISSING_EXTRACTOR_ROOT"

EMPTY_OUT=$(printf '%s' '{"tool_input":{"command":""}}' | bash "$HOOK" 2>&1)
EMPTY_EXIT=$?
if [[ "$EMPTY_EXIT" -eq 2 ]] && printf '%s' "$EMPTY_OUT" | grep -q 'Could not extract'; then
    record_pass "consumer: empty extracted command fails closed (exit 2)"
else
    record_fail "consumer: empty extracted command fails closed" "got exit $EMPTY_EXIT: ${EMPTY_OUT:0:240}"
fi

MALFORMED_OUT=$(printf '%s' '{not-json' | bash "$HOOK" 2>&1)
MALFORMED_EXIT=$?
if [[ "$MALFORMED_EXIT" -eq 2 ]] && printf '%s' "$MALFORMED_OUT" | grep -q 'Could not extract'; then
    record_pass "consumer: malformed JSON fails closed (exit 2)"
else
    record_fail "consumer: malformed JSON fails closed" "got exit $MALFORMED_EXIT: ${MALFORMED_OUT:0:240}"
fi

if [[ "$EXTRACTION_CONTROLS" -eq "$CONSUMER_CASES" ]]; then
    record_pass "extraction control: $EXTRACTION_CONTROLS/$CONSUMER_CASES full-hook commands nonempty"
else
    record_fail "extraction control count" "$EXTRACTION_CONTROLS/$CONSUMER_CASES commands were nonempty"
fi

printf '\nResults: %d passed, %d failed\n' "$PASS" "$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
    printf 'Failed scenarios:\n'
    for name in "${FAILED_NAMES[@]}"; do
        printf '  - %s\n' "$name"
    done
    exit 1
fi
