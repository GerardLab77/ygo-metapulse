"""Generate illustrative sample decklists from fetched card metadata."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.config import DECKS_DIR, DECK_METADATA_DIR, ensure_directories

SAMPLE_NOTES = "Illustrative sample data generated from local card metadata for portfolio demo purposes."

COMMON_MAIN_FILLERS = [
    "Ash Blossom & Joyous Spring",
    "Effect Veiler",
    "Infinite Impermanence",
    "Nibiru, the Primal Being",
    "Droll & Lock Bird",
    "Called by the Grave",
    "Crossout Designator",
    "Triple Tactics Talent",
    "Forbidden Droplet",
    "Pot of Prosperity",
]

COMMON_SIDE_FILLERS = [
    "Cosmic Cyclone",
    "Evenly Matched",
    "Artifact Lancea",
    "Book of Eclipse",
    "Lightning Storm",
    "Harpie's Feather Duster",
    "Solemn Judgment",
    "Droll & Lock Bird",
    "Nibiru, the Primal Being",
    "Forbidden Droplet",
]

COMMON_EXTRA_FILLERS = [
    "Linkuriboh",
    "Relinquished Anima",
    "I:P Masquerena",
    "Knightmare Phoenix",
    "Knightmare Unicorn",
    "S:P Little Knight",
    "Accesscode Talker",
    "Number 41: Bagooska the Terribly Tired Tapir",
    "Abyss Dweller",
    "Divine Arsenal AA-ZEUS - Sky Thunder",
]


@dataclass(frozen=True)
class SampleDeckSpec:
    slug: str
    metadata: dict[str, str]
    archetype_terms: tuple[str, ...]
    preferred_main: tuple[str, ...]
    preferred_extra: tuple[str, ...]
    preferred_side: tuple[str, ...]


def make_sample_spec(
    *,
    slug: str,
    event_name: str,
    event_date: str,
    placement: str,
    player: str,
    archetype: str,
    archetype_terms: tuple[str, ...],
    preferred_main: tuple[str, ...],
    preferred_extra: tuple[str, ...],
    preferred_side: tuple[str, ...] = tuple(COMMON_SIDE_FILLERS),
) -> SampleDeckSpec:
    """Create a sample deck specification with standard metadata fields."""

    return SampleDeckSpec(
        slug=slug,
        metadata={
            "event_name": event_name,
            "event_date": event_date,
            "placement": placement,
            "player": player,
            "archetype": archetype,
            "format": "TCG Advanced",
            "source_url": f"https://example.com/{slug}",
            "notes": SAMPLE_NOTES,
        },
        archetype_terms=archetype_terms,
        preferred_main=preferred_main,
        preferred_extra=preferred_extra,
        preferred_side=preferred_side,
    )


SAMPLE_DECK_SPECS = (
    make_sample_spec(
        slug="sample_maliss_1st",
        event_name="YCS Showcase London",
        event_date="2026-05-18",
        placement="1st",
        player="A. Mercer",
        archetype="Maliss",
        archetype_terms=("maliss", "malice"),
        preferred_main=(
            "Ash Blossom & Joyous Spring",
            "Effect Veiler",
            "Infinite Impermanence",
            "Nibiru, the Primal Being",
            "Called by the Grave",
            "Crossout Designator",
            "Triple Tactics Talent",
            "Pot of Prosperity",
        ),
        preferred_extra=("S:P Little Knight", "Accesscode Talker", "I:P Masquerena"),
    ),
    make_sample_spec(
        slug="sample_maliss_top4",
        event_name="Spring Championship Series",
        event_date="2026-04-27",
        placement="Top 4",
        player="I. Rees",
        archetype="Maliss",
        archetype_terms=("maliss", "malice"),
        preferred_main=(
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
            "Triple Tactics Talent",
            "Droll & Lock Bird",
            "Pot of Prosperity",
            "Forbidden Droplet",
        ),
        preferred_extra=("S:P Little Knight", "Accesscode Talker", "I:P Masquerena"),
    ),
    make_sample_spec(
        slug="sample_orcust_top8",
        event_name="Regional Showcase",
        event_date="2026-04-12",
        placement="Top 8",
        player="J. Hall",
        archetype="Orcust",
        archetype_terms=("orcust",),
        preferred_main=(
            "Orcust Harp Horror",
            "Orcust Cymbal Skeleton",
            "Orcust Knightmare",
            "Girsu, the Orcust Mekk-Knight",
            "World Legacy - \"World Wand\"",
            "Machina Redeployment",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Galatea, the Orcust Automaton",
            "Dingirsu, the Orcust of the Evening Star",
            "Longirsu, the Orcust Orchestrator",
            "I:P Masquerena",
            "Knightmare Unicorn",
        ),
    ),
    make_sample_spec(
        slug="sample_orcust_top16",
        event_name="Open Cup Midlands",
        event_date="2026-03-21",
        placement="Top 16",
        player="L. Singh",
        archetype="Orcust",
        archetype_terms=("orcust",),
        preferred_main=(
            "Orcust Harp Horror",
            "Orcust Cymbal Skeleton",
            "Girsu, the Orcust Mekk-Knight",
            "Infinite Impermanence",
            "Called by the Grave",
            "Triple Tactics Talent",
        ),
        preferred_extra=(
            "Galatea, the Orcust Automaton",
            "Dingirsu, the Orcust of the Evening Star",
            "Longirsu, the Orcust Orchestrator",
        ),
    ),
    make_sample_spec(
        slug="sample_blue_eyes_top16",
        event_name="City Championship",
        event_date="2026-03-08",
        placement="Top 16",
        player="K. Moore",
        archetype="Blue-Eyes",
        archetype_terms=("blue-eyes", "blue eyes"),
        preferred_main=(
            "Blue-Eyes White Dragon",
            "Sage with Eyes of Blue",
            "The White Stone of Ancients",
            "The White Stone of Legend",
            "Dictator of D.",
            "Blue-Eyes Jet Dragon",
            "Trade-In",
            "Bingo Machine, Go!!!",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Blue-Eyes Spirit Dragon",
            "Azure-Eyes Silver Dragon",
            "Blue-Eyes Tyrant Dragon",
            "Hieratic Seal of the Heavenly Spheres",
            "Number 38: Hope Harbinger Dragon Titanic Galaxy",
        ),
    ),
    make_sample_spec(
        slug="sample_blue_eyes_top32",
        event_name="Winter Premier Trial",
        event_date="2026-01-25",
        placement="Top 32",
        player="C. Evans",
        archetype="Blue-Eyes",
        archetype_terms=("blue-eyes", "blue eyes"),
        preferred_main=(
            "Blue-Eyes White Dragon",
            "Sage with Eyes of Blue",
            "The White Stone of Ancients",
            "Blue-Eyes Jet Dragon",
            "Trade-In",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Blue-Eyes Spirit Dragon",
            "Azure-Eyes Silver Dragon",
            "Hieratic Seal of the Heavenly Spheres",
        ),
    ),
    make_sample_spec(
        slug="sample_sky_striker_top32",
        event_name="Open Trial Event",
        event_date="2026-02-16",
        placement="Top 32",
        player="N. Carter",
        archetype="Sky Striker",
        archetype_terms=("sky striker",),
        preferred_main=(
            "Sky Striker Ace - Raye",
            "Sky Striker Ace - Roze",
            "Sky Striker Mobilize - Engage!",
            "Sky Striker Mecha - Widow Anchor",
            "Sky Striker Mecha Modules - Multirole",
            "Sky Striker Airspace - Area Zero",
            "Triple Tactics Talent",
            "Infinite Impermanence",
            "Ash Blossom & Joyous Spring",
        ),
        preferred_extra=(
            "Sky Striker Ace - Kagari",
            "Sky Striker Ace - Shizuku",
            "Sky Striker Ace - Hayate",
            "Sky Striker Ace - Kaina",
            "Sky Striker Ace - Zeke",
        ),
    ),
    make_sample_spec(
        slug="sample_sky_striker_top8",
        event_name="Metro Regional Finals",
        event_date="2026-05-04",
        placement="Top 8",
        player="S. Lowe",
        archetype="Sky Striker",
        archetype_terms=("sky striker",),
        preferred_main=(
            "Sky Striker Ace - Raye",
            "Sky Striker Ace - Roze",
            "Sky Striker Mobilize - Engage!",
            "Sky Striker Mecha - Widow Anchor",
            "Sky Striker Airspace - Area Zero",
            "Triple Tactics Talent",
            "Pot of Prosperity",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Sky Striker Ace - Kagari",
            "Sky Striker Ace - Shizuku",
            "Sky Striker Ace - Hayate",
            "Sky Striker Ace - Zeke",
        ),
    ),
    make_sample_spec(
        slug="sample_kashtira_top4",
        event_name="YCS North Trial",
        event_date="2026-05-10",
        placement="Top 4",
        player="R. Shah",
        archetype="Kashtira",
        archetype_terms=("kashtira",),
        preferred_main=(
            "Kashtira Fenrir",
            "Kashtira Unicorn",
            "Kashtira Riseheart",
            "Kashtira Birth",
            "Pressured Planet Wraitsoth",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Kashtira Shangri-Ira",
            "Kashtira Arise-Heart",
            "Number 11: Big Eye",
            "Mecha Phantom Beast Dracossack",
        ),
    ),
    make_sample_spec(
        slug="sample_labrynth_top8",
        event_name="Spring Open West",
        event_date="2026-04-05",
        placement="Top 8",
        player="D. Harper",
        archetype="Labrynth",
        archetype_terms=("labrynth",),
        preferred_main=(
            "Arianna the Labrynth Servant",
            "Lady Labrynth of the Silver Castle",
            "Lovely Labrynth of the Silver Castle",
            "Welcome Labrynth",
            "Big Welcome Labrynth",
            "Infinite Impermanence",
            "Ash Blossom & Joyous Spring",
        ),
        preferred_extra=("S:P Little Knight", "Knightmare Phoenix", "Knightmare Unicorn"),
    ),
    make_sample_spec(
        slug="sample_purrely_top16",
        event_name="Capital Cup Qualifier",
        event_date="2026-03-29",
        placement="Top 16",
        player="T. Brooks",
        archetype="Purrely",
        archetype_terms=("purrely",),
        preferred_main=(
            "Purrely",
            "Purrelyly",
            "My Friend Purrely",
            "Purrely Delicious Memory",
            "Purrely Pretty Memory",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Expurrely Noir",
            "Epurrely Plump",
            "Epurrely Beauty",
            "Downerd Magician",
            "Divine Arsenal AA-ZEUS - Sky Thunder",
        ),
    ),
    make_sample_spec(
        slug="sample_rescue_ace_top16",
        event_name="Premier Cup North",
        event_date="2026-02-28",
        placement="Top 16",
        player="M. Doyle",
        archetype="Rescue-ACE",
        archetype_terms=("rescue-ace", "rescue ace"),
        preferred_main=(
            "Rescue-ACE Hydrant",
            "Rescue-ACE Air Lifter",
            "Rescue-ACE Turbulence",
            "Rescue-ACE Preventer",
            "Alert!",
            "EMERGENCY!",
            "Infinite Impermanence",
            "Ash Blossom & Joyous Spring",
        ),
        preferred_extra=("S:P Little Knight", "I:P Masquerena", "Knightmare Unicorn"),
    ),
    make_sample_spec(
        slug="sample_swordsoul_top8",
        event_name="National Trial East",
        event_date="2026-02-08",
        placement="Top 8",
        player="P. Foster",
        archetype="Swordsoul",
        archetype_terms=("swordsoul",),
        preferred_main=(
            "Swordsoul of Mo Ye",
            "Swordsoul Strategist Longyuan",
            "Swordsoul of Taia",
            "Swordsoul Emergence",
            "Incredible Ecclesia, the Virtuous",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Swordsoul Grandmaster - Chixiao",
            "Baronne de Fleur",
            "Swordsoul Supreme Sovereign - Chengying",
            "Baxia, Brightness of the Yang Zing",
        ),
    ),
    make_sample_spec(
        slug="sample_bystial_dlink_top4",
        event_name="Championship Circuit South",
        event_date="2026-05-15",
        placement="Top 4",
        player="E. Bell",
        archetype="Bystial Dragon Link",
        archetype_terms=("bystial", "dragon link", "chaos dragon"),
        preferred_main=(
            "The Bystial Lubellion",
            "Bystial Magnamhut",
            "Bystial Druiswurm",
            "Chaos Space",
            "Starliege Seyfert",
            "Black Metal Dragon",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Striker Dragon",
            "Hieratic Seal of the Heavenly Spheres",
            "Borreload Savage Dragon",
            "Borrelend Dragon",
        ),
    ),
    make_sample_spec(
        slug="sample_branded_despia_top8",
        event_name="Regional Showcase South",
        event_date="2026-04-19",
        placement="Top 8",
        player="F. Patel",
        archetype="Branded Despia",
        archetype_terms=("branded", "despia"),
        preferred_main=(
            "Fallen of Albaz",
            "Aluber the Jester of Despia",
            "Branded Fusion",
            "Branded Opening",
            "Despian Tragedy",
            "Ash Blossom & Joyous Spring",
            "Infinite Impermanence",
        ),
        preferred_extra=(
            "Mirrorjade the Iceblade Dragon",
            "Lubellion the Searing Dragon",
            "Albion the Branded Dragon",
            "Granguignol the Dusk Dragon",
        ),
    ),
    make_sample_spec(
        slug="sample_floowandereeze_top32",
        event_name="Winter League Finals",
        event_date="2026-01-12",
        placement="Top 32",
        player="H. Watts",
        archetype="Floowandereeze",
        archetype_terms=("floowandereeze",),
        preferred_main=(
            "Floowandereeze & Robina",
            "Floowandereeze & Eglen",
            "Floowandereeze & Empen",
            "Floowandereeze and the Advent of Adventure",
            "Floowandereeze and the Magnificent Map",
            "Dimension Shifter",
            "Pot of Prosperity",
        ),
        preferred_extra=("Linkuriboh", "Relinquished Anima"),
    ),
)


def ensure_sample_metadata_files(overwrite: bool = False) -> None:
    """Persist sample metadata JSON files."""

    ensure_directories()
    for spec in SAMPLE_DECK_SPECS:
        metadata_path = DECK_METADATA_DIR / f"{spec.slug}.json"
        if metadata_path.exists() and not overwrite:
            continue
        metadata_path.write_text(json.dumps(spec.metadata, indent=2), encoding="utf-8")


def ensure_sample_deck_files(cards: list[dict], overwrite: bool = False) -> list[Path]:
    """Generate sample `.ydk` files from live card metadata."""

    ensure_directories()
    ensure_sample_metadata_files(overwrite=overwrite)
    name_lookup = {str(card.get("name", "")).strip().lower(): card for card in cards}
    created_paths: list[Path] = []

    for spec in SAMPLE_DECK_SPECS:
        deck_path = DECKS_DIR / f"{spec.slug}.ydk"
        if deck_path.exists() and not overwrite:
            created_paths.append(deck_path)
            continue
        deck_sections = _build_deck_sections(cards, name_lookup, spec)
        _write_ydk_file(deck_path, deck_sections)
        created_paths.append(deck_path)

    return created_paths


def _build_deck_sections(
    cards: list[dict],
    name_lookup: dict[str, dict],
    spec: SampleDeckSpec,
) -> dict[str, list[int]]:
    sections: dict[str, list[int]] = {"main": [], "extra": [], "side": []}
    copy_tracker: dict[str, Counter[int]] = {
        "main": Counter(),
        "extra": Counter(),
        "side": Counter(),
    }

    for name in spec.preferred_main:
        _append_card_by_name(sections, copy_tracker, name_lookup, "main", name)
    for name in spec.preferred_extra:
        _append_card_by_name(sections, copy_tracker, name_lookup, "extra", name)
    for name in spec.preferred_side:
        _append_card_by_name(sections, copy_tracker, name_lookup, "side", name)

    archetype_pool = _search_cards(cards, spec.archetype_terms)
    _fill_from_pool(sections, copy_tracker, archetype_pool, "main", 40)
    _fill_from_pool(sections, copy_tracker, archetype_pool, "extra", 15)
    _fill_with_named_cards(sections, copy_tracker, name_lookup, "main", COMMON_MAIN_FILLERS, 40)
    _fill_with_named_cards(sections, copy_tracker, name_lookup, "extra", COMMON_EXTRA_FILLERS, 15)
    _fill_with_named_cards(sections, copy_tracker, name_lookup, "side", COMMON_SIDE_FILLERS, 15)

    global_pool = [card for card in cards if not _is_token(card)]
    _fill_from_pool(sections, copy_tracker, global_pool, "main", 40)
    _fill_from_pool(sections, copy_tracker, global_pool, "extra", 15)
    _fill_from_pool(sections, copy_tracker, global_pool, "side", 15)

    return sections


def _append_card_by_name(
    sections: dict[str, list[int]],
    copy_tracker: dict[str, Counter[int]],
    name_lookup: dict[str, dict],
    section: str,
    name: str,
) -> None:
    card = name_lookup.get(name.lower())
    if not card or not _card_matches_section(card, section):
        return
    _append_card(sections, copy_tracker, section, int(card["id"]))


def _fill_with_named_cards(
    sections: dict[str, list[int]],
    copy_tracker: dict[str, Counter[int]],
    name_lookup: dict[str, dict],
    section: str,
    names: list[str],
    target_size: int,
) -> None:
    while len(sections[section]) < target_size:
        progress = False
        for name in names:
            before = len(sections[section])
            _append_card_by_name(sections, copy_tracker, name_lookup, section, name)
            if len(sections[section]) >= target_size:
                return
            progress = progress or len(sections[section]) > before
        if not progress:
            return


def _fill_from_pool(
    sections: dict[str, list[int]],
    copy_tracker: dict[str, Counter[int]],
    cards: list[dict],
    section: str,
    target_size: int,
) -> None:
    for card in cards:
        if len(sections[section]) >= target_size:
            return
        if not _card_matches_section(card, section):
            continue
        _append_card(sections, copy_tracker, section, int(card["id"]))


def _append_card(
    sections: dict[str, list[int]],
    copy_tracker: dict[str, Counter[int]],
    section: str,
    card_id: int,
) -> None:
    max_copies = 3 if section in {"main", "side"} else 2
    if copy_tracker[section][card_id] >= max_copies:
        return
    sections[section].append(card_id)
    copy_tracker[section][card_id] += 1


def _search_cards(cards: list[dict], terms: tuple[str, ...]) -> list[dict]:
    matches: list[dict] = []
    for card in cards:
        if _is_token(card):
            continue
        haystack = " ".join(
            str(card.get(field, "")).lower() for field in ("name", "archetype", "desc")
        )
        if any(term.lower() in haystack for term in terms):
            matches.append(card)
    return matches


def _card_matches_section(card: dict, section: str) -> bool:
    card_type = str(card.get("type", "")).lower()
    extra_type = any(token in card_type for token in ("fusion", "synchro", "xyz", "link"))
    if section == "main":
        return not extra_type
    if section == "extra":
        return extra_type
    if section == "side":
        return not _is_token(card)
    return False


def _is_token(card: dict) -> bool:
    return "token" in str(card.get("type", "")).lower()


def _write_ydk_file(path: Path, sections: dict[str, list[int]]) -> None:
    lines = [
        "#created by YGO MetaPulse",
        "#main",
        *(str(card_id) for card_id in sections["main"]),
        "#extra",
        *(str(card_id) for card_id in sections["extra"]),
        "!side",
        *(str(card_id) for card_id in sections["side"]),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
