from src.sample_data import SAMPLE_DECK_SPECS


def test_sample_dataset_is_large_enough_for_demo_analytics() -> None:
    slugs = [spec.slug for spec in SAMPLE_DECK_SPECS]

    assert len(SAMPLE_DECK_SPECS) >= 12
    assert len(slugs) == len(set(slugs))
