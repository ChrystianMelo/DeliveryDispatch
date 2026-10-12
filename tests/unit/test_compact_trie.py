"""Testes da trie compacta de prefixos."""

import pytest

from delivery_dispatch.algorithms import Node
from delivery_dispatch.algorithms.compact_trie import _END, CompactTrie


def test_insert_and_search_prefix_with_shared_prefixes():
    trie = CompactTrie()

    trie.insert("6gyf")
    trie.insert("6gyc")
    trie.insert("6gyd")
    trie.insert("6gyf4bf")

    assert len(trie.search_prefix("6gyf")) == 2
    assert len(trie.search_prefix("6gyc")) == 1
    assert len(trie.search_prefix("6gyd")) == 1
    assert len(trie.search_prefix("6gyf4bf")) == 1
    assert len(trie.search_prefix("6gy")) == 4
    assert len(trie.search_prefix("6gyf4")) == 1


def test_geohash_can_be_prefix_of_another_regardless_of_insertion_order():
    trie = CompactTrie()
    trie.insert("6gyf4bf")
    trie.insert("6gyf")
    trie.insert("6gyf4bc")

    assert len(trie.search_prefix("6gyf")) == 3
    assert len(trie.search_prefix("6gyf4bf")) == 1
    assert len(trie.search_prefix("6gyf4bc")) == 1


def test_inserting_existing_geohash_does_not_duplicate_it():
    trie = CompactTrie()
    trie.insert("6gyf4bf")
    trie.insert("6gyf4bf")

    assert len(trie.search_prefix("6gyf4bf")) == 1


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

    assert _END in trie._root.children
    assert len(trie.search_prefix("6")) == 1


def test_search_prefix_returns_only_geohashes_below_matching_node():
    trie = CompactTrie()
    for geohash in ("6gyf", "6gyf4bf", "6gyf4bc", "6gyc"):
        trie.insert(geohash)

    nodes = trie.search_prefix("6gyf")

    assert len(nodes) == 3
    assert all(_END in node.children for node in nodes)


def test_search_prefix_can_end_in_the_middle_of_a_compact_edge():
    trie = CompactTrie()
    trie.insert("6gyf4bf")

    nodes = trie.search_prefix("6gy")

    assert len(nodes) == 1
    assert isinstance(nodes[0], Node)
    assert nodes[0].prefix == "6gyf4bf"
    assert _END in nodes[0].children


def test_search_prefix_returns_empty_list_when_prefix_does_not_exist():
    trie = CompactTrie()
    trie.insert("6gyf4bf")

    assert trie.search_prefix("7zz") == []


def test_empty_prefix_is_rejected():
    trie = CompactTrie()
    trie.insert("6gyf")

    with pytest.raises(ValueError, match="prefix não pode ser vazio"):
        trie.search_prefix("")


@pytest.mark.parametrize("key", [None, 1, True, b"6gyf"])
def test_non_string_keys_are_rejected(key):
    trie = CompactTrie()

    with pytest.raises(TypeError, match="key"):
        trie.insert(key)


def test_end_marker_is_rejected_in_keys():
    trie = CompactTrie()

    with pytest.raises(ValueError, match="marcador"):
        trie.insert("geo$hash")
