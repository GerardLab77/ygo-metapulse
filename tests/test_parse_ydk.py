from pathlib import Path

import pytest

from src.parse_ydk import parse_ydk_file


def test_parse_ydk_sections_and_duplicates(tmp_path: Path) -> None:
    deck_path = tmp_path / "sample.ydk"
    deck_path.write_text(
        "\n".join(
            [
                "#created by unit test",
                "#main",
                "100",
                "100",
                "200",
                "#extra",
                "300",
                "!side",
                "400",
                "400",
                "",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_ydk_file(deck_path)

    assert parsed["main"] == {100: 2, 200: 1}
    assert parsed["extra"] == {300: 1}
    assert parsed["side"] == {400: 2}


def test_parse_ydk_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    deck_path = tmp_path / "comments.ydk"
    deck_path.write_text(
        "\n".join(
            [
                "#created by unit test",
                "",
                "#main",
                "#custom comment",
                "123",
                "",
                "#extra",
                "#another comment",
                "456",
                "!side",
                "",
                "789",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_ydk_file(deck_path)

    assert parsed["main"] == {123: 1}
    assert parsed["extra"] == {456: 1}
    assert parsed["side"] == {789: 1}


def test_parse_ydk_raises_on_invalid_card_id(tmp_path: Path) -> None:
    deck_path = tmp_path / "invalid.ydk"
    deck_path.write_text(
        "\n".join(["#main", "not-an-id"]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid card ID"):
        parse_ydk_file(deck_path)
