"""Application configuration and path management."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DECKS_DIR = DATA_DIR / "decks"
DECK_METADATA_DIR = DATA_DIR / "deck_metadata"
DB_PATH = DATA_DIR / "ygo_metapulse.db"
CARD_CACHE_PATH = RAW_DIR / "cards_cache.json"
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php?misc=yes"
REQUEST_TIMEOUT_SECONDS = 30


def ensure_directories() -> None:
    """Create the project data directories if they do not already exist."""

    for path in (DATA_DIR, RAW_DIR, DECKS_DIR, DECK_METADATA_DIR):
        path.mkdir(parents=True, exist_ok=True)


ensure_directories()
