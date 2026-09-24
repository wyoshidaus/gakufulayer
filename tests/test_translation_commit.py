import json
from pathlib import Path

from gakufulayer.translation_commit import (
    commit_translation,
    parse_ready,
    validate_translation,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def ready(path: Path) -> Path:
    return write(
        path,
        "seg-1|M|Guten Abend.\n"
        "seg-2|O|Ja, gewiß.\n"
        "seg-3|?|Komm zu mir.\n",
    )


def test_japanese_translation_commit_preserves_source_order(tmp_path):
    source = ready(tmp_path / "TU001.ready.txt")
    output = write(
        tmp_path / "ja.txt",
        "seg-2|はい、たしかに。\n"
        "seg-1|こんばんは。\n"
        "seg-3|こちらへ来て。\n",
    )
    passed = tmp_path / "TU001.ja.passed.json"

    result = commit_translation(
        source,
        output,
        passed,
        source_language="de",
        target_language="ja",
    )

    assert result["status"] == "passed"
    payload = json.loads(passed.read_text(encoding="utf-8"))
    assert payload["target_language"] == "ja"
    assert [x["source_ref"] for x in payload["groups"]] == [
        "seg-1", "seg-2", "seg-3"
    ]


def test_same_protocol_supports_english_target(tmp_path):
    source = ready(tmp_path / "TU002.ready.txt")
    output = write(
        tmp_path / "en.txt",
        "seg-1|Good evening.\n"
        "seg-2|Yes, certainly.\n"
        "seg-3|Come to me.\n",
    )
    passed = tmp_path / "TU002.en.passed.json"

    result = commit_translation(
        source,
        output,
        passed,
        source_language="de",
        target_language="en",
    )

    assert result["status"] == "passed"
    assert json.loads(passed.read_text(encoding="utf-8"))["target_language"] == "en"


def test_partial_output_is_not_committed(tmp_path):
    expected = parse_ready(ready(tmp_path / "TU003.ready.txt"))
    report, groups = validate_translation(
        expected, "seg-1|訳1\nseg-2|訳2\ntruncated"
    )
    assert report["status"] == "failed"
    assert report["completed_ids"] == ["seg-1", "seg-2"]
    assert report["missing_ids"] == ["seg-3"]
    assert [x["source_ref"] for x in groups] == ["seg-1", "seg-2"]


def test_committed_result_is_immutable_by_default(tmp_path):
    source = ready(tmp_path / "TU004.ready.txt")
    output = write(
        tmp_path / "ja.txt",
        "seg-1|訳1\nseg-2|訳2\nseg-3|訳3\n",
    )
    passed = tmp_path / "TU004.ja.passed.json"

    first = commit_translation(
        source, output, passed, source_language="de", target_language="ja"
    )
    before = passed.read_text(encoding="utf-8")
    write(output, "seg-1|変更\nseg-2|変更\nseg-3|変更\n")
    second = commit_translation(
        source, output, passed, source_language="de", target_language="ja"
    )

    assert first["status"] == "passed"
    assert second["status"] == "already_committed"
    assert passed.read_text(encoding="utf-8") == before
