# Operations

## Launcher-side verification

`FPGA_VERIFY_ATTESTATION` accepts `auto` (the default), `require`, or `off`.
Before pulling a lock-provided image, and on every `prewarm`, the launcher
uses `gh attestation verify` with the lock entry and publisher workflow.
`auto` prints one note and skips for an image override, missing attestation,
missing `gh`, or failed `gh auth status`; once verification starts, failure
or timeout prevents the pull. `require` makes skip conditions errors, while
`off` never verifies. Ordinary invocations do not re-verify a locally
present image, and `--warn` doctor paths never verify.

## Container hardening

Three layers were adopted after a comparative evaluation of Lynis,
`docker build --check`, Trivy, Grype, Dockle, and hadolint:

- **Dockerfile lint** (`dockerfile-lint` job in `ci.yml`): hadolint
  v2.15.1 via `hadolint-action` v3.5.0 plus `docker build --check`
  (BuildKit built-in). `.hadolint.yaml` allows only docker.io and
  ghcr.io registries and waives DL3008 (exact deb pins rot when archives
  drop them; downloaded tools are already version+sha256 pinned).
- **Image scan on publish** (`publish-fpga-images.yml`): Trivy v0.75.0
  via `trivy-action` v0.36.0 then scans the pushed digest for
  CRITICAL/HIGH fixable vulnerabilities, secrets, and misconfiguration —
  a full JSON report first (always produced, even when the gate fails),
  then the gated SARIF scan (`exit-code 1`) uploaded to code scanning
  (`category: trivy-fpga-tools`). Only after every gate passes does the
  `Promote :latest` step retag the digest to `:latest` via
  `docker buildx imagetools create`, so a failing image never serves
  `:latest`. The action is SHA-pinned and `version:` is explicit — the
  March 2026 Trivy supply-chain compromise made both non-negotiable.
- **Weekly audit** (`container-audit.yml`, Mondays 03:32 UTC): pulls the
  pinned digest from `docker/image-digests.json`, re-scans with a fresh
  vulnerability DB (new CVEs against the frozen image), runs the Docker
  CIS compliance report, runs an informational in-image Lynis 3.1.7
  audit (cloned at tag `3.1.7` then checked out detached at the pinned
  commit `2e99f92265760b73fd6b139868eb8d4116624030`), aggregates
  `container-hardening.json` (artifact), and
  edits/creates a "Container hardening report" issue. The issue closes
  automatically when fixable HIGH/CRITICAL findings reach zero. The
  Lynis Hardening Index is recorded as a trend metric only — its
  denominator shifts with container-skipped tests, so it never gates.
  The CIS aggregator walks `Results` recursively for `MisconfSummary`
  nodes and fails the step when zero checks were evaluated, so dead
  telemetry cannot masquerade as coverage. The plain-CLI CIS scan reuses
  a weekly `actions/cache` Trivy DB (`TRIVY_CACHE_DIR` under
  `$RUNNER_TEMP`).

Not adopted, with reasons: `lynis audit dockerfile` (~6 greps, frozen
since 2018, subset of hadolint, hardening index always 1);
Dockle (v0.4.15 stale; its CIS-derived checks are covered by Trivy's
`--compliance docker-cis` report); Grype (equivalent for the SBOM path,
kept as fallback); checkov (redundant third linter); `cisofy/lynis`
Docker image (does not exist — Lynis runs from a pinned git clone);
non-root USER enforcement and HEALTHCHECK enforcement (CI tools images —
deferred policy decisions).

Changelog evaluation for the adopted pins is in the introducing PR.
Suppressions: `.hadolint.yaml` waivers above; `.trivyignore` holds
time-boxed finding IDs — entries must carry an `exp:` date and a
rationale line here when added.

The uv-managed CPython's bundled `pip` payload (vendored urllib3,
msgpack, setuptools — never invoked; dependencies install via `uv` and
the shipped venv is pip-less) is stripped in the `uv python install`
layer, so the publish gate stays clean without `.trivyignore` waivers.

