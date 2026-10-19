"""Testes das regras principais da geração de entregadores."""

from collections import Counter

from delivery_dispatch.models.bar import Bar
from delivery_dispatch.services.courier_generation import (
    METERS_PER_LATITUDE_DEGREE,
    generate_couriers,
)


class IdentityRoadProjector:
    def project(self, coordinates):
        return list(coordinates)


def make_bar(bar_id, latitude=-19.9, longitude=-43.9):
    return Bar(
        id=bar_id,
        cnae_code=5611201,
        cnae_description="RESTAURANTE",
        street_type="RUA",
        street_name=f"EXEMPLO {bar_id}",
        street_number="10",
        neighborhood="CENTRO",
        legal_name=f"BAR {bar_id}",
        latitude=latitude,
        longitude=longitude,
        geocoding_status="found",
    )


def test_distributes_couriers_equitably_between_bars():
    bars = [make_bar(1), make_bar(2), make_bar(3)]

    couriers = generate_couriers(10, bars, IdentityRoadProjector())

    counts = Counter(courier.center_bar_id for courier in couriers)
    assert sorted(counts.values()) == [3, 3, 4]


def test_generation_is_reproducible_with_the_same_seed():
    bars = [make_bar(1), make_bar(2)]

    first = generate_couriers(20, bars, IdentityRoadProjector(), seed=123)
    second = generate_couriers(20, bars, IdentityRoadProjector(), seed=123)

    assert first == second


def test_generated_coordinates_are_centered_on_the_bar():
    bar = make_bar(1)
    couriers = generate_couriers(
        10_000,
        [bar],
        IdentityRoadProjector(),
        standard_deviation_meters=500,
        seed=42,
    )

    mean_latitude = sum(courier.latitude for courier in couriers) / len(couriers)
    latitude_error_meters = abs(mean_latitude - bar.latitude) * METERS_PER_LATITUDE_DEGREE

    assert latitude_error_meters < 20


def test_builds_couriers_from_road_projected_coordinates():
    class FixedRoadProjector:
        def project(self, coordinates):
            assert len(coordinates) == 2
            return [(-19.91, -43.91), (-19.92, -43.92)]

    couriers = generate_couriers(2, [make_bar(7)], FixedRoadProjector())

    assert [courier.coordinates for courier in couriers] == [
        (-19.91, -43.91),
        (-19.92, -43.92),
    ]
    assert [courier.center_bar_id for courier in couriers] == [7, 7]
    assert all(courier.geohash is not None for courier in couriers)
