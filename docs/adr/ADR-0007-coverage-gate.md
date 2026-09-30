# ADR-0007: Enforce line coverage in CI

- Status: accepted
- Date: 2026-09-30

## Decision

- Configure coverage for `src/fpga` with branch coverage disabled.
- Fresh `origin/main` measured 70.0% line coverage; CI enforces
  `fail_under = 67`, three percentage points below that baseline.
- Run pytest-cov explicitly in CI with
  `uv run pytest --cov --cov-report=term-missing:skip-covered`; keep coverage
  out of pytest `addopts` so developer runs remain opt-in.
- Keep `pytest-xdist`'s `-n auto` configuration; the coverage run supports it.

## Dependency review

- `pytest-cov` 7.1.0 makes total-coverage calculation consistent across report
  settings and handles sqlite `ResourceWarning` more reliably. The stable
  total supports this gate; the warning change needs no project-specific
  behavior or configuration.
- The lock refresh updated `google-auth` 2.59.0 to 2.59.1. Its only release
  note is mTLS support in `requests.Request` during token refresh and
  impersonation. FPGA-agent does not use that transport directly, so no
  FPGA-specific code change was needed.
- The resolver also updated the `sdk-check` transitive dependency `posthog`
  from 7.61.0 to 7.61.1. That patch stops `$mcp_tools_list` events from
  copying tool descriptors into `$mcp_response`; FPGA-agent does not emit
  those PostHog events, so no integration change was needed.
- `coverage` 7.16.2 is newly locked for pytest-cov. Its release fixes three
  coverage-reporting and dynamic-context issues; none requires changes beyond
  using the tool to measure the configured source.
