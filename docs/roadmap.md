# Roadmap

## Foundation

- [x] Create an independent public GakufuLayer repository.
- [x] Implement page-block preprocessing and synthetic-PDF tests in the local prototype.
- [x] Support metadata for one source language and multiple translation targets in the local prototype.
- [x] Publish initial preprocessing and language-metadata code to GitHub.
- [ ] Confirm and add a real open-source LICENSE (Apache-2.0 proposed).
- [ ] Inspect VSOPER code, dependencies, and score/translation assets before migration.

## Multilingual pipeline

- [ ] Extract source-language lyric segments and stable score positions.
- [ ] Define translation-provider and reviewed-text import interfaces.
- [ ] Port and test VSOPER's existing Japanese translation as one target adapter.
- [ ] Implement another source/target pairing and publish reviewed reference tests.
- [ ] Add source-language IPA, fonts and layout tests for CJK and RTL scripts.
- [ ] Place translated text as selectable PDF annotation layers.
- [ ] Add resumable blocks, validation and deterministic PDF assembly.

## Community readiness

- [ ] Verify reuse rights for every published example asset.
- [ ] Publish installation guide, contribution guidance, issue templates and CI results.
- [ ] Publish performance measurements against a permitted large-score fixture.
- [ ] Tag a release only after the documented functionality is tested.
- [ ] Prepare a factual Codex for Open Source application with maintainer activity and intended API-credit use.