The first publish-gate run against the pushed digest (2026-10-03)
surfaced 9 HIGH findings — 6 unique CVEs — all inside the
OSS CAD Suite's vendored `python2.7`/`python3.11` site-packages
(`Flask` 2.1.2, `Werkzeug` 2.3.7, `pip` 19.2.3, `setuptools` 41.2.0 and
65.5.0). The pinned release (`OSS_CAD_SUITE_RELEASE=2026-10-03`) still
vendors the same interpreters, so no in-repo upgrade can clear them and
nothing in the image invokes Flask/Werkzeug or the vendored
pip/setuptools; the IDs carry `.trivyignore` waivers expiring 2027-01-03
and are re-verified by the publish-gate Trivy scan on every suite bump
(see `scripts/dependency_update_deferrals.json`).
fpga-tools is the only published image — there is no second image left
unscanned.

The weekly audit runs Lynis as container root (`--user 0`) with the
committed `docker/lynis-container.prf` profile, which skips tests that
are inapplicable inside a container (kernel/systemd/mounts/storage/
network/PAM/accounting are governed by the runtime flags below, not the
image fs). The profile keeps the Hardening Index and suggestion list to
image-actionable items; remaining suggestions are fixed in the
Dockerfile (`UMASK 027` in login.defs) or silenced only with a
documented reason.

`fpga_launcher.py` applies the runtime-hardening flags the container
profile defers to: `--network none`, `--user uid:gid`,
`--cap-drop ALL`, `--security-opt no-new-privileges`. A `--read-only`
root filesystem stays an optional hardening for callers that supply
tmpfs for tools that need scratch space.

### CIS baseline

The Trivy CIS compliance scan reports `DS-0002` (image runs as root) and
`DS-0026` (no `HEALTHCHECK`) on every tools image. Both are waived with
`exp:` entries in `.trivyignore`: these are CI build/tool containers, not
deployed services — workflows that need a non-root UID already run the
image with `docker run --user`, and batch tooling has no health endpoint
to probe. The waivers renew or get re-fixed by Dockerfile changes when
they lapse.

## Local verification

pytest selects subsets directly for a faster local check — `-k <expr>`,
a test path, or `-n 0` to disable the default `-n auto` workers:

```bash
uv run pytest -q tests/test_gates.py
uv run pytest -q -k synth
uv run pytest -q -n 0 tests/test_gates.py::test_loads
```

Run the full `uv run pytest -q` before submitting.

Local `fpga-tools` builds can reuse the CI-warmed registry buildcache; it is
a public `buildcache` tag, so no GHCR login is needed:

```bash
docker buildx build --load \
  -f docker/fpga-tools.Dockerfile -t fpga-tools:local \
  --cache-from type=registry,ref=ghcr.io/vibebb/fpga-tools:buildcache \
  .
```

## CI runner network auditing

