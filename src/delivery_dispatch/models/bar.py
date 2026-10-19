"""Modelo de um bar ou restaurante da base municipal."""

from dataclasses import dataclass
from typing import Literal

GeocodingStatus = Literal["pending", "found", "not_found"]

STREET_TYPE_NAMES = {
    "ALA": "Alameda",
    "AVE": "Avenida",
    "BEC": "Beco",
    "EST": "Estrada",
    "PCA": "Praça",
    "ROD": "Rodovia",
    "RUA": "Rua",
    "TRV": "Travessa",
    "VDP": "Via de Pedestre",
    "VIA": "Via",
}


@dataclass(frozen=True, slots=True)
class Bar:
    """Representa um estabelecimento e, quando disponível, sua localização."""

    id: int
    cnae_code: int
    cnae_description: str
    street_type: str
    street_name: str
    street_number: str
    neighborhood: str
    legal_name: str
    trade_name: str | None = None
    complement: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geohash: str | None = None
    geocoding_status: GeocodingStatus = "pending"

    @property
    def name(self) -> str:
        """Retorna o nome de exibição preferencial do estabelecimento."""
        return self.trade_name or self.legal_name

    @property
    def address(self) -> str:
        """Retorna o endereço completo para exibição."""
        street_type = STREET_TYPE_NAMES.get(self.street_type, self.street_type)
        parts = [f"{street_type} {self.street_name}, {self.street_number}"]
        if self.complement:
            parts.append(self.complement)
        parts.extend([self.neighborhood, "Belo Horizonte - MG", "Brasil"])
        return ", ".join(parts)

    @property
    def geocoding_query(self) -> str:
        """Retorna um endereço sem complemento, mais adequado à geocodificação."""
        street_type = STREET_TYPE_NAMES.get(self.street_type, self.street_type)
        return ", ".join(
            [
                f"{street_type} {self.street_name}, {self.street_number}",
                self.neighborhood,
                "Belo Horizonte",
                "Minas Gerais",
                "Brasil",
            ]
        )

    @property
    def coordinates(self) -> tuple[float, float] | None:
        """Retorna ``(latitude, longitude)`` quando o bar foi geocodificado."""
        if self.latitude is None or self.longitude is None:
            return None
        return self.latitude, self.longitude
