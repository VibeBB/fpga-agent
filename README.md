# fpga-agent

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/VibeBB/fpga-agent)

**VibeBB fpga-agent designs, checks and builds the programmable logic part of
a maker product — no FPGA experience needed.** You bring a product idea; the
plugin turns it into a verified FPGA bitstream and the paperwork (pin maps,
timing reports, waveform pictures) that proves it. It works hand in hand with
its sister plugins: the circuit agent places the chip on the board, the
firmware agent drives it, and UX-creator coordinates the whole build.

Site: <https://vibebb.org/>. License: BSD-3-Clause (VibeBB). Third-party tools
are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## What you give and what you get back

You give it a product brief and (optionally) the circuit connectivity export
the circuit plugin produces. You get back:

- a design contract `<name>.fpga.json` — the single source of truth for
  device, pins, clocks, sources, simulations and budgets;
- generated artifacts under `fpga-reports/`: the gate report
  (`*.fpga-report.json`/`.md`), the pin map for the circuit agent
  (`*.fpga-pinmap.json`/`.md`), constraint files, transcripts, and PNG
  renders (pin map, floorplan, utilization, timing, per-simulation waveform,
  and a report card) that the agent inspects with vision;
- a bitstream sha256 hash that a human can later use to program the board.

## How it decides pass/fail

Deterministic gates — never the model's opinion — decide:

| gate | checks |
| --- | --- |
| `fpga.contract` | contract schema, device profile, family-specific output suffixes |
| `fpga.provenance` | external library files exist with SPDX headers matching the declared license |
| `fpga.pins` | user I/O of the package, config/JTAG pins acknowledged, I/O standards, pulls |
| `fpga.constraints` | PCF / LPF / CST matches the contract projection |
| `fpga.netlist_match` | every pin on its circuit net, voltages, no unconstrained connected pin |
| `fpga.lint` | NVC (VHDL) or Verilator (Verilog) |
| `fpga.sim.<id>` | NVC or Icarus Verilog testbench prints the expected lines; VCD captured |
| `fpga.formal.<id>` | SymbiYosys prove / BMC / cover of PSL or SVA properties |
| `fpga.synth` | Yosys (+ GHDL plugin for VHDL); synthesized ports equal the pinned ports |
| `fpga.pnr` | nextpnr (`ice40`, `ecp5`, `himbaechel` for Gowin) |
| `fpga.timing` | every declared clock meets its frequency |
| `fpga.utilization` | resources within budget |
| `fpga.bitstream` | IceStorm / Trellis / Apicula packer output with the family preamble; sha256 recorded |

Everything the agent reasons about — decisions, stage impressions, vision
reviews — is recorded as an append-only evidence trail under
`observations/fpga/` and enforced by a Stop hook, so a session cannot finish
while it still owes a record.

## Working with sister plugins

Under UX-creator's Sister Liaison Protocol v2 the agent picks up jobs from
`liaison/*.ux-request.json`, reports its state via `fpga ux inbox`, and
answers with hashed artifacts, gate verdicts and record references via
`fpga ux respond`. Outbound changes to other plugins travel as
`*.fpga-request.json` requests (schema v2: hashed inputs + decision
references). The agent never edits a sibling's inputs.

## Getting started (AgentCanvas / OpenHands)

Install the plugin from `github:VibeBB/fpga-agent`, path `plugins/fpga`.
The launcher runs all tools inside the pinned `fpga-tools` Docker image —
it fails closed when the image cannot be resolved; it never silently falls
back to host tools. Programming a board stays a human step on the host
(`fpga program --confirm-sha256`), confirmed against the gate report's
bitstream hash.

Standalone quick start:

```bash
uv sync --locked
python3 scripts/fetch_colibri.py   # pinned Colibri into third_party/ (gitignored)
docker build -f docker/fpga-tools.Dockerfile -t fpga-tools:dev .
export FPGA_TOOLS_IMAGE=fpga-tools:dev
python3 plugins/fpga/scripts/fpga_launcher.py doctor
python3 plugins/fpga/scripts/fpga_launcher.py gates examples/uart-echo-icebreaker/uart-echo.fpga.json
```

## Limits

- Open toolchain only: Lattice iCE40/ECP5, Gowin GW1N/GW2A; bundled profiles
  `ice40-up5k-sg48`, `ecp5-lfe5u-25f-cabga381`, `ecp5-lfe5u-85f-cabga381`,
  `gowin-gw1nr9c-qn88p`, `gowin-gw2ar18c-qn88p`, `gowin-gw2a18c-pbga256`.
  No vendor tools, no other families.
- Single-corner timing, no power estimation (see
  [docs/improvement-notes.md](docs/improvement-notes.md)).
- The agent never programs hardware; generated artifacts are protected from
  hand edits by hooks.
- Records and renders are advisory evidence; gate verdicts stay the only
  pass/fail authority.

## Repository layout

- `src/fpga/` — contract models, device profiles, gates, renders, records,
  liaison, CLI, MCP server.
