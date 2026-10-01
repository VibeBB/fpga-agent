## SBOM attestations

The image publish workflow generates and attests a package-level SPDX-2.3 SBOM
for the published digest with predicate type
`https://spdx.dev/Document/v2.3`, and records its URL as `sbom_attestation`.
File entries and relationships involving files are omitted to stay below the
16 MiB attestation limit. The full Syft SBOM is attached to the workflow run
as an artifact retained for 90 days.
Locked-image checks verify the attestation when present and warn when absent.
# fpga-tools image

`fpga-tools.Dockerfile` bundles every tool the gates call on Ubuntu 26.04
(see `THIRD_PARTY_NOTICES.md` and ADR-0002). Build and smoke-test it with:

```bash
docker build -f docker/fpga-tools.Dockerfile -t fpga-tools:dev .
docker run --rm --network none fpga-tools:dev python -m fpga doctor
```

The launcher uses the image named by `FPGA_TOOLS_IMAGE`, or the pin in
`plugins/fpga/tools-image.json` followed by the `fpga_tools` entry of
`docker/image-digests.json` after the published image digest is locked.
`.github/workflows/publish-fpga-images.yml` publishes
`ghcr.io/vibebb/fpga-tools` with a commit-specific `${sha}-tools` tag and a
`latest` tag, then smoke-tests every example. The digest lock is updated only
from the published image; do not record a local build digest. The build runs
the ULX3S example's full gates offline as a smoke test. External HDL such as
Colibri is not in the image; fetch it into the workspace with
`scripts/fetch_colibri.py` before running the gates.

Each published image receives GitHub build provenance. The lock records its
attestation URL, and locked-image checks verify it against this repository's
publisher workflow when present. Existing pins without attestation metadata
continue with a warning until the next publish.
