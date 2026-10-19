"""Geração espacial de entregadores ao redor dos bares geocodificados."""

import math
import random
from collections.abc import Sequence
from typing import Protocol

from delivery_dispatch.algorithms.geohash import encode
from delivery_dispatch.models.bar import Bar
from delivery_dispatch.models.courier import Courier

METERS_PER_LATITUDE_DEGREE = 111_320.0
DEFAULT_STANDARD_DEVIATION_METERS = 500.0
DEFAULT_RANDOM_SEED = 42

Coordinates = tuple[float, float]


class RoadProjector(Protocol):
    """Projeta coordenadas matemáticas para posições válidas na malha viária."""

    def project(self, coordinates: Sequence[Coordinates]) -> list[Coordinates]: ...


def generate_couriers(
    count: int,
    bars: Sequence[Bar],
    road_projector: RoadProjector,
    *,
    standard_deviation_meters: float = DEFAULT_STANDARD_DEVIATION_METERS,
    seed: int = DEFAULT_RANDOM_SEED,
) -> list[Courier]:
    """Gera ``count`` entregadores normalmente distribuídos ao redor dos bares.

    Os entregadores são divididos de forma equilibrada entre os bares disponíveis.
    Os pontos matemáticos resultantes são projetados para a via transitável mais próxima.
    """
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count deve ser um inteiro")
    if count < 0:
        raise ValueError("count não pode ser negativo")
    if not math.isfinite(standard_deviation_meters) or standard_deviation_meters < 0:
        raise ValueError("standard_deviation_meters deve ser finito e não negativo")
    if count == 0:
        return []

    centers = [bar for bar in bars if bar.coordinates is not None]
    if not centers:
        raise ValueError("não há bares com coordenadas para distribuir os entregadores")

    random_generator = random.Random(seed)
    random_generator.shuffle(centers)
    generated_coordinates: list[Coordinates] = []
    center_ids: list[int] = []

    for index in range(count):
        center = centers[index % len(centers)]
        latitude = center.latitude
        longitude = center.longitude
        assert latitude is not None and longitude is not None

        latitude_offset = random_generator.gauss(0, standard_deviation_meters)
        longitude_offset = random_generator.gauss(0, standard_deviation_meters)
        longitude_degree_size = METERS_PER_LATITUDE_DEGREE * max(
            abs(math.cos(math.radians(latitude))),
            1e-12,
        )
        generated_coordinates.append(
            (
                latitude + latitude_offset / METERS_PER_LATITUDE_DEGREE,
                longitude + longitude_offset / longitude_degree_size,
            )
        )
        center_ids.append(center.id)

    corrected_coordinates = road_projector.project(generated_coordinates)
    if len(corrected_coordinates) != count:
        raise ValueError("o projetor viário retornou uma quantidade incorreta de coordenadas")

    return [
        Courier(
            id=index + 1,
            latitude=latitude,
            longitude=longitude,
            center_bar_id=center_ids[index],
            geohash=encode(latitude, longitude),
        )
        for index, (latitude, longitude) in enumerate(corrected_coordinates)
    ]
