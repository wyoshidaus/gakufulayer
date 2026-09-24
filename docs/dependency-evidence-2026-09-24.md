# CI dependency evidence — 24 September 2026

This is a reproducible engineering audit of the installed Python environments,
not a legal determination, release approval, SPDX compliance certificate, or a
promise that future dependency resolution will match these versions.

Evidence: [successful run 36048394351](https://github.com/wyoshidaus/gakufulayer/actions/runs/36048394351).
Download the three dependency-inventory artifacts from that run to inspect
their package metadata, discovered license texts and SHA-256 digests. GitHub
retains these CI artifacts for 30 days.

| Environment | Python | Installed distributions | Automatic license-review flags |
| --- | --- | ---: | --- |
| Core only | 3.12.14 | 3 | 0 |
| Full PDF + tests | 3.12.14 | 9 | PyMuPDF AGPLv3/commercial license decision |
| Full PDF + tests | 3.10.21 | 13 | PyMuPDF license decision; setuptools 79.0.1 has an incomplete machine-readable license marker; GakufuLayer editable-install duplicate LICENSE alias (scanner issue fixed after this run) |

Installed direct runtime versions: pypdf 6.19.0 (core and full);
PyMuPDF 1.28.2 (full only). Python 3.10's full environment also
installs setuptools 79.0.1, whose [version-specific upstream LICENSE]
(https://github.com/pypa/setuptools/blob/v79.0.1/LICENSE)
contains an MIT-style permission notice. That upstream source is
independent evidence and should be archived with a pinned release;
do not silently rewrite raw distribution metadata in the inventory.

The duplicated editable-install short `LICENSE` warning was confirmed
against the installed `gakufulayer-0.1.0.dev0.dist-info/licenses/LICENSE`.
The scanner now recognizes that exact wheel path as an alias while preserving
warnings for independently missing `NOTICE` or other texts.

## What the evidence does and does not establish

The core isolated environment does not include PyMuPDF. Its observed installed
license metadata contains no automatic review flags in this CI run. This
supports the *technical* separation of the optional renderer; it does not
constitute a legal opinion on all possible ways of distributing the project.

The full environments contain PyMuPDF. Even when all installed license files
are discoverable and the tests pass, `release_cleared` remains false.
This is intentional: choosing AGPL-compliant distribution, a commercial
license, or a different rendering backend is a release-level decision.
The rights to scores, lyric texts, translations and user-supplied fonts are
separate from runtime dependency licensing.

CI inventories report installed Python distributions. They do **not** inventory
system-provided Noto fonts, an isolated PEP 517 build environment, operating
system libraries, or every vendored native dependency. They do not pin future
installation resolution, and the retained archives expire.

## Follow-up verification

Before a renderer release: choose the distribution model; audit and pin the
complete runtime and build dependencies; review third-party and bundled
license texts; decide corresponding-source and network-use obligations; verify
output producer/XMP notices and rights to shipped PDF/font assets. Keep
[issue #5](https://github.com/wyoshidaus/gakufulayer/issues/5) open until
the remaining checks are completed.
