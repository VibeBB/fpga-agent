#!/usr/bin/env bash
# Upsert the tracking issue for a scheduled report workflow.
#
# Environment:
#   LABEL              issue label identifying the report stream (required)
#   LABEL_COLOR        label color (default: 0366d6)
#   LABEL_DESCRIPTION  label description (default: LABEL)
#   TITLE              issue title to find or create (required)
#   REPORT_MD          markdown file used for the issue body (required)
#   CLEAN              "1" when the report carries no actionable findings
#   CLOSE_COMMENT      comment posted when a clean report closes the issue
#   GITHUB_REPOSITORY  owner/repo (provided by Actions)
#
# Behavior: the canonical open report issue is edited when one exists
# (duplicates are closed); a new issue is created only when the report is
# not clean — a clean run with no open issue stays in the step summary
# instead of producing a create+close notification pair.
set -euo pipefail

: "${LABEL:?LABEL is required}"
: "${TITLE:?TITLE is required}"
: "${REPORT_MD:?REPORT_MD is required}"
: "${CLEAN:?CLEAN is required (0 or 1)}"
: "${CLOSE_COMMENT:?CLOSE_COMMENT is required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

# gh issue create fails with "could not add label" when the label does not
# exist (observed before the first report issue landed).
gh label create "$LABEL" --repo "$GITHUB_REPOSITORY" \
  --color "${LABEL_COLOR:-0366d6}" \
  --description "${LABEL_DESCRIPTION:-$LABEL}" --force

numbers=$(gh issue list --repo "$GITHUB_REPOSITORY" --state open \
  --label "$LABEL" \
  --search "in:title $TITLE" \
  --json number --jq '.[].number')
number=$(head -n1 <<< "$numbers")
# A second open report issue would silently fork the report stream; close
# extras so the canonical one keeps updating.
for extra in $(tail -n +2 <<< "$numbers"); do
  gh issue close "$extra" --repo "$GITHUB_REPOSITORY" \
    --comment "Duplicate of the canonical report issue #${number}." || true
done

if [ -n "$number" ]; then
  gh issue edit "$number" --repo "$GITHUB_REPOSITORY" --body-file "$REPORT_MD"
elif [ "$CLEAN" != "1" ]; then
  number=$(gh issue create --repo "$GITHUB_REPOSITORY" \
    --title "$TITLE" --label "$LABEL" --body-file "$REPORT_MD" | sed 's#.*/##')
else
  echo "Report is clean and no open \"$TITLE\" issue exists; skipping issue create."
fi

if [ "$CLEAN" = "1" ] && [ -n "$number" ]; then
  gh issue close "$number" --repo "$GITHUB_REPOSITORY" --comment "$CLOSE_COMMENT"
fi
