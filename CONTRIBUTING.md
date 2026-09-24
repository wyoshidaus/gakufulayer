# Contributing to GakufuLayer

GakufuLayer is being built as a multilingual tool for preparing vocal scores. It currently ships only PDF preprocessing and language-selection metadata.

1. Open an issue before major changes and explain the input languages, output languages, and expected behavior.
2. Use a focused branch and include tests for each new behavior.
3. Test with generated PDFs or legally redistributable material, not commercial scores or unlicensed translations.
4. Run python -m pip install -e '.[dev]' and python -m pytest before a pull request.
5. For translation or pronunciation features, include source-language context, human-review requirements, and appropriate script or RTL test cases. Do not claim a language is supported until reviewed end-to-end tests exist.
6. Never commit API keys, private score libraries, user data, or material whose redistribution rights are unclear.

The maintainer has not yet finalized the project license. Contribution and redistribution terms must be settled before accepting external code contributions.
