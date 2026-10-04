#!/usr/bin/env bash
# Digest lock PR sweep: merge stalled bot digest-lock PRs whose required
# checks are green, then dispatch post-merge verification on main for any
# recent lock merge that GitHub's event stream did not cover (bot merges
# do not fire push events). Runs from digest-lock-sweep.yml; extracted so
# tests can drive it through a gh stub (tests/test_digest_lock_sweep.py).
set -uo pipefail

# Lock PRs sometimes stay open with auto-merge armed and every
# required check green while GitHub's mergeability evaluation
# reports "blocked" indefinitely. Re-try the merge every 6 hours;
# the branch ruleset still gates it, so an unsatisfied PR cannot merge.
dispatch_post_merge=false
prs=$(gh pr list --repo "$GITHUB_REPOSITORY" --state open --limit 50 \
  --json number,headRefName \
  --jq '.[] | select(.headRefName | startswith("bot/update-image-digests-")) | .number')
if [ -z "$prs" ]; then
  echo "no open digest-lock PRs" | tee -a "$GITHUB_STEP_SUMMARY"
else
  for pr in $prs; do
    pr_url="https://github.com/$GITHUB_REPOSITORY/pull/$pr"
    state=$(gh api "repos/$GITHUB_REPOSITORY/pulls/$pr" --jq '.mergeable_state // "unknown"' || echo unknown)
    case "$state" in
      clean|blocked|behind|unstable)
        if gh pr merge --repo "$GITHUB_REPOSITORY" --squash --delete-branch "$pr"; then
          echo "merged $pr_url (was $state)" | tee -a "$GITHUB_STEP_SUMMARY"
          dispatch_post_merge=true
        else
          gh pr merge --repo "$GITHUB_REPOSITORY" --auto --squash --delete-branch "$pr" || true
          echo "$pr_url left open ($state; auto-merge armed)" | tee -a "$GITHUB_STEP_SUMMARY"
        fi
        ;;
      *)
        echo "$pr_url skipped (mergeable_state=$state)" | tee -a "$GITHUB_STEP_SUMMARY"
        ;;
    esac
  done
fi
# Bot merges do not fire push events, so a lock merge that landed
# outside a live publisher — a merge above, or an auto-merge
# armed by the publisher that completed after it exited — never
# triggers the post-merge workflows. Cover any recent lock merge
# that has no ci.yml dispatch since its merge; one run verifies main.
if [ "$dispatch_post_merge" != true ]; then
  cutoff=$(date -u -d '7 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  while IFS= read -r merged_at; do
    [ -n "$merged_at" ] || continue
    [ "$merged_at" \> "$cutoff" ] || continue
    runs=$(gh run list --repo "$GITHUB_REPOSITORY" --workflow ci.yml \
      --branch main --event workflow_dispatch \
      --created ">=$merged_at" --json databaseId --jq 'length' || echo 0)
    if [ "${runs:-0}" = "0" ]; then
      dispatch_post_merge=true
      break
    fi
  done < <(gh pr list --repo "$GITHUB_REPOSITORY" --state merged --limit 10 \
    --json headRefName,mergedAt \
    --jq '.[] | select(.headRefName | startswith("bot/update-image-digests-")) | .mergedAt')
fi
if [ "$dispatch_post_merge" = true ]; then
  gh workflow run ci.yml --repo "$GITHUB_REPOSITORY" --ref main || true
  gh workflow run locked-image-check.yml --repo "$GITHUB_REPOSITORY" --ref main || true
  echo "dispatched post-merge verification on main" | tee -a "$GITHUB_STEP_SUMMARY"
fi
