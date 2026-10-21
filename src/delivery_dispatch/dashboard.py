"""Interface web interativa do DeliveryDispatch."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html, no_update

from delivery_dispatch.models.bar import Bar
from delivery_dispatch.models.courier import Courier
from delivery_dispatch.services.bar_search import BarSearchIndex, normalize_text
from delivery_dispatch.services.courier_generation import (
    RoadProjector,
    generate_couriers,
)
from delivery_dispatch.services.courier_search import (
    CourierSearchIndex,
    CourierSearchResult,
)
from delivery_dispatch.services.road_network import RoadNetworkError

BELO_HORIZONTE_CENTER = (-19.9167, -43.9345)
SEARCH_RESULT_LIMIT = 12
MAP_STYLE = "carto-positron"
BAR_COLOR = "#111827"
SELECTED_BAR_COLOR = "#f97316"
COURIER_COLOR = "#6b7280"
SELECTED_COURIER_COLOR = "#22c55e"
BAR_MARKER_SYMBOL = "restaurant"
COURIER_MARKER_SYMBOL = "bicycle"
DEFAULT_SEARCH_RADIUS_KM = 2.0
DEFAULT_MAP_ZOOM = 11.3
AVERAGE_COURIER_SPEED_KMH = 30.0

type CourierRecord = tuple[int, float, float, int, str]


def validate_courier_count(value: object) -> int:
    """Converte a entrada da interface em uma quantidade inteira não negativa."""
    if value is None or isinstance(value, bool):
        raise ValueError("Informe a quantidade de entregadores.")

    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Informe a quantidade de entregadores.")
        try:
            number = int(text)
        except ValueError as error:
            raise ValueError("Use um número inteiro para a quantidade.") from error
    elif isinstance(value, int):
        number = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        number = int(value)
    else:
        raise ValueError("Use um número inteiro para a quantidade.")

    if number < 0:
        raise ValueError("A quantidade não pode ser negativa.")
    return number


def validate_search_radius(value: object) -> float:
    """Converte a entrada da interface em um raio positivo, em quilômetros."""
    if value is None or isinstance(value, bool):
        raise ValueError("Informe o raio de busca.")
    try:
        radius = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Use um número para o raio de busca.") from error
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("O raio de busca deve ser maior que zero.")
    return radius


def estimated_arrival_minutes(distance_km: float) -> float:
    """Estima o tempo de chegada a 30 km/h usando a distância em linha reta."""
    if not math.isfinite(distance_km) or distance_km < 0:
        raise ValueError("distance_km deve ser um número finito e não negativo")
    return distance_km / AVERAGE_COURIER_SPEED_KMH * 60


def serialize_couriers(
    couriers: Sequence[Courier],
) -> list[dict[str, int | float | str]]:
    """Transforma entregadores em dados seguros para o armazenamento da sessão."""
    return [
        {
            "id": courier.id,
            "latitude": courier.latitude,
            "longitude": courier.longitude,
            "center_bar_id": courier.center_bar_id,
            "geohash": courier.geohash or "",
        }
        for courier in couriers
    ]


def restaurant_option(bar: Bar) -> dict[str, str | int]:
    """Cria uma opção concisa e pesquisável para o seletor de restaurantes."""
    return {
        "label": f"{bar.name} — {bar.address}",
        "value": bar.id,
        "title": f"{bar.name} — {bar.address}",
        "search": normalize_text(f"{bar.name} {bar.legal_name} {bar.address}"),
    }


def _selected_bar(bars_by_id: Mapping[int, Bar], selected_bar_id: int | str | None) -> Bar | None:
    if selected_bar_id is None:
        return None
    try:
        return bars_by_id.get(int(selected_bar_id))
    except (TypeError, ValueError):
        return None


def _courier_record(record: Mapping[str, Any]) -> CourierRecord:
    return (
        int(record["id"]),
        float(record["latitude"]),
        float(record["longitude"]),
        int(record["center_bar_id"]),
        str(record.get("geohash") or ""),
    )


@lru_cache(maxsize=8)
def _courier_index(records: tuple[CourierRecord, ...]) -> CourierSearchIndex:
    """Reutiliza a Trie enquanto a frota serializada da sessão não mudar."""
    return CourierSearchIndex(
        Courier(
            id=courier_id,
            latitude=latitude,
            longitude=longitude,
            center_bar_id=center_bar_id,
            geohash=geohash or None,
        )
        for courier_id, latitude, longitude, center_bar_id, geohash in records
    )


def _search_nearby_couriers(
    records: Sequence[Mapping[str, Any]],
    selected_bar: Bar | None,
    radius_km: float,
) -> list[CourierSearchResult]:
    """Busca uma vez os entregadores usados pelo mapa e pela tabela."""
    if selected_bar is None or selected_bar.coordinates is None or not records:
        return []

    assert selected_bar.latitude is not None
    assert selected_bar.longitude is not None
    courier_index = _courier_index(tuple(_courier_record(record) for record in records))
    return courier_index.search(
        selected_bar.latitude,
        selected_bar.longitude,
        radius_km,
    )


def _add_courier_trace(
    figure: go.Figure,
    records: Sequence[Mapping[str, Any]],
    bars_by_id: Mapping[int, Bar],
    *,
    color: str,
    highlighted: bool,
    name: str,
) -> None:
    if not records:
        return

    base_names = [
        (
            bars_by_id.get(int(record["center_bar_id"])).name
            if bars_by_id.get(int(record["center_bar_id"])) is not None
            else "Estabelecimento não identificado"
        )
        for record in records
    ]
    latitudes = [record["latitude"] for record in records]
    longitudes = [record["longitude"] for record in records]
    customdata = [
        [record["id"], record.get("geohash") or "—", base_name]
        for record, base_name in zip(records, base_names, strict=True)
    ]
    legend_group = f"couriers-{name}"

    if highlighted:
        # Os símbolos Maki desta versão do Plotly não recebem a cor do marcador.
        # Apenas o resultado da busca ganha o halo verde, sem adicionar um
        # fundo aos entregadores que não foram selecionados.
        figure.add_trace(
            go.Scattermap(
                lat=latitudes,
                lon=longitudes,
                mode="markers",
                marker={
                    "color": color,
                    "opacity": 0.9,
                    "size": 15,
                },
                customdata=customdata,
                hoverinfo="skip",
                legendgroup=legend_group,
                name=name,
            )
        )
    figure.add_trace(
        go.Scattermap(
            lat=latitudes,
            lon=longitudes,
            mode="markers",
            marker={
                "allowoverlap": True,
                "color": BAR_COLOR,
                "opacity": 1,
                "size": 8,
                "symbol": COURIER_MARKER_SYMBOL,
            },
            customdata=customdata,
            hovertemplate=(
                "<b>Entregador #%{customdata[0]}</b><br>"
                "Centro: %{customdata[2]}<br>"
                "Geohash: %{customdata[1]}<extra></extra>"
            ),
            legendgroup=legend_group,
            name=name,
            showlegend=False if highlighted else None,
        )
    )


def build_map_figure(
    bars_by_id: Mapping[int, Bar],
    courier_records: Sequence[Mapping[str, Any]] | None = None,
    selected_bar_id: int | str | None = None,
    search_radius_km: object = DEFAULT_SEARCH_RADIUS_KM,
    *,
    search_results: Sequence[CourierSearchResult] | None = None,
) -> go.Figure:
    """Monta o mapa com os bares, a frota corrente e o restaurante selecionado."""
    records = list(courier_records or ())
    selected = _selected_bar(bars_by_id, selected_bar_id)
    selected_with_coordinates = selected if selected and selected.coordinates else None
    if search_results is None:
        radius = validate_search_radius(search_radius_km)
        matches = _search_nearby_couriers(records, selected_with_coordinates, radius)
    else:
        matches = list(search_results)
    nearby_ids = {match.courier.id for match in matches}
    visible_bars = [
        bar
        for bar in bars_by_id.values()
        if bar.coordinates is not None
        and (selected_with_coordinates is None or bar.id != selected_with_coordinates.id)
    ]

    figure = go.Figure()
    if visible_bars:
        figure.add_trace(
            go.Scattermap(
                lat=[bar.latitude for bar in visible_bars],
                lon=[bar.longitude for bar in visible_bars],
                mode="markers",
                marker={
                    "allowoverlap": True,
                    "color": BAR_COLOR,
                    "opacity": 0.9,
                    "size": 8,
                    "symbol": BAR_MARKER_SYMBOL,
                },
                customdata=[[bar.name, bar.address] for bar in visible_bars],
                hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"),
                name="Restaurantes",
            )
        )

    regular_records = [record for record in records if int(record["id"]) not in nearby_ids]
    nearby_records = [record for record in records if int(record["id"]) in nearby_ids]
    _add_courier_trace(
        figure,
        regular_records,
        bars_by_id,
        color=COURIER_COLOR,
        highlighted=False,
        name=(
            "Entregadores fora do raio" if selected_with_coordinates is not None else "Entregadores"
        ),
    )
    _add_courier_trace(
        figure,
        nearby_records,
        bars_by_id,
        color=SELECTED_COURIER_COLOR,
        highlighted=True,
        name="Entregadores no raio",
    )

    if selected_with_coordinates is not None:
        assert selected_with_coordinates.latitude is not None
        assert selected_with_coordinates.longitude is not None
        selected_latitude = selected_with_coordinates.latitude
        selected_longitude = selected_with_coordinates.longitude
        selected_customdata = [[selected_with_coordinates.name, selected_with_coordinates.address]]
        figure.add_trace(
            go.Scattermap(
                lat=[selected_latitude],
                lon=[selected_longitude],
                mode="markers",
                marker={
                    "color": SELECTED_BAR_COLOR,
                    "size": 22,
                },
                customdata=selected_customdata,
                hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"),
                legendgroup="selected-restaurant",
                name="Restaurante selecionado",
            )
        )
        figure.add_trace(
            go.Scattermap(
                lat=[selected_latitude],
                lon=[selected_longitude],
                mode="markers",
                marker={
                    "allowoverlap": True,
                    "color": BAR_COLOR,
                    "size": 11,
                    "symbol": BAR_MARKER_SYMBOL,
                },
                customdata=selected_customdata,
                hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"),
                legendgroup="selected-restaurant",
                name="Ícone do restaurante selecionado",
                showlegend=False,
            )
        )

    if selected_with_coordinates is not None:
        center = {
            "lat": selected_with_coordinates.latitude,
            "lon": selected_with_coordinates.longitude,
        }
    else:
        center = {"lat": BELO_HORIZONTE_CENTER[0], "lon": BELO_HORIZONTE_CENTER[1]}
    zoom = DEFAULT_MAP_ZOOM

    # O Plotly só instancia o subplot MapLibre quando existe ao menos um
    # ``Scattermap``. Sem esta âncora, o estado inicial (sem restaurante e sem
    # entregadores) renderiza apenas uma área branca apesar de ``layout.map``.
    if not figure.data:
        figure.add_trace(
            go.Scattermap(
                lat=[center["lat"]],
                lon=[center["lon"]],
                mode="markers",
                marker={"size": 1, "opacity": 0},
                hoverinfo="skip",
                showlegend=False,
                name="Base do mapa",
            )
        )

    figure.update_layout(
        map={"style": MAP_STYLE, "center": center, "zoom": zoom},
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="#e8eeec",
        plot_bgcolor="#e8eeec",
        hovermode="closest",
        hoverlabel={
            "bgcolor": "#0f2942",
            "bordercolor": "#0f2942",
            "font": {"color": "#ffffff", "family": "Arial, sans-serif", "size": 13},
        },
        showlegend=False,
        uirevision="delivery-dispatch-map",
    )
    return figure


def build_courier_results_table(
    results: Sequence[CourierSearchResult],
    selected_bar: Bar | None,
    *,
    has_couriers: bool,
) -> html.Section:
    """Monta a tabela dos entregadores aprovados pelo filtro de distância."""
    result_count = len(results)
    heading = html.Div(
        [
            html.Div(
                [
                    html.P("RESULTADO DA BUSCA", className="results-kicker"),
                    html.H3("Entregadores dentro do raio"),
                ]
            ),
            html.Span(
                (
                    f"{result_count} encontrado"
                    if result_count == 1
                    else f"{result_count} encontrados"
                ),
                className="results-count",
            ),
        ],
        className="results-heading",
    )

    if selected_bar is None:
        content: Any = html.P(
            "Selecione um restaurante para consultar os entregadores mais próximos.",
            className="results-empty",
        )
    elif selected_bar.coordinates is None:
        content = html.P(
            "O restaurante selecionado não possui coordenadas para a consulta.",
            className="results-empty",
        )
    elif not has_couriers:
        content = html.P(
            "Gere uma frota para preencher a tabela de resultados.",
            className="results-empty",
        )
    elif not results:
        content = html.P(
            "Nenhum entregador foi encontrado dentro do raio informado.",
            className="results-empty",
        )
    else:
        rows = [
            html.Tr(
                [
                    html.Td(f"#{result.courier.id}"),
                    html.Td(f"{result.distance_km:.3f}"),
                    html.Td(f"{estimated_arrival_minutes(result.distance_km):.1f}"),
                    html.Td(f"{result.courier.latitude:.6f}"),
                    html.Td(f"{result.courier.longitude:.6f}"),
                    html.Td(result.courier.geohash or "—", className="results-geohash"),
                ]
            )
            for result in results
        ]
        content = html.Div(
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("ID", scope="col"),
                                html.Th("Distância (km)", scope="col"),
                                html.Th("Tempo estimado (min)", scope="col"),
                                html.Th("Latitude", scope="col"),
                                html.Th("Longitude", scope="col"),
                                html.Th("Geohash", scope="col"),
                            ]
                        )
                    ),
                    html.Tbody(rows),
                ]
            ),
            className="results-table-scroll",
        )

    return html.Section(
        [heading, content],
        id="courier-results",
        className="courier-results",
        **{"aria-live": "polite"},
    )


def _empty_restaurant_card() -> html.Div:
    return html.Div(
        [
            html.Div(className="selection-pin selection-pin--empty"),
            html.Div(
                [
                    html.P("Nenhum restaurante selecionado", className="selection-title"),
                    html.P(
                        "Busque acima para destacar um ponto no mapa.",
                        className="selection-copy",
                    ),
                ]
            ),
        ],
        className="selection-card selection-card--empty",
    )


def _restaurant_card(bar: Bar) -> html.Div:
    location_label = "No mapa" if bar.coordinates else "Sem coordenadas"
    location_class = "tag tag--success" if bar.coordinates else "tag tag--warning"
    return html.Div(
        [
            html.Div(className="selection-pin"),
            html.Div(
                [
                    html.P("RESTAURANTE SELECIONADO", className="selection-eyebrow"),
                    html.H3(bar.name, className="selection-name"),
                    html.P(bar.address, className="selection-address"),
                    html.Div(
                        [
                            html.Span(bar.neighborhood.title(), className="tag"),
                            html.Span(location_label, className=location_class),
                        ],
                        className="tag-row",
                    ),
                ],
                className="selection-content",
            ),
        ],
        className="selection-card",
    )


def _layout(bars_by_id: Mapping[int, Bar]) -> html.Div:
    total_bars = len(bars_by_id)
    located_bars = sum(bar.coordinates is not None for bar in bars_by_id.values())
    return html.Div(
        [
            dcc.Store(id="courier-store", data=[], storage_type="memory"),
            html.Header(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(className="brand-node brand-node--one"),
                                    html.Span(className="brand-route"),
                                    html.Span(className="brand-node brand-node--two"),
                                ],
                                className="brand-mark",
                                **{"aria-hidden": "true"},
                            ),
                            html.Div(
                                [
                                    html.Span("Delivery", className="brand-name"),
                                    html.Span(
                                        "Dispatch",
                                        className="brand-name brand-name--accent",
                                    ),
                                ],
                                className="brand-wordmark",
                            ),
                        ],
                        className="brand",
                    ),
                    html.Div(
                        [
                            html.Span(className="live-dot"),
                            html.Span("BASE DE BELO HORIZONTE"),
                        ],
                        className="dataset-badge",
                    ),
                ],
                className="app-header",
            ),
            html.Main(
                [
                    html.Aside(
                        [
                            html.Div(
                                [
                                    html.P("PAINEL DE OPERAÇÃO", className="kicker"),
                                ],
                                className="intro",
                            ),
                            html.Section(
                                [
                                    html.Div(
                                        [
                                            html.Span("01", className="step-number"),
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Encontrar restaurante",
                                                        htmlFor="restaurant-search",
                                                        className="field-label",
                                                    ),
                                                    html.P(
                                                        "Pesquise pelo nome ou endereço",
                                                        className="field-hint",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="section-heading",
                                    ),
                                    dcc.Dropdown(
                                        id="restaurant-search",
                                        options=[],
                                        placeholder="Ex.: Portugal, Savassi ou Café",
                                        searchable=True,
                                        clearable=True,
                                        optionHeight=64,
                                        maxHeight=320,
                                        className="restaurant-dropdown",
                                    ),
                                    html.Div(_empty_restaurant_card(), id="restaurant-card"),
                                    html.Label(
                                        "Raio de busca dos entregadores",
                                        htmlFor="search-radius",
                                        className="field-label radius-label",
                                    ),
                                    html.P(
                                        "Distância máxima em relação ao restaurante",
                                        className="field-hint",
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="search-radius",
                                                type="number",
                                                min=0.1,
                                                step=0.1,
                                                value=DEFAULT_SEARCH_RADIUS_KM,
                                                debounce=True,
                                                inputMode="decimal",
                                            ),
                                            html.Span("KM", className="input-suffix"),
                                        ],
                                        className="number-field radius-field",
                                    ),
                                ],
                                className="control-section",
                            ),
                            html.Div(className="section-divider"),
                            html.Section(
                                [
                                    html.Div(
                                        [
                                            html.Span("02", className="step-number"),
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Simular frota",
                                                        htmlFor="courier-count",
                                                        className="field-label",
                                                    ),
                                                    html.P(
                                                        "A geração substitui a frota atual",
                                                        className="field-hint",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        className="section-heading",
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="courier-count",
                                                type="number",
                                                min=0,
                                                step=1,
                                                value=100,
                                                debounce=True,
                                                inputMode="numeric",
                                            ),
                                            html.Span("ENTREGADORES", className="input-suffix"),
                                        ],
                                        className="number-field",
                                    ),
                                    html.Button(
                                        [
                                            html.Span(className="button-icon"),
                                            html.Span(
                                                "Gerar entregadores",
                                                id="generate-button-label",
                                            ),
                                        ],
                                        id="generate-couriers",
                                        n_clicks=0,
                                        className="primary-button",
                                        type="button",
                                    ),
                                    html.Div(
                                        [
                                            html.Span(className="feedback-icon"),
                                            html.Span(
                                                "Informe o tamanho da frota e inicie a simulação."
                                            ),
                                        ],
                                        id="generation-feedback",
                                        className="generation-feedback",
                                        role="status",
                                        **{"aria-live": "polite"},
                                    ),
                                ],
                                className="control-section",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Strong(f"{located_bars:,}".replace(",", ".")),
                                            html.Span("no mapa"),
                                        ],
                                        className="data-stat",
                                    ),
                                    html.Div(className="data-rule"),
                                    html.Div(
                                        [
                                            html.Strong(f"{total_bars:,}".replace(",", ".")),
                                            html.Span("na base"),
                                        ],
                                        className="data-stat",
                                    ),
                                    html.P("Dados: Prefeitura de BH · OpenStreetMap"),
                                ],
                                className="data-summary",
                            ),
                        ],
                        className="sidebar",
                    ),
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                "MAPA OPERACIONAL",
                                                className="map-kicker",
                                            ),
                                            html.H2("Belo Horizonte"),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Strong("0", id="courier-total"),
                                            html.Span("entregadores na simulação"),
                                        ],
                                        className="fleet-counter",
                                    ),
                                ],
                                className="map-toolbar",
                            ),
                            html.Div(
                                [
                                    dcc.Loading(
                                        dcc.Graph(
                                            id="dispatch-map",
                                            figure=build_map_figure(bars_by_id),
                                            config={
                                                "displaylogo": False,
                                                "scrollZoom": True,
                                                "modeBarButtonsToRemove": [
                                                    "select2d",
                                                    "lasso2d",
                                                    "autoScale2d",
                                                ],
                                            },
                                            responsive=True,
                                            className="dispatch-map",
                                            style={"height": "580px"},
                                        ),
                                        type="circle",
                                        color="#0f766e",
                                        parent_className="map-loading",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Img(
                                                        src="/assets/restaurant-marker.svg",
                                                        alt="",
                                                    ),
                                                    html.Span("Restaurantes"),
                                                ],
                                                className="map-legend-item",
                                            ),
                                            html.Div(
                                                [
                                                    html.Img(
                                                        src="/assets/bicycle-marker.svg",
                                                        alt="",
                                                    ),
                                                    html.Span("Entregadores"),
                                                ],
                                                className="map-legend-item",
                                            ),
                                        ],
                                        className="map-legend",
                                        **{"aria-label": "Legenda do mapa"},
                                    ),
                                    html.Div(
                                        [
                                            html.Span(className="tip-icon"),
                                            html.Span(
                                                "Role para aproximar e arraste para "
                                                "explorar o mapa."
                                            ),
                                        ],
                                        className="map-tip",
                                    ),
                                ],
                                className="map-stage",
                            ),
                            build_courier_results_table(
                                [],
                                None,
                                has_couriers=False,
                            ),
                        ],
                        className="map-panel",
                    ),
                ],
                className="workspace",
            ),
        ],
        className="app-shell",
    )


def create_app(
    bars: Sequence[Bar],
    road_projector: RoadProjector,
    *,
    assets_folder: str | Path | None = None,
) -> Dash:
    """Cria a aplicação Dash sem iniciar o servidor."""
    all_bars = list(bars)
    bars_by_id = {bar.id: bar for bar in all_bars}
    located_bars = [bar for bar in all_bars if bar.coordinates is not None]
    search_index = BarSearchIndex(all_bars)
    generation_lock = threading.Lock()

    assets_path = Path(assets_folder) if assets_folder else Path(__file__).with_name("assets")
    app = Dash(
        __name__,
        assets_folder=str(assets_path),
        title="DeliveryDispatch · Painel operacional",
        update_title="Atualizando mapa…",
    )
    app.layout = _layout(bars_by_id)

    @app.callback(
        Output("restaurant-search", "options"),
        Input("restaurant-search", "search_value"),
        State("restaurant-search", "value"),
    )
    def update_restaurant_options(
        search_value: str | None, selected_bar_id: int | None
    ) -> list[dict[str, str | int]]:
        matches = (
            search_index.search(search_value, limit=SEARCH_RESULT_LIMIT)
            if search_value and len(search_value.strip()) >= 2
            else []
        )
        selected = _selected_bar(bars_by_id, selected_bar_id)
        if selected is not None and all(bar.id != selected.id for bar in matches):
            matches.insert(0, selected)
        return [restaurant_option(bar) for bar in matches]

    @app.callback(
        Output("dispatch-map", "figure"),
        Output("restaurant-card", "children"),
        Output("courier-results", "children"),
        Input("restaurant-search", "value"),
        Input("courier-store", "data"),
        Input("search-radius", "value"),
    )
    def update_map(
        selected_bar_id: int | None,
        courier_records: list[dict[str, int | float | str]] | None,
        search_radius_km: int | float | str | None,
    ) -> tuple[go.Figure, html.Div, list[Any]]:
        started_at = time.perf_counter()
        selected = _selected_bar(bars_by_id, selected_bar_id)
        card = _restaurant_card(selected) if selected else _empty_restaurant_card()
        try:
            radius = validate_search_radius(search_radius_km)
        except ValueError:
            radius = DEFAULT_SEARCH_RADIUS_KM
        records = list(courier_records or ())
        results = _search_nearby_couriers(records, selected, radius)
        results_table = build_courier_results_table(
            results,
            selected,
            has_couriers=bool(records),
        )
        figure = build_map_figure(
            bars_by_id,
            records,
            selected_bar_id,
            radius,
            search_results=results,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1_000
        print(
            f"[consulta] raio={radius:.1f} km | encontrados={len(results)} | "
            f"tempo={elapsed_ms:.1f} ms",
            flush=True,
        )
        return (
            figure,
            card,
            results_table.children,
        )

    @app.callback(
        Output("courier-store", "data"),
        Output("generation-feedback", "children"),
        Output("generation-feedback", "className"),
        Output("courier-total", "children"),
        Input("generate-couriers", "n_clicks"),
        State("courier-count", "value"),
        prevent_initial_call=True,
        running=[
            (Output("generate-couriers", "disabled"), True, False),
            (
                Output("generate-button-label", "children"),
                "Gerando…",
                "Gerar entregadores",
            ),
        ],
    )
    def regenerate_couriers(
        clicks: int, count_value: int | float | str | None
    ) -> tuple[
        list[dict[str, int | float | str]] | Any,
        list[Any],
        str,
        str | Any,
    ]:
        try:
            count = validate_courier_count(count_value)
            with generation_lock:
                # Cada clique representa uma nova simulação. Usar o contador como
                # semente evita repetir a mesma distribuição quando N não muda.
                couriers = generate_couriers(
                    count,
                    located_bars,
                    road_projector,
                    seed=clicks,
                )
        except (OSError, ValueError, RoadNetworkError) as error:
            return (
                no_update,
                [html.Span(className="feedback-icon"), html.Span(str(error))],
                "generation-feedback generation-feedback--error",
                no_update,
            )

        if count == 0:
            message = "A frota foi limpa. Informe um novo N quando quiser simular."
        elif count == 1:
            message = "1 entregador foi gerado e posicionado na malha viária."
        else:
            message = (
                f"{count:,} entregadores foram gerados e posicionados na malha viária."
            ).replace(",", ".")
        return (
            serialize_couriers(couriers),
            [html.Span(className="feedback-icon"), html.Span(message)],
            "generation-feedback generation-feedback--success",
            f"{count:,}".replace(",", "."),
        )

    return app