- `plugins/fpga/` — the OpenHands plugin: agents (`fpga-architect`,
  `fpga-developer`, `fpga-review`), commands (`doctor`, `design`, `gates`,
  `pinmap`, `simulate`, `verify`, `build`, `render`, `liaison`, `records`),
  skills, hooks, launcher, `.mcp.json`.
- `examples/` — a UART echo on iCE40 plus blinky designs on ECP5 and Gowin
  boards.
- `docker/fpga-tools.Dockerfile` — pinned Ubuntu 26.04 toolchain image.
- `docs/` — the full documentation tree; start at
  [docs/README.md](docs/README.md).

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
uv run python scripts/check_plugin_load.py
uv run python scripts/verify_docs.py
```

The workflow-lint check runs actionlint and zizmor. Releases verify CI,
workflow lint, and a remote plugin install smoke test before creating a
release. See [docs/development.md](docs/development.md).

### SBOM attestations

The tools-image publisher generates an SPDX-2.3 SBOM for the published digest,
attests it with predicate type `https://spdx.dev/Document/v2.3`, uploads the
artifact for 30 days, and records its URL in `sbom_attestation`. Locked-image
checks verify available SBOM attestations and warn when metadata is absent.

## License

BSD-3-Clause. Copyright VibeBB.

## 日本語

**VibeBB fpga-agent は、メーカー製品のプログラマブルロジック部分を、FPGA の
専門知識なしに設計・検証・ビルドします。** あなたが持ち込むのは製品アイデア。
プラグインは検証済みの FPGA ビットストリームと、それを裏付ける資料
（ピンマップ、タイミングレポート、波形画像）を返します。姉妹プラグインと
連携して動きます: 回路エージェントがチップを基板に配置し、ファームウェア
エージェントがそれを駆動し、UX-creator が全体を調整します。

サイト: <https://vibebb.org/>。ライセンス: BSD-3-Clause（VibeBB）。

### 渡すもの・返ってくるもの

製品ブリーフと（任意で）回路プラグインが出力する回路接続エクスポートを渡します。
返ってくるのは:

- 設計コントラクト `<name>.fpga.json` — デバイス、ピン、クロック、ソース、
  シミュレーション、予算の唯一の正典。
- `fpga-reports/` 配下の生成物 — ゲートレポート（`*.fpga-report.json`/`.md`）、
  回路エージェント向けピンマップ（`*.fpga-pinmap.json`/`.md`）、制約ファイル、
  トランスクリプト、そしてエージェントがビジョンで確認する PNG レンダリング
  （ピンマップ、フロアプラン、使用率、タイミング、シミュレーションごとの波形、
  レポートカード）。
- 後で人間がボードに書き込む際に使うビットストリームの sha256 ハッシュ。

### 合否の決め方

モデルの意見ではなく、決定論的なゲートが判定します（表は英語節と同じゲート
一覧）。エージェントが検討した内容 — 決定、ステージ印象、ビジョンレビュー —
は `observations/fpga/` 配下の追記専用ログとして残り、Stop フックが未記録の
セッション終了を拒否します。

### 姉妹プラグインとの連携

UX-creator の Sister Liaison Protocol v2 のもと、`liaison/*.ux-request.json`
の仕事を `fpga ux inbox` で確認し、ハッシュ済み成果物・ゲート判定・記録参照を
`fpga ux respond` で返します。他プラグインへの変更依頼は `*.fpga-request.json`
（v2: ハッシュ済み入力 + 決定記録参照）として送ります。兄弟の入力を直接編集
することはありません。

### 始め方（AgentCanvas / OpenHands）

`github:VibeBB/fpga-agent`、パス `plugins/fpga` からインストールします。
ランチャーはすべてのツールをピン固定の `fpga-tools` Docker イメージ内で
実行し、イメージが解決できない場合はフェイルクローズします — ホスト側
ツールへの暗黙のフォールバックはありません。ボードへの書き込みは常に
ホスト上の人間の操作（`fpga program --confirm-sha256`）で、ゲートレポートの
ビットストリームハッシュとの突き合わせが必須です。

### 制約

- オープンツールチェーンのみ: Lattice iCE40/ECP5、Gowin GW1N/GW2A。
  同梱プロファイルは `ice40-up5k-sg48`、`ecp5-lfe5u-25f-cabga381`、
  `ecp5-lfe5u-85f-cabga381`、`gowin-gw1nr9c-qn88p`、`gowin-gw2ar18c-qn88p`、
  `gowin-gw2a18c-pbga256`。ベンダーツール・他ファミリは対象外。
- シングルコーナーのタイミングのみ、消費電力推定なし。
- エージェントはハードウェアに一切書き込みません。生成物はフックが手編集
  から保護します。
- 記録とレンダリングは助言的な証拠であり、合否の権限はゲート判定のみに
  あります。

### ライセンス

BSD-3-Clause。Copyright VibeBB。第三者ツールとライブラリは
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) に一覧があります。
