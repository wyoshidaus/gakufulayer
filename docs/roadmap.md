# Roadmap

## Foundation

- [x] Create an independent public GakufuLayer repository.
- [x] Implement page-block preprocessing and synthetic-PDF tests in the local prototype.
- [x] Support metadata for one source language and multiple translation targets in the local prototype.
- [x] Publish initial preprocessing and language-metadata code to GitHub.
- [x] Adopt Apache License 2.0 for newly authored GakufuLayer code.
- [x] Audit VSOPER's translation-unit validation and port its transaction semantics.
- [ ] Finish auditing VSOPER's PDF and score-specific assets/dependencies before further migration.

## Multilingual pipeline

- [ ] Extract source-language lyric segments and stable score positions.
- [x] Define provider-neutral translation interfaces and an offline reviewed-text adapter.
- [x] Port and test the VSOPER translation-unit validation/commit protocol without a fixed target language.
- [ ] Connect a real translation provider; the ported protocol does not translate by itself.
- [ ] Implement another source/target pairing and publish reviewed reference tests.
- [ ] Add source-language IPA, fonts and layout tests for CJK and RTL scripts.
- [x] Render reviewed, explicitly positioned multilingual text as selectable PDFs and optional OCG groups.
- [ ] Detect valid score-relative placement automatically and validate collision with notation.
- [x] Reassemble independently preprocessed page blocks and verify selected source-page mapping with synthetic PDF tests.
- [ ] Benchmark this assembly pipeline on an authorized full-length opera and add visual QC for image-only source pages.
- [ ] Add resumable blocks, validation and deterministic PDF assembly.

## Community readiness

- [ ] Verify reuse rights for every published example asset.
- [ ] Publish installation guide, contribution guidance, issue templates and CI results.
- [ ] Publish performance measurements against a permitted large-score fixture.
- [x] Separate the permissively licensed core install from the optional PyMuPDF PDF renderer.
- [ ] Complete PyMuPDF distribution, network-use and PDF producer metadata due diligence (issue #5) before releasing.
- [ ] Tag a release only after the documented functionality is tested.
- [ ] Prepare a factual Codex for Open Source application with maintainer activity and intended API-credit use.
