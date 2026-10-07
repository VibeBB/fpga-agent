# Dependency update review

Run the report locally with:

```bash
uv sync --locked
uv run --no-sync python scripts/check_dependency_updates.py \
  --markdown /tmp/fpga-dependencies.md \
  --json /tmp/fpga-dependencies.json
```

The report checks direct and locked PyPI dependencies, the uv pin, GitHub
Actions SHA pins (including subpath actions such as
`github/codeql-action/upload-sarif`, resolved to the owning repository),
pinned `uvx` tools, Docker ARG release pins, the Ubuntu base
tag, `git clone --branch` pins inside workflows, and Python-version support.
Direct-download pins in workflows are tracked too: the sha256-pinned
actionlint tarball and zizmor wheel in `workflow-lint.yml`, and tool
`version:` inputs on actions (the Trivy version given to
`aquasecurity/trivy-action` and `aquasecurity/setup-trivy`).
Review candidates against upstream release notes and compatibility with the
FPGA gates. Regenerate `uv.lock` with uv; do not edit it by hand.

Workflow `git clone --branch` pins are treated as a `git-clone` surface and
each ref is compared against the upstream repo's latest semver tag, so a new
release of the pinned CISOfy/lynis checkout in `container-audit.yml` surfaces
in the weekly report.

These Dockerfile surfaces require manual review before changing:

- `OSS_CAD_SUITE_ASSET` and `OSS_CAD_SUITE_SHA256` must match the selected
  OSS CAD Suite release asset and its upstream checksum.
- `NVC_ASSET` and `NVC_SHA256` must match the selected NVC release asset and
  its upstream checksum.
- The Ubuntu base-image digest is a security pin. Review the immutable digest
  against the supported `26.04` tag; do not update it from a local build or an
  unverified mirror.

The report checks the OSS CAD Suite date-tag and NVC release-tag candidates
but cannot validate their platform-specific asset names or checksums.
Deferrals and review dates are tracked in
`scripts/dependency_update_deferrals.json`; a deferred candidate still needs
an owner to revisit it by the listed date.

## Current deferrals

| Surface | Name | Latest | Re-check | Reason |
| --- | --- | --- | --- | --- |
| pypi | mcp | 2.3.0 | 2027-04-01 | `openhands-sdk` 1.53.0 -> `fastmcp<4` -> `fastmcp-slim` requires `mcp>=1.24.0,<2.0`; mcp 2.x cannot coexist with the SDK pin. |

| docker-arg | OSS_CAD_SUITE_RELEASE | 2026-10-03 | 2027-01-03 | Vendored python2.7/3.11 site-packages carry 6 upstream CVEs waived in `.trivyignore`; re-scan on every suite bump. |

## Decisions — 2026-10-03 round

| Component | Change | Decision | Reason |
| --- | --- | --- | --- |
| openhands-sdk / openhands-tools | 1.50.1 -> 1.51.0 | adopted | Per-commit review in `research/sdk-v1.51.0-feature-evaluation.md`; no agent-profile/persona features adopted (plugin keeps its `.fpga.json` contract). |
| uv | 0.12.21 -> 0.12.22 | adopted | Bug-fix release (relock hash verification, workspace default groups); no repo-visible behavior change; CPython 3.12.15 ships via `uv python install` on rebuild. |
| OSS CAD Suite | 2026-10-01 -> 2026-10-03 | adopted | Newest dated release with the linux-x64 asset published; sha256 computed from the downloaded tarball (`41b1e1c6…`). `.trivyignore` waivers stay until the publish-gate Trivy scan re-verifies the new image. |
| anchore/sbom-action | stays v0.24.3 | no-op | Already pinned at `66cbf4b` (# v0.24.3); nothing to change. |
| ruff | stays 0.16.10 | no-op | `>=0.16` already resolved to the latest 0.16.10 in `uv.lock`. |
| mcp | stays `>=1.29,<2` | deferred | `fastmcp<4` constraint in openhands-sdk 1.52.0 still caps `mcp<2.0`; deferral refreshed to latest 2.3.0. |

## Decisions — 2026-10-05 round (SDK 1.52.0)

| Component | Change | Decision | Reason |
| --- | --- | --- | --- |
| openhands-sdk / openhands-tools | 1.51.0 -> 1.52.0 | adopted | Per-commit review in `research/sdk-v1.52.0-feature-evaluation.md`; everything repo-facing adopted implicitly or not applicable (bug fixes + agent-server/TS-client housekeeping, no plugin-surface change). |
| mcp | stays `>=1.29,<2` | deferred | `fastmcp<4` constraint in openhands-sdk 1.52.0 still caps `mcp<2.0`; deferral reason refreshed to cite 1.52.0. |

## Decisions — 2026-10-07 round (SDK 1.53.0)

| Component | Change | Decision | Reason |
| --- | --- | --- | --- |
| openhands-sdk / openhands-tools | 1.52.0 -> 1.53.0 | adopted | Per-commit review in `research/sdk-v1.53.0-feature-evaluation.md`; everything repo-facing adopted implicitly or not applicable (one skills-scan fix lands with the pin; canvas-extension icon, release CI and docs/test sweeps carry no plugin-surface change). |
| mcp | stays `>=1.29,<2` | deferred | `fastmcp<4` constraint in openhands-sdk 1.53.0 still caps `mcp<2.0`; deferral reason refreshed to cite 1.53.0. |

## Decisions — 2026-10-04 round (GitHub Actions latest-state wave)

| Component | Change | Decision | Reason |
| --- | --- | --- | --- |
| actions/cache | v4.3.0 -> v6.1.0 | adopted | v4's Node20 runtime was deleted 2026-09-23 and forced onto node24; v6 is the ESM line the rest of the family already pins. SHA `55cc8345…`. |
| uv | 0.12.22 -> 0.12.23 | adopted | Patch release; keeps `required-version`, Dockerfile `UV_VERSION`, and the setup-uv `version:` input in lockstep. |
| CPython | 3.12/3.13 -> 3.14 adopted, 3.15 canary | adopted | Latest stable minor is 3.14.x (3.15 lands 2026-10-09). Matrix gains a 3.14 leg plus a `3.15` experimental leg gated at step level (`::warning::` annotation, not a gate failure). `fastuuid`/`PyO3 0.26` already fails 3.15 — that is the canary working. |
| actions/setup-node / python surfaces | `python-version:`/`node-version:`/`.python-version`/Dockerfile `uv venv`/`python3.x` now monitored | adopted | Dep-checker coverage review found these pins unmonitored; `check_python_versions` now scans every workflow and the dotfile. |
| codeql-action | new shared `codeql.yml` (actions + python) | adopted | Advanced config analyses both languages; requires repo-level "default setup" to be disabled or the upload is rejected — tracked outside this file. |

The scheduled workflow writes its Markdown and JSON reports under the runner's
temporary directory, adds the report and run URL to the step summary, and
exposes outdated and unknown counts. Fetch failures are reported as unknown;
the tracking issue is only created or kept open while either count is
nonzero; a clean run edits/closes an existing issue and otherwise writes
just the step summary. Dependabot groups
GitHub Actions updates and applies a seven-day cooldown to Actions and Docker
updates.
