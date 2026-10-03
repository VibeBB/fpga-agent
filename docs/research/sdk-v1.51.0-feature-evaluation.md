# OpenHands SDK v1.51.0 feature evaluation (fpga-agent)

Scope: `openhands-sdk`, `openhands-tools`, and any directly pinned OpenHands packages move from 1.50.1 to 1.51.0 (PyPI release 2026-10-03T07:38Z). The complete upstream range `v1.50.1..v1.51.0` was reviewed. uv moves to 0.12.22 in the same round.

Primary source: [OpenHands SDK v1.51.0 release](https://github.com/OpenHands/software-agent-sdk/releases/tag/v1.51.0).

## SDK 1.50.1 -> 1.51.0

| Upstream change | Decision | Evaluation |
| --- | --- | --- |
| #5151 agent-profiles: `tools` is the only tool control, selected from one server catalog | not adopted | VibeBB plugins keep their own tool contract (`.fpga.json` gates) and do not use SDK agent-profiles; no repo change. |
| #5449 agent-profiles: a profile can replace the agent's persona | not adopted | Persona/profile machinery is not used by the fpga plugin; agents delegate to `python -m fpga`. |
| #5450 loaded tools supply their system-prompt guidance (browser) | not adopted | Browser tool is not loaded by this plugin; guidance remains the plugin's Markdown agents/skills. |
| #5358 agent-profiles: delegated sub-agents stay within the profile's tools and MCP servers | not adopted | No SDK sub-agent delegation in this repo (delegation is a product feature via OpenHands, not Devin children). |
| #5406 agent-profiles: launch every agent through resolve and finalize | adopted implicitly | Internal launch path unification; plugin-load check (`scripts/check_plugin_load.py`) exercises the same path and passes under 1.51.0. |
| #5332 `prompt_cache_key` resolved via real provider for proxied models | adopted with the pin | Bug fix on the LLM path; benefits any proxied deployment without repo changes. |
| #5274 OpenRouter becomes a verified provider | adopted with the pin | Provider catalog addition; no constraint on existing providers. |
| #5412 send system+user classifier messages for direct-routing | adopted with the pin | Routing correctness fix; no repo surface. |
| #5434 deprecate `ACPAgentSettings.llm` so ACP agents keep their metrics LLM | adopted with the pin | Settings cleanup; this repo does not override ACP settings. |
| #5417 agent-server: resolve provider connection in `/switch_llm` | upstream image | Agent-server-only fix; this repository does not build or manage an agent-server image. |
| #1326 fix `find_dotenv` assertion error in local conversation | adopted with the pin | Local-conversation robustness fix on the path the plugin-load check exercises. |
| #5419 pydantic 2.12.5 -> 2.13.5 | lock-only | Picked up through `uv.lock` resolution within existing `pydantic>=2` constraint. |
| #4945, #5415 CI fixes (behavior-test comment, version-bump-prs failure surfacing) | upstream CI | Upstream repository CI only; nothing to adopt here. |
| #5425, #5428 TypeScript client dependency bumps | not applicable | This repository does not use the SDK TypeScript client. |
| #5397 stress-test run-slot fix | not applicable | Upstream test-only change. |
| #5470 release | not applicable | Release housekeeping. |

## Compatibility deferrals

MCP 2.x remains deferred: installed SDK metadata continues to require `fastmcp>=3.2.0,<4` (resolved `fastmcp-slim==3.4.7`), which caps `mcp<2.0`. Keep the existing deferral and its re-check policy; `scripts/dependency_update_deferrals.json` tracks `mcp` latest `2.3.0`. The `openhands-agent-server` image tag `1.51.0-python` is available upstream; no committed image lock is edited by this bump.
