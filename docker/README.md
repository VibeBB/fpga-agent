# fpga-tools image

`fpga-tools.Dockerfile` bundles every tool the gates call on Ubuntu 26.04
(see `THIRD_PARTY_NOTICES.md` and ADR-0002). Build and smoke-test it with:

```bash
docker build -f docker/fpga-tools.Dockerfile -t fpga-tools:dev .
docker run --rm --network none fpga-tools:dev python -m fpga doctor
```

The launcher uses the image named by `FPGA_TOOLS_IMAGE`, or the
`fpga_tools` entry of `docker/image-digests.json` once a published digest
is recorded. The build runs the ULX3S example's full gates offline as a
smoke test. External HDL such as Colibri is not in the image; fetch it
into the workspace with `scripts/fetch_colibri.py` first.
