"""Testes da conversão binária de coordenadas para Geohash."""

import pytest

from delivery_dispatch.algorithms.geohash import BASE32, encode


@pytest.mark.parametrize(
    ("latitude", "longitude", "levels", "expected"),
    [
        (42.6, -5.6, 5, "ezs42"),
        (57.64911, 10.40744, 8, "u4pruydq"),
        (-25.382708, -49.265506, 8, "6gkzwgjz"),
        (0, 0, 8, "s0000000"),
        (-90, -180, 8, "00000000"),
        (-90, 180, 8, "pbpbpbpb"),
        (90, -180, 8, "bpbpbpbp"),
        (90, 180, 8, "zzzzzzzz"),
    ],
)
def test_known_geohashes(latitude, longitude, levels, expected):
    assert encode(latitude, longitude, levels) == expected


@pytest.mark.parametrize("levels", range(1, 9))
def test_levels_produce_prefixes(levels):
    result = encode(57.64911, 10.40744, levels)

    assert result == "u4pruydq"[:levels]
    assert len(result) == levels
    assert set(result) <= set(BASE32)


def test_default_is_eight_levels():
    assert encode(42.6, -5.6) == "ezs42e44"


@pytest.mark.parametrize(
    ("latitude", "longitude", "expected"),
    [(0, 0, "s"), (0, -0.001, "e"), (-0.001, 0, "k"), (-0.001, -0.001, "7")],
)
def test_midpoint_and_interleaving_order(latitude, longitude, expected):
    assert encode(latitude, longitude, 1) == expected


@pytest.mark.parametrize("levels", [0, -1, 9, 100])
def test_invalid_levels(levels):
    with pytest.raises(ValueError, match="levels"):
        encode(0, 0, levels)


@pytest.mark.parametrize("levels", [True, False, 1.5, "8", None])
def test_non_integer_levels(levels):
    with pytest.raises(TypeError, match="levels"):
        encode(0, 0, levels)


@pytest.mark.parametrize("value", [-90.001, 90.001, float("nan"), float("inf"), -float("inf")])
def test_invalid_latitude(value):
    with pytest.raises(ValueError, match="latitude"):
        encode(value, 0)


@pytest.mark.parametrize("value", [-180.001, 180.001, float("nan"), float("inf"), -float("inf")])
def test_invalid_longitude(value):
    with pytest.raises(ValueError, match="longitude"):
        encode(0, value)


@pytest.mark.parametrize("value", [True, False, "0", None, complex(0, 1)])
@pytest.mark.parametrize("axis", ["latitude", "longitude"])
def test_non_numeric_coordinates(value, axis):
    coordinates = {"latitude": 0, "longitude": 0, axis: value}

    with pytest.raises(TypeError, match=axis):
        encode(**coordinates)
