"""Testes do índice geoespacial de entregadores."""

import pytest

from delivery_dispatch.algorithms.geohash import encode
from delivery_dispatch.models.courier import Courier
from delivery_dispatch.services.courier_search import (
    CourierSearchIndex,
    geohash_grid_prefixes,
    geohash_precision_for_radius,
    haversine_distance_km,
)


def make_courier(courier_id, latitude, longitude):
    return Courier(courier_id, latitude, longitude, center_bar_id=1)


def test_haversine_distance_uses_the_great_circle():
    assert haversine_distance_km(0, 0, 1, 0) == pytest.approx(111.195, rel=1e-5)
    assert haversine_distance_km(-19.92, -43.94, -19.92, -43.94) == 0


def test_radius_selects_a_grid_precision_and_adjacent_prefixes():
    prefixes = geohash_grid_prefixes(-19.92, -43.9344, 0.5)

    assert geohash_precision_for_radius(-19.92, 0.5) == 6
    assert encode(-19.92, -43.9344, 6) in prefixes
    assert encode(-19.92, -43.9342, 6) in prefixes
    assert all(len(prefix) == 6 for prefix in prefixes)
    assert len(prefixes) <= 9


def test_search_crosses_a_geohash_border_before_filtering_by_haversine():
    restaurant = (-19.92, -43.9344)
    across_border = make_courier(1, -19.92, -43.9342)
    outside_radius = make_courier(2, -19.925, -43.9344)
    index = CourierSearchIndex([across_border, outside_radius])

    assert encode(*restaurant, 6) != encode(*across_border.coordinates, 6)
    assert {courier.id for courier in index.candidates(*restaurant, 0.5)} == {1, 2}
    results = index.search(*restaurant, 0.5)

    assert [result.courier.id for result in results] == [1]
    assert results[0].distance_km == pytest.approx(
        haversine_distance_km(*restaurant, *across_border.coordinates)
    )


def test_index_preserves_couriers_that_share_the_same_geohash():
    couriers = [
        make_courier(1, -19.92, -43.94),
        make_courier(2, -19.92, -43.94),
    ]

    results = CourierSearchIndex(couriers).search(-19.92, -43.94, 1)

    assert [result.courier.id for result in results] == [1, 2]
    assert [result.distance_km for result in results] == [0, 0]


def test_search_orders_results_by_distance():
    restaurant = (-19.92, -43.94)
    farther = make_courier(1, -19.924, -43.94)
    closer = make_courier(2, -19.921, -43.94)

    results = CourierSearchIndex([farther, closer]).search(*restaurant, 1)

    assert [result.courier.id for result in results] == [2, 1]
    assert results[0].distance_km < results[1].distance_km


@pytest.mark.parametrize("radius", [0, -1, float("inf")])
def test_rejects_invalid_search_radii(radius):
    with pytest.raises(ValueError):
        geohash_grid_prefixes(-19.92, -43.94, radius)
