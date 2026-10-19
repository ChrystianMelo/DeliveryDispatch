"""Testes da conversão binária de coordenadas para Geohash."""

import pytest

from delivery_dispatch.algorithms.geohash import BASE32, decode, encode


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


@pytest.mark.parametrize(
    ("geohash", "expected"),
    [
        ("ezs42", (42.60498046875, -5.60302734375)),
        ("u4pruydq", (57.649126052856445, 10.40731430053711)),
        ("6gkzwgjz", (-25.38262367248535, -49.2656135559082)),
        ("s0000000", (0.0000858306884765625, 0.000171661376953125)),
    ],
)
def test_decode_returns_cell_center(geohash, expected):
    assert decode(geohash) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-25.382708, -49.265506),
        (42.6, -5.6),
        (57.64911, 10.40744),
        (0.0, 0.0),
        (-89.9, 179.9),
    ],
)
@pytest.mark.parametrize("levels", range(1, 9))
def test_encode_then_decode_approximates_original_coordinates(latitude, longitude, levels):
    geohash = encode(latitude, longitude, levels)
    decoded_latitude, decoded_longitude = decode(geohash)
    latitude_bits = (levels * 5) // 2
    longitude_bits = (levels * 5 + 1) // 2
    latitude_cell_size = 180 / (2**latitude_bits)
    longitude_cell_size = 360 / (2**longitude_bits)
    latitude_tolerance = latitude_cell_size / 2
    longitude_tolerance = longitude_cell_size / 2

    assert decoded_latitude == pytest.approx(latitude, abs=latitude_tolerance)
    assert decoded_longitude == pytest.approx(longitude, abs=longitude_tolerance)


@pytest.mark.parametrize("value", [None, 123, True, ["e"]])
def test_decode_rejects_non_string_values(value):
    with pytest.raises(TypeError, match="geohash"):
        decode(value)


@pytest.mark.parametrize("value", ["", "012345678", "a", "EZS42", "ezs4!"])
def test_decode_rejects_invalid_geohashes(value):
    with pytest.raises(ValueError, match="geohash|caractere"):
        decode(value)
