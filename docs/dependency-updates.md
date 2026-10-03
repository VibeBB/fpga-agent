# Dependency update review

Run the report locally with:

```bash
uv sync --locked
uv run --no-sync python scripts/check_dependency_updates.py \
  --markdown /tmp/fpga-dependencies.md \
  --json /tmp/fpga-dependencies.json
```

The report checks direct and locked PyPI dependencies, the uv pin, GitHub
Actions SHA pins, pinned `uvx` tools, Docker ARG release pins, the Ubuntu base
tag, `git clone --branch` pins inside workflows, and Python-version support.
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

The scheduled workflow writes its Markdown and JSON reports under the runner's
temporary directory, adds the report and run URL to the step summary, and
exposes outdated and unknown counts. Fetch failures are reported as unknown;
the tracking issue stays open until both counts are zero. Dependabot groups
GitHub Actions updates and applies a seven-day cooldown to Actions and Docker
updates.