Every job in every workflow starts with `step-security/harden-runner` in
audit-only mode (the pinned v2.21.1 step is kept byte-identical across the
family's shared workflows). It observes network egress without blocking
requests; per-run insights are available in the GitHub Actions job
summary.

## Digest-lock PR verification

The publisher dispatches `ci.yml` and `workflow-lint.yml` on the lock branch — skipped when a pull_request run already covers the PR head SHA, since the required checks would run twice on identical content — then polls the authoritative required-check set for up to 15 minutes. Non-required failures do not block publishing; a concluded required-check failure or a PR closed without merge fails the job. A PR merged externally triggers the existing post-merge main workflows without waiting for their results. If required checks remain pending at the deadline, the publisher arms squash auto-merge with branch deletion and exits successfully so branch protection can complete the merge. When the merge later lands — either via armed auto-merge or via the `digest-lock-sweep.yml` retry — the sweep's own merge dispatches `ci.yml` and `locked-image-check.yml` on main, closing the post-merge verification gap left by token merges suppressing push triggers.

`release.yml` accepts a `dry_run` input that rehearses a release without
writing anything: the bump job computes the would-be version with
`bump_version.py --dry-run`, checks the tag is free, emits HEAD as the
release SHA, and the downstream verify/install-smoke/build jobs still
run against it while tag and release creation are skipped. The
bump-version state machine — version resolution, tag check, direct push,
and the self-approving + dispatched-checks + auto-merge fallback PR — lives
in `scripts/release_bump.sh` (the workflow step is a thin wrapper) and is
covered by `tests/test_release_bump.py` (stubbed `gh`, local git remotes).

`publish-fpga-images.yml` accepts a `dry_run` dispatch input that rehearses
the publish: the image builds into the local daemon and the Trivy gate,
SBOM chain, measurement, and smoke checks still run against it, but nothing
is pushed, promoted (`:latest`), attested, locked, or dispatched, and no
SARIF reaches code scanning. The run summary lists every skipped step.

The verify job runs pytest through `scripts/structural_coverage.py run`,
which enforces `[tool.coverage.report] fail_under` (statement+branch) and
the C0, C1, decision, C2, MC/DC and boundary floors in
`[tool.vibebb-coverage]` (see [test-coverage.md](test-coverage.md) and
ADR-0011, which supersedes the ADR-0007 line-coverage gate).

SPDX generation prefers the GHCR registry source, writes temporary data under
the runner's temporary directory, and disables file metadata. The publisher
removes file entries and relationships involving files to produce the
package-level SPDX-2.3 SBOM. A guard reports disk space and the attested SBOM
size after transformation and fails above 16 MiB; the full Syft SBOM is
uploaded as a 90-day workflow-run artifact.

## Scheduled hygiene

`ghcr-tag-retention.yml` runs weekly and deletes orphaned `<sha>-tools`
tags from the fpga-tools package — failed publishes push a per-sha tag
that is never promoted, locked, or attested. A tag is only removed when
it is older than 14 days, its digest is not the one pinned by
`docker/image-digests.json`, and no build-provenance attestation exists
for the digest; `workflow_dispatch` offers a `dry_run` report mode.
CodeQL (python) is analyzed by GitHub's default code-scanning setup in
repository Settings — an in-repo `codeql.yml` must not be added, since
Code Scanning rejects SARIF uploads from advanced configurations while
default setup is enabled.

## Python canary promotion policy

The `3.15` canary leg in `ci.yml` is advisory: step-level
`continue-on-error` converts its failure into a `::warning::` signal so a
forward-incompatible interpreter never blocks the gate chain. Promote it
to a required matrix leg only when all of these hold:

1. The interpreter is a stable release — release candidates and earlier
   pre-releases stay advisory.
2. Every required dependency publishes wheels carrying the new ABI tag.
   The blockers seen so far are `cadquery-ocp-novtk` (no `cp315` wheels)
   and PyO3-based transitive pins such as `fastuuid` via the OpenHands
   SDK. The leg detects the landing itself: it goes green once wheels
   exist.
3. Three consecutive green runs on main — weekly or push-triggered runs
   with no canary `::warning::` in their logs.

Promotion moves `3.15` into the required version list and drops the
`continue-on-error`/`::warning::` reporting step; record the adoption in
`docs/dependency-updates.md` where that file exists, otherwise in this
section. A regression after promotion is handled like any main CI
failure — the leg does not silently revert to advisory.

## Settings-level posture (recorded decisions)

The following live in repository Settings rather than code; they are
intentional for the solo-maintainer bot-merge workflow and are recorded
here so audits do not re-flag them:

- Branch protection does not require approving reviews, code owners, or
  "apply to administrators": every merge is performed by automation
  (digest-lock, version-bump, and Devin PRs), so required approvers would
  only add friction to a pipeline that already gates on the required-check
  set. OpenSSF Scorecard reports this as Branch-Protection 3 and
  Code-Review 0; that is the recorded trade-off, not an oversight.
- The Dependency graph must stay enabled for `dependency-review.yml` to
  evaluate pull requests.
- `release.yml` is dispatch-only; run it once with `dry_run=true` before
  the first real release to rehearse bump, verify, and install-smoke
  without creating a GitHub release.
