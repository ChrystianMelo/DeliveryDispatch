"""Testes das funções e da composição principal do painel web."""

from dataclasses import replace

import pytest
from dash.development.base_component import Component

from delivery_dispatch.dashboard import (
    build_courier_results_table,
    build_map_figure,
    create_app,
    estimated_arrival_minutes,
    restaurant_option,
    serialize_couriers,
    validate_courier_count,
    validate_search_radius,
)
from delivery_dispatch.models.bar import Bar
from delivery_dispatch.models.courier import Courier
from delivery_dispatch.services.courier_search import CourierSearchResult


def make_bar(bar_id=1, *, latitude=-19.92, longitude=-43.94):
    return Bar(
        id=bar_id,
        cnae_code=5611201,
        cnae_description="RESTAURANTE",
        street_type="RUA",
        street_name="DOS TAMOIOS",
        street_number="100",
        neighborhood="CENTRO",
        legal_name="RESTAURANTE TESTE",
        trade_name="CASA TESTE",
        latitude=latitude,
        longitude=longitude,
        geohash="6gy",
        geocoding_status="found" if latitude is not None else "not_found",
    )


def component_ids(component):
    ids = set()
    if not isinstance(component, Component):
        return ids
    if getattr(component, "id", None):
        ids.add(component.id)
    children = getattr(component, "children", None)
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        ids.update(component_ids(child))
    return ids


def component_by_id(component, component_id):
    if not isinstance(component, Component):
        return None
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        match = component_by_id(child, component_id)
        if match is not None:
            return match
    return None


def component_text(component):
    if isinstance(component, str):
        return component
    if isinstance(component, (list, tuple)):
        return " ".join(component_text(child) for child in component)
    if not isinstance(component, Component):
        return ""
    children = getattr(component, "children", None)
    if not isinstance(children, (list, tuple)):
        children = [children]
    return " ".join(component_text(child) for child in children)


def legend_names(figure):
    return [trace.name for trace in figure.data if trace.showlegend is not False]


def symbol_traces(figure, symbol):
    return [trace for trace in figure.data if trace.marker.symbol == symbol]


@pytest.mark.parametrize("value, expected", [(0, 0), (12, 12), (12.0, 12), (" 9 ", 9)])
def test_validates_non_negative_integer_courier_counts(value, expected):
    assert validate_courier_count(value) == expected


@pytest.mark.parametrize("value", [None, True, -1, 2.5, "2.5", "abc", float("inf")])
def test_rejects_invalid_courier_counts(value):
    with pytest.raises(ValueError):
        validate_courier_count(value)


@pytest.mark.parametrize("value, expected", [(1, 1.0), (2.5, 2.5), (" 0.8 ", 0.8)])
def test_validates_positive_search_radius(value, expected):
    assert validate_search_radius(value) == expected


@pytest.mark.parametrize("value", [None, True, 0, -1, "abc", float("inf")])
def test_rejects_invalid_search_radius(value):
    with pytest.raises(ValueError):
        validate_search_radius(value)


def test_estimates_arrival_time_at_30_km_per_hour():
    assert estimated_arrival_minutes(1) == pytest.approx(2)
    assert estimated_arrival_minutes(0) == 0


def test_serializes_couriers_for_the_session_store():
    courier = Courier(7, -19.91, -43.93, center_bar_id=3, geohash="6gyf")

    assert serialize_couriers([courier]) == [
        {
            "id": 7,
            "latitude": -19.91,
            "longitude": -43.93,
            "center_bar_id": 3,
            "geohash": "6gyf",
        }
    ]


def test_restaurant_option_is_searchable_without_accents():
    bar = replace(make_bar(), trade_name="CAFÉ AÇÃO")

    option = restaurant_option(bar)

    assert option["value"] == bar.id
    assert "cafe acao" in option["search"]


def test_results_table_shows_couriers_and_calculated_distances():
    bar = make_bar()
    courier = Courier(7, -19.921, -43.94, bar.id, "6gyf")
    table = build_courier_results_table(
        [CourierSearchResult(courier, 0.111195)],
        bar,
        has_couriers=True,
    )

    text = component_text(table)
    assert table.id == "courier-results"
    assert "1 encontrado" in text
    assert "#7" in text
    assert "0.111" in text
    assert "0.2" in text
    assert "6gyf" in text


def test_empty_state_still_creates_the_interactive_map_subplot():
    figure = build_map_figure({})

    assert len(figure.data) == 1
    assert figure.data[0].type == "scattermap"
    assert figure.data[0].marker.opacity == 0
    assert figure.layout.map.style == "carto-positron"


def test_map_initially_shows_every_located_bar_in_black():
    first_bar = make_bar(1)
    second_bar = make_bar(2, latitude=-19.91, longitude=-43.93)
    bar_without_coordinates = make_bar(3, latitude=None, longitude=None)

    figure = build_map_figure(
        {
            first_bar.id: first_bar,
            second_bar.id: second_bar,
            bar_without_coordinates.id: bar_without_coordinates,
        }
    )

    assert legend_names(figure) == ["Restaurantes"]
    assert figure.layout.showlegend is False
    assert list(figure.data[0].lat) == [first_bar.latitude, second_bar.latitude]
    assert figure.data[0].mode == "markers"
    assert figure.data[0].marker.color == "#111827"
    assert figure.data[0].marker.symbol == "restaurant"
    assert figure.data[0].marker.allowoverlap is True


