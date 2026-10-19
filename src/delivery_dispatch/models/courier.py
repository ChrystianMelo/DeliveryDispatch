"""Modelo de um entregador simulado."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Courier:
    """Representa a posição viária de um entregador e seu bar de referência."""

    id: int
    latitude: float
    longitude: float
    center_bar_id: int
    geohash: str | None = None

    @property
    def coordinates(self) -> tuple[float, float]:
        return self.latitude, self.longitude
