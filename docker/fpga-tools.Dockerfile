ARG UV_VERSION=0.12.21
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ubuntu:26.04 (resolute)
FROM ubuntu:26.04@sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78

ARG DEBIAN_FRONTEND=noninteractive
ARG IMAGE_REVISION=unknown
ARG OSS_CAD_SUITE_RELEASE=2026-09-30
ARG OSS_CAD_SUITE_ASSET=oss-cad-suite-linux-x64-20260930.tgz
ARG OSS_CAD_SUITE_SHA256=9e50078dd84062bb78b19cc27a2185b9d37f8cd3d80c03242ec6d85044895fc1
ARG NVC_VERSION=1.23.0
ARG NVC_ASSET=nvc_1.23.0-1_amd64_ubuntu-26.04.deb
ARG NVC_SHA256=deda7ffc97b04301f0dbf5e16614e0e6537ba8a292d3d11502675a3514ba995a

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
# The suite's bin/ is appended (never `source environment`) so the fpga
# virtualenv's Python stays first on PATH.
ENV PATH="/opt/fpga/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/oss-cad-suite/bin"
ENV PYTHONPYCACHEPREFIX=/tmp/fpga-pycache

LABEL org.opencontainers.image.source="https://github.com/VibeBB/fpga-agent" \
      org.opencontainers.image.licenses="BSD-3-Clause" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      fpga.oss-cad-suite.release="${OSS_CAD_SUITE_RELEASE}" \
      fpga.nvc.version="${NVC_VERSION}"

COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install --no-install-recommends -y \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# OSS CAD Suite (Yosys, GHDL plugin, nextpnr, IceStorm, Trellis, Apicula,
# SymbiYosys, solvers, Icarus, Verilator, openFPGALoader). Every tool keeps
# its own license under /opt/oss-cad-suite/license and runs as a subprocess.
RUN curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/oss-cad-suite.tgz \
        "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_SUITE_RELEASE}/${OSS_CAD_SUITE_ASSET}" \
    && echo "${OSS_CAD_SUITE_SHA256}  /tmp/oss-cad-suite.tgz" | sha256sum --check \
    && tar -xzf /tmp/oss-cad-suite.tgz -C /opt \
    && rm -f /tmp/oss-cad-suite.tgz \
    && rm -rf /opt/oss-cad-suite/examples \
    && mkdir -p /usr/share/doc/oss-cad-suite \
    && printf '%s\n' \
        "source=https://github.com/YosysHQ/oss-cad-suite-build" \
        "release=${OSS_CAD_SUITE_RELEASE}" \
        "sha256=${OSS_CAD_SUITE_SHA256}" \
        "licenses=/opt/oss-cad-suite/license" \
        > /usr/share/doc/oss-cad-suite/SOURCE

# NVC VHDL simulator, GPL-3.0-or-later, checksum-pinned Ubuntu 26.04 package.
RUN curl --fail --location --silent --show-error \
        --retry 5 --retry-delay 10 --retry-all-errors \
        --output /tmp/nvc.deb \
        "https://github.com/nickg/nvc/releases/download/r${NVC_VERSION}/${NVC_ASSET}" \
    && echo "${NVC_SHA256}  /tmp/nvc.deb" | sha256sum --check \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install --no-install-recommends -y /tmp/nvc.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/nvc.deb \
    && mkdir -p /usr/share/doc/nvc-release \
    && printf '%s\n' \
        "source=https://github.com/nickg/nvc" \
        "version=${NVC_VERSION}" \
        "sha256=${NVC_SHA256}" \
        "license=GPL-3.0-or-later" \
        > /usr/share/doc/nvc-release/SOURCE

WORKDIR /opt/fpga
COPY pyproject.toml uv.lock .python-version README.md LICENSE ./
COPY src ./src
RUN uv python install 3.12 \
    && uv sync --locked --no-dev --no-group sdk-check \
    && python -m fpga --help >/dev/null

# Smoke test: the full flow of a bundled example without network access.
COPY examples/blinky-ulx3s /tmp/smoke
RUN python -m fpga doctor \
    && python -m fpga gates /tmp/smoke/blinky.fpga.json >/tmp/smoke.json \
    && rm -rf /tmp/smoke /tmp/smoke.json /tmp/fpga-pycache

WORKDIR /work
