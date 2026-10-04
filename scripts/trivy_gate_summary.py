#!/usr/bin/env python3
"""Render the fixable CRITICAL/HIGH findings from a Trivy SARIF report as
a markdown table on stdout.

Usage: trivy_gate_summary.py [SARIF_PATH] — the publish workflow appends
the output to $GITHUB_STEP_SUMMARY when the Trivy gate fails so the
offending rules are reviewable without downloading artifacts.
"""

from __future__ import annotations

import json
import sys
from typing import Any, cast


def _list_of_dicts(node: dict[str, Any], *path: str) -> list[dict[str, Any]]:
    current: Any = node
    for key in path:
        if not isinstance(current, dict):
            return []
        current = cast(dict[str, Any], current).get(key)
    if not isinstance(current, list):
        return []
    return [
        cast(dict[str, Any], item) for item in cast(list[Any], current) if isinstance(item, dict)
    ]


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else "trivy-image.sarif"
    with open(path, encoding="utf-8") as fh:
        data: Any = json.load(fh)
    document = cast(dict[str, Any], data if isinstance(data, dict) else {})
    rules: dict[str, dict[str, Any]] = {}
    for run in _list_of_dicts(document, "runs"):
        for rule in _list_of_dicts(run, "tool", "driver", "rules"):
            rules[str(rule.get("id") or "")] = rule
    rows: list[tuple[str, str, str, str]] = []
    for run in _list_of_dicts(document, "runs"):
        for result in _list_of_dicts(run, "results"):
            rid = str(result.get("ruleId") or "?")
            rule = rules.get(rid) or {}
            properties = rule.get("properties")
            cvss = ""
            if isinstance(properties, dict):
                cvss = str(cast(dict[str, Any], properties).get("security-severity") or "")
            level = str(result.get("level") or "")
            message_node = result.get("message")
            message = ""
            if isinstance(message_node, dict):
                message = str(cast(dict[str, Any], message_node).get("text") or "")
            message = " ".join(message.split()).replace("|", "\\|")[:160]
            rows.append((rid, cvss, level, message))
    if rows:
        print("### Trivy gate: fixable CRITICAL/HIGH findings\n")
        print("| rule | severity (CVSS) | level | detail |")
        print("|---|---|---|---|")
        for rid, cvss, level, message in rows:
            print(f"| {rid} | {cvss} | {level} | {message} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
