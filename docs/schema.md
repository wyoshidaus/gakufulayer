# Annotation schema

The first language-independent domain model is implemented in `src/gakufulayer/annotations.py`.

A source lyric segment is stored once. Each translation is keyed independently by target language, while pronunciation belongs to the source language.

~~~json
{
  "segment_id": "seg-0001",
  "source_text": "Guten Abend",
  "source_language": "de",
  "source_page": 12,
  "translations": {
    "ja": {
      "language": "ja",
      "text": "こんばんは",
      "status": "reviewed",
      "provider": null,
      "reviewer": "reviewer-name"
    },
    "en": {
      "language": "en",
      "text": "Good evening",
      "status": "needs_review",
      "provider": "provider-name",
      "reviewer": null
    }
  },
  "pronunciation": {
    "language": "de",
    "text": "...",
    "system": "IPA"
  }
}
~~~

This schema intentionally does not embed translation-provider API details. Provider adapters will translate between external services and these internal records. A human-reviewed import can therefore use the same model as an automated provider.

Coordinates and layout geometry will be added when lyric extraction and score alignment are implemented.
