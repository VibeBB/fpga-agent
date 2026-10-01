# AGENTS.md — VibeBB fpga-agent

Guidance for AI agents and humans working on this repository, the FPGA
sibling in the VibeBB OpenHands plugin family.

## Authoring rules

- Executable logic is Python 3.12 under `src/fpga/` (stdlib + pydantic v2
  + mcp). Agents, commands and skills under `plugins/fpga/` are Markdown
  and delegate every step to `python -m fpga` through
  `plugins/fpga/scripts/fpga_launcher.py`.
- The contract `<name>.fpga.json` is the source of truth. `*.fpga.pcf`,
  `*.fpga.lpf`, `*.fpga.cst`, `*.fpga-pinmap.*`, `*.fpga-report.*`,
  `sim-*.log`, `formal-*.log`, `observations/fpga/*.jsonl` and
  `intake/attachments/manifest.jsonl` are generated; never edit them by
  hand.
- Gates fail closed: missing tools, files or unparseable output are
  failures.
- Device profiles under `src/fpga/devices/` are generated from the open
  device databases by `scripts/extract_device_profiles.py`; regenerate,
  do not hand-edit.
- External HDL (e.g. Colibri, CERN-OHL-W-2.0) is referenced from a pinned
  checkout under `third_party/` (gitignored), never copied into the tree.
- Sibling cooperation is JSON artifacts in the workspace; never import a
  sibling's code and never edit a sibling's inputs (write an
  `fpga_request`).
- External tools run as subprocesses. Do not import GPL code. Downloaded
  tools are pinned by version and sha256 and listed in
  `THIRD_PARTY_NOTICES.md`.
- Programming hardware is host-only and human-confirmed; it is never a
  gate or MCP tool; the `deny-programming` hook denies it for agents.
- New dependencies or tools need an ADR under `docs/adr/`.

## Voice and commit policy

- Code, comments, docs, commit messages and PR text are English.
- Commit style: `feat(scope): imperative summary`, max 72 chars.
- PRs follow `.github/PULL_REQUEST_TEMPLATE.md`.

## Verification

```bash
uv sync --locked
python3 scripts/fetch_colibri.py
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
uv run python scripts/check_plugin_load.py
uv run python scripts/verify_docs.py
```

`tests/test_flows.py` (marker `tools`) runs only when the OSS CAD Suite
and NVC are on PATH. The `e2e` CI job builds
`docker/fpga-tools.Dockerfile` and runs those tests plus the full gates
of every example inside it with `--network none`.

Shared workflows are canonical across the family; change all 11 copies together and update `EXPECTED` in `scripts/check_shared_workflows.py`.

## CI/CD

Digest-lock PRs use `scripts/publish_image_pin_pr.sh`: the publisher
dispatches `ci.yml` and `workflow-lint.yml` on the lock branch, then polls
the authoritative required-check set for up to 30 minutes. Non-required
failures do not block publishing; a concluded required-check failure or a PR
closed without merge fails the job. A PR merged externally triggers the
existing post-merge main workflows. If required checks are still pending at
the deadline, the publisher arms squash auto-merge with branch deletion and
exits successfully.

SPDX SBOM generation prefers registry pulls, uses runner temporary storage,
and disables file metadata. The attested SBOM is package-level SPDX 2.3;
file entries and relationships involving files are omitted to stay below
16 MiB. The full Syft SBOM is attached to the workflow run as a 90-day
artifact.
