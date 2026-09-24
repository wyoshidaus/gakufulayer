# Contributing to GakufuLayer

GakufuLayer is being built as a multilingual tool for preparing vocal scores. It currently ships PDF preprocessing, multilingual translation-result validation, reviewed-text imports and rendering of reviewed, pre-positioned translation overlays.

1. Open an issue before major changes and explain the input languages, output languages, and expected behavior.
2. Use a focused branch and include tests for each new behavior.
3. Test with generated PDFs or legally redistributable material, not commercial scores or unlicensed translations.
4. Run `python -m pip install -e '.[pdf,dev]'` and `python -m pytest` before a pull request. The base `python -m pip install -e .` installs only the core package.
5. For translation or pronunciation features, include source-language context, human-review requirements, and appropriate script or RTL test cases. Do not claim a language is supported until reviewed end-to-end tests exist.
6. Never commit API keys, private score libraries, user data, or material whose redistribution rights are unclear.

GakufuLayer's original code is Apache-2.0 licensed. Contributions are submitted under that license unless expressly agreed otherwise. Third-party scores, lyrics, translations and fonts are subject to separate rights; only provide assets with verified redistribution permission. The PDF renderer is an opt-in PyMuPDF extra (AGPLv3 or commercial terms); see [dependency-licensing.md](docs/dependency-licensing.md) and issue #5 before distributing a combined application or deploying a hosted service.
