# fpga-agent

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/VibeBB/fpga-agent)

VibeBB FPGA plugin for OpenHands (Software Agent SDK). It designs,
verifies and builds FPGA designs — HDL/RTL, testbenches, formal
properties, constraints, bitstreams — together with the sibling plugins
(`electrical-circuit-agent`, `firmware-agent`, `mechanical-agent`,
`wire-agent`, `UX-creator-agent`, `document-agent`, ...).

An FPGA contract `<name>.fpga.json` declares the device, top level,
sources, external HDL libraries, clocks, pins, build, simulations and
formal runs. Deterministic gates, all open-source tools, decide whether
the design is acceptable:

| gate | checks |
| --- | --- |
| `fpga.contract` | contract schema, device profile, family-specific output suffixes |
| `fpga.provenance` | external library files exist with SPDX headers matching the declared license |
| `fpga.pins` | user I/O of the package, config/JTAG pins acknowledged, I/O standards, pulls |
| `fpga.constraints` | PCF / LPF / CST matches the contract projection |
| `fpga.netlist_match` | every pin on its circuit net, voltages, no unconstrained connected pin |
| `fpga.lint` | NVC (VHDL) or Verilator (Verilog) |
| `fpga.sim.<id>` | NVC or Icarus Verilog testbench prints the expected lines |
| `fpga.formal.<id>` | SymbiYosys prove / BMC / cover of PSL or SVA properties |
| `fpga.synth` | Yosys (+ GHDL plugin for VHDL); synthesized ports equal the pinned ports |
| `fpga.pnr` | nextpnr (`ice40`, `ecp5`, `himbaechel` for Gowin) |
| `fpga.timing` | every declared clock meets its frequency |
| `fpga.utilization` | resources within budget |
| `fpga.bitstream` | IceStorm / Trellis / Apicula packer output with the family preamble; sha256 recorded |

Supported families: Lattice iCE40 and ECP5, Gowin GW1N and GW2A.
Bundled device profiles: `ice40-up5k-sg48`, `ecp5-lfe5u-25f-cabga381`,
`ecp5-lfe5u-85f-cabga381`, `gowin-gw1nr9c-qn88p`,
`gowin-gw2ar18c-qn88p`, `gowin-gw2a18c-pbga256`.

## Layout

- `src/fpga/` — contract models, device profiles, gates, CLI, MCP server.
- `plugins/fpga/` — the OpenHands plugin: agents (`fpga-architect`,
  `fpga-developer`, `fpga-review`), commands (`doctor`, `design`,
  `gates`, `pinmap`, `simulate`, `verify`, `build`), skills, hooks,
  launcher, `.mcp.json`.
