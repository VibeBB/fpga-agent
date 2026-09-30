# ADR-0008: Publish FPGA tools image and lock its digest

## Status

Accepted

## Context

The FPGA gates depend on a native toolchain that is too large and platform
specific to reproduce reliably through host package installation. Rebuilding
the image at use time also makes tool versions vary with the base registry and
download sources.

## Decision

Publish `docker/fpga-tools.Dockerfile` as
`ghcr.io/vibebb/fpga-tools`, tagging each build with its source commit and
maintaining a digest lock for the plugin launcher and repository checks.
Only a digest returned by the publishing workflow may update the lock; local
builds are for verification and never become the recorded pin.

## Consequences

The image workflow verifies the published digest with the launcher and every
example before updating the repository and plugin lock files. Scheduled
locked-image checks exercise the pinned image, and the image-tools measurement
record documents the tool commands and versions in that image.
