"""Testes da trie compacta de prefixos."""

import pytest

from delivery_dispatch.algorithms.compact_trie import _END, CompactTrie


def test_insert_and_search_geohashes_with_shared_prefixes():
    trie = CompactTrie()

    trie.insert("6gyf")
    trie.insert("6gyc")
    trie.insert("6gyd")
    trie.insert("6gyf4bf")

    assert trie.search("6gyf")
    assert trie.search("6gyc")
    assert trie.search("6gyd")
    assert trie.search("6gyf4bf")
    assert not trie.search("6gy")
    assert not trie.search("6gyf4")


def test_geohash_can_be_prefix_of_another_regardless_of_insertion_order():
    trie = CompactTrie()
    trie.insert("6gyf4bf")
    trie.insert("6gyf")
    trie.insert("6gyf4bc")

    assert trie.search("6gyf")
    assert trie.search("6gyf4bf")
    assert trie.search("6gyf4bc")


def test_inserting_existing_geohash_does_not_duplicate_it():
    trie = CompactTrie()
    trie.insert("6gyf4bf")
    trie.insert("6gyf4bf")

    assert trie.search("6gyf4bf")


def test_every_geohash_ends_with_end_marker():
    trie = CompactTrie()
    trie.insert("6gyf")

    geohash_node = trie._root.children["6"]

    assert geohash_node.prefix == "6gyf"
    assert set(geohash_node.children) == {_END}


def test_empty_key_is_supported():
    trie = CompactTrie()
    trie.insert("")
    trie.insert("6")

    assert trie.search("")
    assert trie.search("6")


def test_search_returns_false_for_missing_geohash():
    trie = CompactTrie()
    trie.insert("6gyf4bf")

    assert not trie.search("6gyf4bc")


@pytest.mark.parametrize("key", [None, 1, True, b"6gyf"])
def test_non_string_keys_are_rejected(key):
    trie = CompactTrie()

    with pytest.raises(TypeError, match="key"):
        trie.insert(key)


def test_end_marker_is_rejected_in_keys():
    trie = CompactTrie()

    with pytest.raises(ValueError, match="marcador"):
        trie.insert("geo$hash")