- `examples/uart-echo-icebreaker/` — VHDL-2008 UART echo on iCE40 UP5K
  using the [Colibri](https://gitlab.com/colibri-cern/colibri) UART,
  linked to a circuit connectivity export.
- `examples/blinky-ulx3s/` — Verilog on ECP5 85F with an SVA proof.
- `examples/blinky-tangnano9k/` — VHDL on Gowin GW1NR-9 with a PSL proof.
- `examples/blinky-tangnano20k/` — Verilog on Gowin GW2AR-18C with an SVA proof.
- `examples/blinky-tangprimer20k/` — VHDL on Gowin GW2A-18C (PG256) with a PSL proof.
- `docker/fpga-tools.Dockerfile` — pinned Ubuntu 26.04 toolchain image.
- `docs/` — ADRs.

## Quick start

```bash
uv sync --locked
python3 scripts/fetch_colibri.py   # pinned Colibri into third_party/ (gitignored)
docker build -f docker/fpga-tools.Dockerfile -t fpga-tools:dev .
export FPGA_TOOLS_IMAGE=fpga-tools:dev
python3 plugins/fpga/scripts/fpga_launcher.py doctor
python3 plugins/fpga/scripts/fpga_launcher.py gates examples/uart-echo-icebreaker/uart-echo.fpga.json
```

Without an image the launcher runs on the host and every missing tool
fails its gate. CLI:
`fpga {doctor,validate,check,gates,constraints,pinmap,lint,sim,formal,build,program,request,profile}`.
MCP tools: `fpga_doctor`, `fpga_validate`, `fpga_check`, `fpga_gates`,
`fpga_constraints`, `fpga_pinmap_export`, `fpga_lint`, `fpga_sim`,
`fpga_formal`, `fpga_build`, `fpga_request`, `fpga_profile`.

## Programming a board

Programming is a human step on the host, never an agent or MCP action:

```bash
python -m fpga gates board.fpga.json          # must pass; records the bitstream sha256
python -m fpga program board.fpga.json --confirm-sha256 <sha256> --dry-run
python -m fpga program board.fpga.json --confirm-sha256 <sha256>
```

`program` refuses unless the last full gate report passed for the
current contract and the bitstream on disk still has the reported hash.

## Development

The workflow-lint check runs actionlint and zizmor. Releases verify CI,
workflow lint, and a remote plugin install smoke test before creating a
release.

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
uv run python scripts/check_plugin_load.py
uv run python scripts/verify_docs.py
```

### SBOM attestations

The tools-image publisher generates an SPDX-2.3 SBOM for the published digest,
attests it with predicate type `https://spdx.dev/Document/v2.3`, uploads the
artifact for 30 days, and records its URL in `sbom_attestation`. Locked-image
checks verify available SBOM attestations and warn when metadata is absent.

## License

BSD-3-Clause. Third-party tools and libraries are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## 日本語

OpenHands（Software Agent SDK）向けの VibeBB FPGA プラグイン。姉妹プラグイン
（`electrical-circuit-agent`、`firmware-agent`、`mechanical-agent`、
`wire-agent`、`UX-creator-agent`、`document-agent` など）と連携して、
FPGA 設計 — HDL/RTL、テストベンチ、形式プロパティ、制約、ビットストリーム — を
設計・検証・ビルドします。

FPGA コントラクト `<name>.fpga.json` でデバイス、トップレベル、ソース、
外部 HDL ライブラリ、クロック、ピン、ビルド、シミュレーション、形式検証を
宣言します。オープンソースツールによる決定論的なゲートが設計の合否を
判定します:

| ゲート | 検査内容 |
| --- | --- |
| `fpga.contract` | コントラクトのスキーマ、デバイスプロファイル、ファミリごとの出力サフィックス |
| `fpga.provenance` | 外部ライブラリファイルの存在と、宣言ライセンスと一致する SPDX ヘッダ |
| `fpga.pins` | パッケージのユーザー I/O、コンフィグ/JTAG ピンの確認、I/O 規格、プル抵抗 |
| `fpga.constraints` | PCF / LPF / CST がコントラクト投影と一致 |
| `fpga.netlist_match` | 全ピンが回路ネット上にあること、電圧、未制約の接続ピンなし |
| `fpga.lint` | NVC（VHDL）または Verilator（Verilog） |
| `fpga.sim.<id>` | NVC または Icarus Verilog のテストベンチが期待行を出力 |
| `fpga.formal.<id>` | PSL/SVA プロパティの SymbiYosys prove / BMC / cover |
| `fpga.synth` | Yosys（VHDL は GHDL プラグイン併用）。合成後ポートがピン固定ポートと一致 |
| `fpga.pnr` | nextpnr（`ice40`、`ecp5`、Gowin 用 `himbaechel`） |
| `fpga.timing` | 宣言された全クロックが周波数を満たすこと |
| `fpga.utilization` | リソースが予算内 |
| `fpga.bitstream` | IceStorm / Trellis / Apicula パッカー出力とファミリプリアンブル、sha256 記録 |

対応ファミリ: Lattice iCE40 / ECP5、Gowin GW1N / GW2A。
同梱デバイスプロファイル: `ice40-up5k-sg48`、`ecp5-lfe5u-25f-cabga381`、
`ecp5-lfe5u-85f-cabga381`、`gowin-gw1nr9c-qn88p`、
`gowin-gw2ar18c-qn88p`、`gowin-gw2a18c-pbga256`。

### 構成

- `src/fpga/` — コントラクトモデル、デバイスプロファイル、ゲート、CLI、MCP サーバー。
- `plugins/fpga/` — OpenHands プラグイン: エージェント
  （`fpga-architect`、`fpga-developer`、`fpga-review`）、コマンド
  （`doctor`、`design`、`gates`、`pinmap`、`simulate`、`verify`、`build`）、
  スキル、フック、ランチャー、`.mcp.json`。
- `examples/` — UART エコー（iCE40）と 4 種のブリンカー（ECP5/Gowin）の例。
- `docker/fpga-tools.Dockerfile` — ピン固定済み Ubuntu 26.04 ツールチェーンイメージ。
- `docs/` — ADR。

### クイックスタート

```bash
uv sync --locked
python3 scripts/fetch_colibri.py   # third_party/ へのピン固定取得（gitignored）
docker build -f docker/fpga-tools.Dockerfile -t fpga-tools:dev .
export FPGA_TOOLS_IMAGE=fpga-tools:dev
python3 plugins/fpga/scripts/fpga_launcher.py doctor
python3 plugins/fpga/scripts/fpga_launcher.py gates examples/uart-echo-icebreaker/uart-echo.fpga.json
```

イメージがない場合、ランチャーはホスト上で実行し、不足ツールは各ゲートで失敗します。

### ボードへの書き込み

プログラミングはホスト上の人間の操作であり、エージェントや MCP の操作ではありません:

```bash
python -m fpga gates board.fpga.json          # 必須。ビットストリームの sha256 を記録
python -m fpga program board.fpga.json --confirm-sha256 <sha256> --dry-run
python -m fpga program board.fpga.json --confirm-sha256 <sha256>
```

`program` は、最新のフルゲートレポートが現在のコントラクトに対して pass で、
ディスク上のビットストリームが記録されたハッシュと一致しない限り拒否します。

### 開発

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
uv run python scripts/check_plugin_load.py
uv run python scripts/verify_docs.py
```

workflow-lint チェックは actionlint と zizmor を実行します。リリースは
CI、ワークフローリント、リモートプラグインインストールのスモークテストを
確認してから作成されます。

### ライセンス

BSD-3-Clause。第三者ツールとライブラリは
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) に一覧があります。
