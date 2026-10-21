"""Testes do índice textual de bares e restaurantes."""

import pytest

from delivery_dispatch.models.bar import Bar
from delivery_dispatch.services.bar_search import BarSearchIndex, normalize_text


def make_bar(
    bar_id: int,
    *,
    name: str,
    street_name: str = "AFONSO PENA",
    street_number: str = "100",
) -> Bar:
    return Bar(
        id=bar_id,
        cnae_code=5611201,
        cnae_description="RESTAURANTE",
        street_type="AVE",
        street_name=street_name,
        street_number=street_number,
        neighborhood="CENTRO",
        legal_name=name,
    )


def test_normalizes_case_accents_and_repeated_spaces():
    assert normalize_text("  Ação   & CAFÉ  ") == "acao & cafe"


def test_searches_by_name_or_address_without_case_or_accent_distinction():
    first = make_bar(1, name="Café Mineiro")
    second = make_bar(2, name="Cantina", street_name="SÃO JOÃO", street_number="25")
    index = BarSearchIndex([first, second])

    assert index.search("CAFE") == [first]
    assert index.search("avenida sao joao") == [second]
    assert index.search("sao joao") == [second]
    assert index.search("centro") == [first, second]


def test_preserves_duplicate_keys_and_deduplicates_matches_between_indexes():
    first = make_bar(1, name="Bar Central")
    second = make_bar(2, name="Bar Central")
    index = BarSearchIndex([first, second])

    assert index.search("bar central") == [first, second]

    same_text = make_bar(3, name="Avenida Afonso Pena, 100, Centro, Belo Horizonte - MG, Brasil")
    duplicated_match_index = BarSearchIndex([same_text])
    assert duplicated_match_index.search("avenida afonso pena") == [same_text]


def test_limits_results_and_accepts_an_injected_normalizer():
    bars = [
        make_bar(1, name="BAR-UM"),
        make_bar(2, name="BAR-DOIS"),
        make_bar(3, name="BAR-TRÊS"),
    ]
    index = BarSearchIndex(
        bars,
        normalizer=lambda value: normalize_text(value).replace("-", ""),
    )

    assert index.search("bar-", limit=2) == bars[:2]
    assert index.search("bar-", limit=0) == []


def test_empty_query_has_no_results_and_invalid_limits_are_rejected():
    index = BarSearchIndex([make_bar(1, name="Bar Um")])

    assert index.search("   ") == []
    with pytest.raises(TypeError):
        index.search("bar", limit=True)
    with pytest.raises(ValueError):
        index.search("bar", limit=-1)


def test_handles_the_terminal_marker_reserved_by_the_trie():
    bar = make_bar(1, name="Bar $ Econômico")
    index = BarSearchIndex([bar])

    assert index.search("BAR $") == [bar]
