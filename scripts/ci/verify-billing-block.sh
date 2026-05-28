#!/usr/bin/env bash
set -euo pipefail

# Verifies that ALL failing CI checks on a PR failed solely due to
# GitHub Actions org-level billing failure (not real test failures).
#
# Usage: verify-billing-block.sh <owner> <repo> <pr-number>
# Exit 0 = billing-only failure confirmed (safe to use override)
# Exit 1 = real failure detected or verification failed

BILLING_ANNOTATION="The job was not started because recent account payments have failed or your spending limit needs to be increased."
MAX_DURATION_SECONDS=5

if [ $# -ne 3 ]; then
    echo "Usage: $0 <owner> <repo> <pr-number>"
    exit 1
fi

OWNER="$1"
REPO="$2"
PR="$3"

SHA=$(gh pr view "$PR" --repo "$OWNER/$REPO" --json headRefOid -q '.headRefOid')
if [ -z "$SHA" ]; then
    echo "FAIL: could not resolve head SHA for PR #$PR"
    exit 1
fi

echo "Checking PR #$PR ($OWNER/$REPO) at SHA $SHA"
echo "---"

CHECK_RUNS=$(gh api "repos/$OWNER/$REPO/commits/$SHA/check-runs" --paginate -q '.check_runs[]')
if [ -z "$CHECK_RUNS" ]; then
    echo "FAIL: no check runs found for SHA $SHA"
    exit 1
fi

TOTAL=0
BILLING_BLOCKED=0
REAL_FAILURE=0

while IFS= read -r run; do
    name=$(echo "$run" | jq -r '.name')
    status=$(echo "$run" | jq -r '.status')
    conclusion=$(echo "$run" | jq -r '.conclusion')
    started=$(echo "$run" | jq -r '.started_at')
    completed=$(echo "$run" | jq -r '.completed_at')
    annotation_text=$(echo "$run" | jq -r '.output.summary // ""')

    TOTAL=$((TOTAL + 1))

    if [ "$conclusion" = "success" ] || [ "$conclusion" = "skipped" ] || [ "$conclusion" = "neutral" ]; then
        echo "  PASS: $name ($conclusion)"
        continue
    fi

    if [ "$started" != "null" ] && [ "$completed" != "null" ]; then
        start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$started" +%s 2>/dev/null || date -d "$started" +%s 2>/dev/null || echo 0)
        end_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$completed" +%s 2>/dev/null || date -d "$completed" +%s 2>/dev/null || echo 0)
        duration=$((end_epoch - start_epoch))
    else
        duration=999
    fi

    if echo "$annotation_text" | grep -qF "$BILLING_ANNOTATION"; then
        is_billing="yes"
    else
        annotations=$(gh api "repos/$OWNER/$REPO/check-runs/$(echo "$run" | jq -r '.id')/annotations" -q '.[].message' 2>/dev/null || echo "")
        if echo "$annotations" | grep -qF "$BILLING_ANNOTATION"; then
            is_billing="yes"
        else
            is_billing="no"
        fi
    fi

    if [ "$is_billing" = "yes" ] && [ "$duration" -le "$MAX_DURATION_SECONDS" ]; then
        BILLING_BLOCKED=$((BILLING_BLOCKED + 1))
        echo "  BILLING: $name (${duration}s, annotation confirmed)"
    else
        REAL_FAILURE=$((REAL_FAILURE + 1))
        echo "  REAL FAILURE: $name (${duration}s, billing_annotation=$is_billing, conclusion=$conclusion)"
    fi
done < <(gh api "repos/$OWNER/$REPO/commits/$SHA/check-runs" --paginate -q '.check_runs[] | @json')

echo "---"
echo "Total checks: $TOTAL"
echo "Billing-blocked: $BILLING_BLOCKED"
echo "Real failures: $REAL_FAILURE"

if [ "$REAL_FAILURE" -gt 0 ]; then
    echo ""
    echo "FAIL: $REAL_FAILURE check(s) failed for non-billing reasons. Do NOT use the billing override."
    exit 1
fi

if [ "$BILLING_BLOCKED" -eq 0 ]; then
    echo ""
    echo "FAIL: no billing-blocked checks found. Nothing to override."
    exit 1
fi

echo ""
echo "PASS: all $BILLING_BLOCKED failing check(s) are billing-blocked. Override is safe."
exit 0
