"""Testes dos contratos principais da trie compacta."""

import pytest

from delivery_dispatch.algorithms import Node
from delivery_dispatch.algorithms.compact_trie import CompactTrie


def _values(trie: CompactTrie[str], prefix: str) -> set[str | None]:
    return {node.value for node in trie.search_prefix(prefix)}


def test_searches_shared_prefixes_and_compacted_edges():
    trie = CompactTrie[str]()
    trie.insert("6gyf4bf", "long")
    trie.insert("6gyf", "short")
    trie.insert("6gyf4bc", "sibling")
    trie.insert("6gyc", "other branch")

    assert _values(trie, "6gyf") == {"long", "short", "sibling"}
    assert _values(trie, "6gyf4") == {"long", "sibling"}
    assert _values(trie, "6gyc") == {"other branch"}
    assert trie.search_prefix("7zz") == []


def test_duplicate_key_preserves_first_value():
    trie = CompactTrie[str]()
    trie.insert("6gyf", "first")
    trie.insert("6gyf", "second")

    assert _values(trie, "6gyf") == {"first"}


def test_remove_preserves_siblings_and_descendants():
    trie = CompactTrie[str]()
    for key in ("6gyf", "6gyf4bf", "6gyf4bc", "6gyc"):
        trie.insert(key, key)

    trie.remove("6gyf4bc")
    trie.remove("6gyf")

    assert trie.search_prefix("6gyf4bc") == []
    assert _values(trie, "6gyf") == {"6gyf4bf"}
    assert _values(trie, "6gyc") == {"6gyc"}


def test_remove_missing_key_raises_key_error():
    trie = CompactTrie[str]()
    trie.insert("6gyf", "value")

    with pytest.raises(KeyError):
        trie.remove("missing")

    assert _values(trie, "6gyf") == {"value"}


def test_generic_values_are_stored_only_in_terminal_leaves():
    first_payload = object()
    second_payload = object()
    trie = CompactTrie[object]()
    trie.insert("shared-one", first_payload)
    trie.insert("shared-two", second_payload)

    leaves = trie.search_prefix("shared")

    assert {id(node.value) for node in leaves} == {id(first_payload), id(second_payload)}
    assert all(node.children == {} for node in leaves)

    def assert_parent_values_are_empty(node: Node[object]) -> None:
        if node.children:
            assert node.value is None
        for child in node.children.values():
            assert_parent_values_are_empty(child)

    assert_parent_values_are_empty(trie._root)


def test_rejects_invalid_keys_and_prefixes():
    trie = CompactTrie[str]()

    with pytest.raises(TypeError):
        trie.insert(None, "value")
    with pytest.raises(ValueError):
        trie.insert("reserved$marker", "value")
    with pytest.raises(ValueError):
        trie.search_prefix("")
