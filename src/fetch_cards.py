"""Fetch and cache YGOPRODeck card metadata."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from src.config import API_URL, CARD_CACHE_PATH, REQUEST_TIMEOUT_SECONDS, ensure_directories

logger = logging.getLogger(__name__)


def _load_cached_cards(cache_path: Path = CARD_CACHE_PATH) -> list[dict]:
    with cache_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected cached card payload to be a list, got {type(payload).__name__}.")
    return payload


def _save_cached_cards(cards: list[dict], cache_path: Path = CARD_CACHE_PATH) -> None:
    ensure_directories()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cards, handle, indent=2)


def fetch_cards(force_refresh: bool = False) -> list[dict]:
    """Return card metadata from cache or the YGOPRODeck API."""

    ensure_directories()
    if CARD_CACHE_PATH.exists() and not force_refresh:
        logger.info("Loading card metadata from cache: %s", CARD_CACHE_PATH)
        return _load_cached_cards()

    try:
        logger.info("Fetching card metadata from YGOPRODeck.")
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        cards = payload.get("data")
        if not isinstance(cards, list):
            raise ValueError("YGOPRODeck response did not contain a 'data' list.")
        _save_cached_cards(cards)
        logger.info("Saved %s cards to cache.", len(cards))
        return cards
    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        if CARD_CACHE_PATH.exists():
            logger.warning("Card fetch failed (%s). Falling back to cached metadata.", exc)
            return _load_cached_cards()
        raise RuntimeError(
            "Unable to fetch card metadata and no local cache is available. "
            "Run again when the YGOPRODeck API is reachable."
        ) from exc
