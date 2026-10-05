# Development

## Setup

```bash
uv sync --locked
python3 scripts/fetch_colibri.py   # pinned Colibri into third_party/ (gitignored)
```

## Verify

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright                      # strict mode; must be clean
env -u BASH_ENV -u "BASH_FUNC_gh%%" uv run pytest
env -u BASH_ENV -u "BASH_FUNC_gh%%" uv run pytest -m tools
uv run python scripts/check_shared_hooks.py
uv run --group sdk-check python scripts/check_plugin_load.py
uv run python scripts/verify_docs.py
uvx zizmor@1.30.1 .github/workflows   # only when workflows changed
```

Notes:

- Run pytest through `env -u BASH_ENV -u "BASH_FUNC_gh%%"` — Devin's
  exported `gh` shell function breaks the stub-gh tests otherwise.
- `tests/test_flows.py` (marker `tools`) needs the OSS CAD Suite and NVC
  on PATH; it runs the real toolchain on every bundled example and asserts
  the PNG renders and VCD captures exist.
- pytest runs `xdist -n auto`; use `-n 0` when debugging a single test.
- Device profiles under `src/fpga/devices/` are generated; regenerate with
  `scripts/extract_device_profiles.py`, never hand-edit.
- `plugins/fpga/hooks/scripts/_records.py` and `require_records.py` are
  shared-family canonical files verified by normalized-AST sha256
  (`scripts/check_shared_hooks.py`); a hash mismatch means the file was
  edited — do not edit them in this repo.
- `docker/image-digests.json` is written only by the publish workflow.

## Commits

`feat(scope): imperative summary`, ≤72 chars, English. No `git add .`,
no amends, no `--no-verify`, no force-push, no pushes to main.
