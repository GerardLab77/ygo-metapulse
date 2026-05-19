from pathlib import Path

from src import ingest


def test_select_deck_files_prefers_real_decks(tmp_path: Path, monkeypatch) -> None:
    decks_dir = tmp_path / "decks"
    decks_dir.mkdir()
    (decks_dir / "sample_demo.ydk").write_text("#main\n100\n", encoding="utf-8")
    (decks_dir / "real_event_top8.ydk").write_text("#main\n200\n", encoding="utf-8")

    monkeypatch.setattr(ingest, "DECKS_DIR", decks_dir)

    selected_files, deck_mode = ingest._select_deck_files()

    assert deck_mode == "real"
    assert [path.name for path in selected_files] == ["real_event_top8.ydk"]