def test_couriers_are_gray_before_a_bar_is_selected():
    bar = make_bar()
    records = serialize_couriers([Courier(1, -19.91, -43.93, bar.id, "6gyf")])

    figure = build_map_figure({bar.id: bar}, records)

    assert legend_names(figure) == ["Restaurantes", "Entregadores"]
    assert figure.layout.showlegend is False
    assert figure.data[1].mode == "markers"
    assert figure.data[1].marker.color == "#111827"
    assert figure.data[1].marker.symbol == "bicycle"
    assert figure.data[1].marker.allowoverlap is True


def test_map_highlights_only_nearby_couriers_in_green():
    bar = make_bar()
    other_bar = make_bar(2, latitude=-19.90, longitude=-43.92)
    records = serialize_couriers([Courier(1, -19.91, -43.93, bar.id, "6gyf")])

    figure = build_map_figure({bar.id: bar, other_bar.id: other_bar}, records, bar.id)

    assert legend_names(figure) == [
        "Restaurantes",
        "Entregadores no raio",
        "Restaurante selecionado",
    ]
    assert figure.layout.showlegend is False
    assert list(figure.data[0].lat) == [other_bar.latitude]
    assert figure.data[0].marker.color == "#111827"
    assert figure.data[1].marker.color == "#22c55e"
    selected_restaurant = next(
        trace for trace in figure.data if trace.name == "Restaurante selecionado"
    )
    assert selected_restaurant.marker.color == "#f97316"
    assert len(symbol_traces(figure, "bicycle")) == 1
    assert len(symbol_traces(figure, "restaurant")) == 2
    assert figure.layout.map.center.lat == bar.latitude
    assert figure.layout.map.center.lon == bar.longitude
    assert figure.layout.map.zoom == 11.3


def test_map_keeps_distant_couriers_gray_and_highlights_search_results():
    bar = make_bar(latitude=-19.92, longitude=-43.94)
    records = serialize_couriers(
        [
            Courier(1, -19.921, -43.94, bar.id, "near"),
            Courier(2, -19.94, -43.94, bar.id, "far"),
        ]
    )

    initial_figure = build_map_figure({bar.id: bar}, records)
    figure = build_map_figure({bar.id: bar}, records, bar.id, search_radius_km=0.5)

    initial_courier_trace = next(
        trace for trace in initial_figure.data if trace.name == "Entregadores"
    )
    regular_trace = next(
        trace for trace in figure.data if trace.name == "Entregadores fora do raio"
    )
    nearby_trace = next(trace for trace in figure.data if trace.name == "Entregadores no raio")

    assert [row[0] for row in regular_trace.customdata] == [2]
    assert regular_trace.marker.color == "#111827"
    assert regular_trace.marker.symbol == "bicycle"
    assert [row[0] for row in nearby_trace.customdata] == [1]
    assert nearby_trace.marker.color == "#22c55e"
    initial_points = set(zip(initial_courier_trace.lat, initial_courier_trace.lon, strict=True))
    result_points = set(zip(regular_trace.lat, regular_trace.lon, strict=True)) | set(
        zip(nearby_trace.lat, nearby_trace.lon, strict=True)
    )
    assert result_points == initial_points
    assert len(regular_trace.lat) + len(nearby_trace.lat) == 2
    assert figure.layout.uirevision == initial_figure.layout.uirevision
    assert figure.layout.map.zoom == initial_figure.layout.map.zoom


def test_app_factory_exposes_search_count_button_and_map_without_projecting():
    class UnexpectedProjector:
        def project(self, coordinates):
            raise AssertionError("o projetor deve ser usado somente após o clique")

    app = create_app([make_bar()], UnexpectedProjector())

    assert {
        "restaurant-search",
        "courier-count",
        "search-radius",
        "generate-couriers",
        "dispatch-map",
        "courier-store",
        "courier-results",
    } <= component_ids(app.layout)
    assert len(app.callback_map) == 3

    dispatch_map = component_by_id(app.layout, "dispatch-map")
    assert dispatch_map is not None
    assert legend_names(dispatch_map.figure) == ["Restaurantes"]
    assert dispatch_map.figure.layout.showlegend is False
    assert dispatch_map.figure.data[0].marker.symbol == "restaurant"


def test_map_callback_populates_results_table_with_distance():
    bar = make_bar()
    records = serialize_couriers([Courier(7, -19.921, -43.94, bar.id, "6gyf")])
    app = create_app([bar], object())
    callback = next(
        definition["callback"].__wrapped__
        for output, definition in app.callback_map.items()
        if "courier-results.children" in output
    )

    _, _, table_children = callback(bar.id, records, 0.5)

    text = component_text(table_children)
    assert "#7" in text
    assert "0.111" in text


def test_each_generate_click_uses_a_new_distribution_seed(monkeypatch):
    used_seeds = []

    def record_generation_seed(count, bars, road_projector, *, seed):
        used_seeds.append(seed)
        return []

    monkeypatch.setattr(
        "delivery_dispatch.dashboard.generate_couriers",
        record_generation_seed,
    )
    app = create_app([make_bar()], object())
    callback = next(
        definition["callback"].__wrapped__
        for output, definition in app.callback_map.items()
        if "courier-store.data" in output
    )

    callback(1, 10)
    callback(2, 10)

    assert used_seeds == [1, 2]
