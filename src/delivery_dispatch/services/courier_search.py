"""Busca geoespacial de entregadores indexados por Geohash."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from delivery_dispatch.algorithms.compact_trie import CompactTrie
from delivery_dispatch.algorithms.geohash import MAX_LEVELS, encode
from delivery_dispatch.models.courier import Courier

EARTH_RADIUS_KM = 6371.0088
_UNIQUE_SEPARATOR = "\x01"


@dataclass(frozen=True, slots=True)
class CourierSearchResult:
    """Entregador aprovado pelo filtro e sua distância até o restaurante."""

    courier: Courier
    distance_km: float


def _validate_radius(radius_km: float) -> float:
    if isinstance(radius_km, bool) or not isinstance(radius_km, (int, float)):
        raise TypeError("radius_km deve ser um número")
    radius = float(radius_km)
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("radius_km deve ser finito e maior que zero")
    return radius


def _validate_latitude(latitude: float) -> float:
    """Valida uma latitude em graus e retorna seu valor convertido para ``float``."""
    if isinstance(latitude, bool) or not isinstance(latitude, (int, float)):
        raise TypeError("latitude deve ser um número")
    value = float(latitude)
    if not math.isfinite(value) or not -90.0 <= value <= 90.0:
        raise ValueError("latitude deve ser finita e estar entre -90 e 90")
    return value


def _validate_coordinates(latitude: float, longitude: float) -> None:
    # Reutiliza o mesmo contrato de domínio da codificação Geohash.
    encode(latitude, longitude, 1)


def _haversine_distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    first_latitude_radians, second_latitude_radians = map(
        math.radians, (first_latitude, second_latitude)
    )
    latitude_delta = second_latitude_radians - first_latitude_radians
    longitude_delta = math.radians(second_longitude - first_longitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_latitude_radians)
        * math.cos(second_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(haversine)))


def haversine_distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    """Retorna a distância do grande círculo entre dois pontos, em quilômetros."""
    _validate_coordinates(first_latitude, first_longitude)
    _validate_coordinates(second_latitude, second_longitude)
    return _haversine_distance_km(
        first_latitude,
        first_longitude,
        second_latitude,
        second_longitude,
    )


def _grid_shape(precision: int) -> tuple[int, int, float, float]:
    total_bits = precision * 5
    longitude_bits = (total_bits + 1) // 2
    latitude_bits = total_bits // 2
    latitude_cells = 2**latitude_bits
    longitude_cells = 2**longitude_bits
    return (
        latitude_cells,
        longitude_cells,
        180.0 / latitude_cells,
        360.0 / longitude_cells,
    )


def geohash_precision_for_radius(latitude: float, radius_km: float) -> int:
    """Escolhe o prefixo mais preciso cuja célula ainda cobre um raio por eixo.

    Com essa escolha, uma busca local costuma visitar apenas a célula do ponto e
    suas oito adjacentes. A cobertura continua correta para raios maiores, pois
    :func:`geohash_grid_prefixes` expande a grade quando necessário.
    """
    valid_latitude = _validate_latitude(latitude)
    radius = _validate_radius(radius_km)
    latitude_radians = math.radians(valid_latitude)
    precision = 1

    for candidate in range(1, MAX_LEVELS + 1):
        _, _, latitude_span, longitude_span = _grid_shape(candidate)
        height_km = EARTH_RADIUS_KM * math.radians(latitude_span)
        width_km = EARTH_RADIUS_KM * math.radians(longitude_span) * abs(math.cos(latitude_radians))
        if min(height_km, width_km) < radius:
            break
        precision = candidate

    return precision


def geohash_grid_prefixes(
    latitude: float,
    longitude: float,
    radius_km: float,
) -> tuple[str, ...]:
    """Retorna as células Geohash que cobrem o retângulo envolvente do raio.

    Os prefixos têm a mesma precisão e incluem a célula do ponto e todas as
    células adjacentes que podem interceptar o círculo consultado. Isso evita o
    falso negativo de pontos próximos separados por uma borda da grade.
    """
    _validate_coordinates(latitude, longitude)
    radius = _validate_radius(radius_km)
    precision = geohash_precision_for_radius(latitude, radius)
    latitude_cells, longitude_cells, latitude_span, longitude_span = _grid_shape(precision)

    latitude_index = min(
        latitude_cells - 1,
        max(0, math.floor((latitude + 90.0) / latitude_span)),
    )
    longitude_index = min(
        longitude_cells - 1,
        max(0, math.floor((longitude + 180.0) / longitude_span)),
    )

    angular_radius = min(radius / EARTH_RADIUS_KM, math.pi)
    latitude_delta = math.degrees(angular_radius)
    latitude_steps = math.ceil(latitude_delta / latitude_span)
    latitude_indexes = range(
        max(0, latitude_index - latitude_steps),
        min(latitude_cells - 1, latitude_index + latitude_steps) + 1,
    )

    reaches_a_pole = latitude - latitude_delta <= -90.0 or latitude + latitude_delta >= 90.0
    if angular_radius >= math.pi / 2 or reaches_a_pole:
        longitude_indexes: Iterable[int] = range(longitude_cells)
    else:
        longitude_delta = math.degrees(
            math.asin(
                min(
                    1.0,
                    abs(math.sin(angular_radius) / math.cos(math.radians(latitude))),
                )
            )
        )
        longitude_steps = math.ceil(longitude_delta / longitude_span)
        longitude_indexes = {
            (longitude_index + offset) % longitude_cells
            for offset in range(-longitude_steps, longitude_steps + 1)
        }

    prefixes = {
        encode(
            -90.0 + (latitude_cell + 0.5) * latitude_span,
            -180.0 + (longitude_cell + 0.5) * longitude_span,
            precision,
        )
        for latitude_cell in latitude_indexes
        for longitude_cell in longitude_indexes
    }
    return tuple(sorted(prefixes))


class CourierSearchIndex:
    """Índice de entregadores em uma Trie compacta de Geohashes completos."""

    def __init__(self, couriers: Iterable[Courier]) -> None:
        self._tree = CompactTrie[Courier]()

        for position, courier in enumerate(couriers):
            geohash = encode(courier.latitude, courier.longitude)
            # O sufixo preserva entregadores diferentes que ocupam a mesma célula.
            self._tree.insert(f"{geohash}{_UNIQUE_SEPARATOR}{position}", courier)

    def candidates(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[Courier]:
        """Coleta nas subárvores da grade os candidatos à filtragem geométrica."""
        candidates: list[Courier] = []
        seen_ids: set[int] = set()

        for prefix in geohash_grid_prefixes(latitude, longitude, radius_km):
            for node in self._tree.search_prefix(prefix):
                courier = node.value
                if courier is None or courier.id in seen_ids:
                    continue
                candidates.append(courier)
                seen_ids.add(courier.id)

        return candidates

    def search(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
    ) -> list[CourierSearchResult]:
        """Retorna entregadores no raio e suas distâncias, do mais próximo ao mais distante."""
        radius = _validate_radius(radius_km)
        matches = [
            CourierSearchResult(
                courier=courier,
                distance_km=_haversine_distance_km(
                    latitude,
                    longitude,
                    courier.latitude,
                    courier.longitude,
                ),
            )
            for courier in self.candidates(latitude, longitude, radius)
        ]
        matches = [match for match in matches if match.distance_km <= radius]
        matches.sort(key=lambda match: (match.distance_km, match.courier.id))
        return matches
