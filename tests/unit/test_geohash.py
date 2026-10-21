"""Testes dos contratos principais de codificação Geohash."""

import pytest

from delivery_dispatch.algorithms.geohash import decode, encode


def test_encode_matches_known_geohash_references():
    assert encode(42.6, -5.6, 5) == "ezs42"
    assert encode(57.64911, 10.40744) == "u4pruydq"
    assert encode(-25.382708, -49.265506) == "6gkzwgjz"


def test_encode_rejects_invalid_arguments():
    with pytest.raises(ValueError):
        encode(0, 0, 0)
    with pytest.raises(ValueError):
        encode(0, 0, 9)
    with pytest.raises(TypeError):
        encode(0, 0, 1.5)
    with pytest.raises(ValueError):
        encode(-90.001, 0)
    with pytest.raises(ValueError):
        encode(0, 181)
    with pytest.raises(TypeError):
        encode("0", 0)


def test_decode_matches_known_geohash_reference():
    assert decode("ezs42") == pytest.approx((42.60498046875, -5.60302734375))


def test_decode_rejects_invalid_geohashes():
    with pytest.raises(TypeError):
        decode(None)
    with pytest.raises(ValueError):
        decode("")
    with pytest.raises(ValueError):
        decode("012345678")
    with pytest.raises(ValueError):
        decode("ezs4!")
