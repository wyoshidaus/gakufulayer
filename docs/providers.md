# Translation providers

GakufuLayer keeps translation providers outside the PDF engine.

## Contract

A provider receives ordered `TranslationRequest` objects and returns `Translation` records in the same order. The request includes a stable segment ID, source text, source language and target language.

The core interface deliberately contains no API key, HTTP client or vendor-specific field. This makes cloud APIs, local models and human-reviewed imports interchangeable at the domain-model boundary.

## Reviewed text

`ReviewedTextProvider` is the first implemented adapter. It requires text and reviewer metadata supplied by the caller and performs no network access. It demonstrates that GakufuLayer can run its multilingual workflow without requiring a paid translation service.

Machine-translation adapters will be added separately and must document:
- supported source/target languages;
- provider/model version where available;
- privacy and data-transfer implications;
- review expectations;
- failure and retry behavior.

Provider support never implies linguistic quality for every accepted language tag.
