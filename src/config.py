"""Application configuration and path management."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DECKS_DIR = DATA_DIR / "decks"
DECK_METADATA_DIR = DATA_DIR / "deck_metadata"
TOURNAMENT_DATA_DIR = DATA_DIR / "tournament_decks" / "ygoprodeck"
TOURNAMENT_DECKS_DIR = TOURNAMENT_DATA_DIR / "decks"
TOURNAMENT_DECK_METADATA_DIR = TOURNAMENT_DATA_DIR / "deck_metadata"
YGOPRODECK_IMPORT_DIR = DATA_DIR / "imports" / "ygoprodeck_tournaments"
YGOPRODECK_MANUAL_YDK_DIR = YGOPRODECK_IMPORT_DIR / "manual_ydk"
YGOPRODECK_IMPORT_REPORTS_DIR = YGOPRODECK_IMPORT_DIR / "reports"
YGOPRODECK_IMPORT_TEMPLATE_PATH = YGOPRODECK_IMPORT_DIR / "import_manifest_template.csv"
DB_PATH = DATA_DIR / "ygo_metapulse.db"
CARD_CACHE_PATH = RAW_DIR / "cards_cache.json"
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes"
YGOPRODECK_TOURNAMENT_CATEGORY_URL = "https://ygoprodeck.com/category/format/tournament%20meta%20decks"
REQUEST_TIMEOUT_SECONDS = 30


def ensure_directories() -> None:
    """Create the project data directories if they do not already exist."""

    for path in (
        DATA_DIR,
        RAW_DIR,
        DECKS_DIR,
        DECK_METADATA_DIR,
        TOURNAMENT_DECKS_DIR,
        TOURNAMENT_DECK_METADATA_DIR,
        YGOPRODECK_MANUAL_YDK_DIR,
        YGOPRODECK_IMPORT_REPORTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


ensure_directories()
