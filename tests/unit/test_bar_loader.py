"""Testes dos fluxos principais de leitura e persistência dos bares."""

from dataclasses import replace
from pathlib import Path

import pytest

from delivery_dispatch.algorithms.geohash import encode
from delivery_dispatch.data.bar_loader import load_bars, prepare_bars_csv, save_bars

CSV_CONTENT = (
    "_id,CNAE_PRINCIPAL,DESCRICAO_CNAE_PRINCIPAL,DESC_LOGRADOURO,"
    "NOME_LOGRADOURO,NUMERO_IMOVEL,COMPLEMENTO,NOME_BAIRRO,NOME,NOME_FANTASIA\n"
    "12,5611201,RESTAURANTES E SIMILARES,AVE,PORTUGAL,4316,,JARDIM ATLANTICO,"
    "BAR E CAFE DONATELO LTDA,\n"
    "32,5611201,RESTAURANTES E SIMILARES,RUA,VINTE E OITO DE SETEMBRO,606,LOJA,"
    "ESPLANADA,PALLATE COMERCIO LTDA,PALLATE\n"
)


class FakeGeocoder:
    def __init__(self):
        self.queries: list[str] = []

    def geocode(self, query: str) -> tuple[float, float]:
        self.queries.append(query)
        return -19.9, -43.9


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "bares.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


def test_load_bars_maps_csv_fields(csv_path):
    bars = load_bars(csv_path)

    assert len(bars) == 2
    assert bars[0].id == 12
    assert bars[0].name == "BAR E CAFE DONATELO LTDA"
    assert bars[0].address == (
        "Avenida PORTUGAL, 4316, JARDIM ATLANTICO, Belo Horizonte - MG, Brasil"
    )
    assert bars[0].coordinates is None
    assert bars[1].name == "PALLATE"
    assert bars[1].complement == "LOJA"


def test_save_and_load_preserves_processed_bars(csv_path, tmp_path):
    bar = replace(
        load_bars(csv_path)[0],
        latitude=-19.9,
        longitude=-43.9,
        geohash=encode(-19.9, -43.9),
        geocoding_status="found",
    )
    processed_path = tmp_path / "processed" / "bares_geocodificados.csv"

    save_bars([bar], processed_path)

    assert load_bars(processed_path) == [bar]


def test_prepare_bars_csv_resumes_only_pending_records(csv_path, tmp_path):
    processed_path = tmp_path / "bares_geocodificados.csv"
    first_geocoder = FakeGeocoder()

    first_bars = prepare_bars_csv(
        csv_path,
        processed_path,
        geocoder=first_geocoder,
        geocode_limit=1,
    )

    assert [bar.geocoding_status for bar in first_bars] == ["found", "pending"]
    assert len(first_geocoder.queries) == 1

    second_geocoder = FakeGeocoder()
    second_bars = prepare_bars_csv(
        csv_path,
        processed_path,
        geocoder=second_geocoder,
        geocode_limit=1,
    )

    assert [bar.geocoding_status for bar in second_bars] == ["found", "found"]
    assert len(second_geocoder.queries) == 1
