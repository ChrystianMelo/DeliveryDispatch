"""Leitura da base de bares e construção dos modelos da aplicação."""

import csv
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Protocol, cast

from delivery_dispatch.algorithms.geohash import encode
from delivery_dispatch.models.bar import Bar, GeocodingStatus

REQUIRED_COLUMNS = {
    "_id",
    "CNAE_PRINCIPAL",
    "DESCRICAO_CNAE_PRINCIPAL",
    "DESC_LOGRADOURO",
    "NOME_LOGRADOURO",
    "NUMERO_IMOVEL",
    "COMPLEMENTO",
    "NOME_BAIRRO",
    "NOME",
    "NOME_FANTASIA",
}
PROCESSED_COLUMNS = (
    "_id",
    "CNAE_PRINCIPAL",
    "DESCRICAO_CNAE_PRINCIPAL",
    "DESC_LOGRADOURO",
    "NOME_LOGRADOURO",
    "NUMERO_IMOVEL",
    "COMPLEMENTO",
    "NOME_BAIRRO",
    "NOME",
    "NOME_FANTASIA",
    "LATITUDE",
    "LONGITUDE",
    "GEOCODING_STATUS",
)
GEOCODING_STATUSES = {"pending", "found", "not_found"}
GEOCODING_CHECKPOINT_INTERVAL = 100


class Geocoder(Protocol):
    """Contrato mínimo aceito pelo carregador de bares."""

    def geocode(self, query: str) -> tuple[float, float] | None:
        """Converte um endereço em ``(latitude, longitude)``."""


def _optional(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _bar_from_row(row: Mapping[str, str | None], line_number: int) -> Bar:
    try:
        latitude_text = _optional(row.get("LATITUDE"))
        longitude_text = _optional(row.get("LONGITUDE"))
        if (latitude_text is None) != (longitude_text is None):
            raise ValueError("latitude e longitude devem estar ambas preenchidas")

        latitude = float(latitude_text) if latitude_text is not None else None
        longitude = float(longitude_text) if longitude_text is not None else None
        geohash = (
            encode(latitude, longitude) if latitude is not None and longitude is not None else None
        )

        default_status = "found" if latitude is not None else "pending"
        status_text = (_optional(row.get("GEOCODING_STATUS")) or default_status).lower()
        if status_text not in GEOCODING_STATUSES:
            raise ValueError("status de geocodificação inválido")
        status = cast(GeocodingStatus, status_text)

        return Bar(
            id=int(row["_id"] or ""),
            cnae_code=int(row["CNAE_PRINCIPAL"] or ""),
            cnae_description=(row["DESCRICAO_CNAE_PRINCIPAL"] or "").strip(),
            street_type=(row["DESC_LOGRADOURO"] or "").strip(),
            street_name=(row["NOME_LOGRADOURO"] or "").strip(),
            street_number=(row["NUMERO_IMOVEL"] or "").strip(),
            complement=_optional(row["COMPLEMENTO"]),
            neighborhood=(row["NOME_BAIRRO"] or "").strip(),
            legal_name=(row["NOME"] or "").strip(),
            trade_name=_optional(row["NOME_FANTASIA"]),
            latitude=latitude,
            longitude=longitude,
            geohash=geohash,
            geocoding_status=status,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"linha {line_number} inválida no CSV de bares") from error


def load_bars(
    csv_path: str | Path,
    *,
    geocoder: Geocoder | None = None,
    limit: int | None = None,
) -> list[Bar]:
    """Cria uma coleção de bares a partir do CSV.

    Quando ``geocoder`` é informado, cada endereço é consultado durante a
    construção da coleção. Bares não encontrados continuam na lista, mas sem
    coordenadas e sem Geohash.
    """
    if isinstance(limit, bool) or (limit is not None and not isinstance(limit, int)):
        raise TypeError("limit deve ser um inteiro ou None")
    if limit is not None and limit < 0:
        raise ValueError("limit não pode ser negativo")

    path = Path(csv_path)
    bars: list[Bar] = []

    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"colunas ausentes no CSV de bares: {missing}")

        for line_number, row in enumerate(reader, start=2):
            if limit is not None and len(bars) >= limit:
                break

            bar = _bar_from_row(row, line_number)
            if geocoder is not None:
                coordinates = geocoder.geocode(bar.geocoding_query)
                if coordinates is not None:
                    latitude, longitude = coordinates
                    bar = replace(
                        bar,
                        latitude=latitude,
                        longitude=longitude,
                        geohash=encode(latitude, longitude),
                        geocoding_status="found",
                    )
                else:
                    bar = replace(bar, geocoding_status="not_found")
            bars.append(bar)

    return bars


def save_bars(bars: list[Bar], csv_path: str | Path) -> None:
    """Salva os bares, suas coordenadas e o estado da geocodificação."""
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PROCESSED_COLUMNS)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "_id": bar.id,
                    "CNAE_PRINCIPAL": bar.cnae_code,
                    "DESCRICAO_CNAE_PRINCIPAL": bar.cnae_description,
                    "DESC_LOGRADOURO": bar.street_type,
                    "NOME_LOGRADOURO": bar.street_name,
                    "NUMERO_IMOVEL": bar.street_number,
                    "COMPLEMENTO": bar.complement or "",
                    "NOME_BAIRRO": bar.neighborhood,
                    "NOME": bar.legal_name,
                    "NOME_FANTASIA": bar.trade_name or "",
                    "LATITUDE": bar.latitude if bar.latitude is not None else "",
                    "LONGITUDE": bar.longitude if bar.longitude is not None else "",
                    "GEOCODING_STATUS": bar.geocoding_status,
                }
            )

    temporary_path.replace(path)


def prepare_bars_csv(
    raw_csv_path: str | Path,
    processed_csv_path: str | Path,
    *,
    geocoder: Geocoder | None = None,
    geocode_limit: int | None = None,
    force: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[Bar]:
    """Cria ou atualiza o CSV processado e retorna todos os bares.

    Na primeira execução, copia toda a base original para o arquivo processado.
    Se um geocodificador for informado, consulta apenas registros pendentes e
    salva checkpoints durante o processamento e persiste o resultado final.
    Assim, chamadas posteriores retomam do primeiro endereço ainda pendente.
    """
    if isinstance(geocode_limit, bool) or (
        geocode_limit is not None and not isinstance(geocode_limit, int)
    ):
        raise TypeError("geocode_limit deve ser um inteiro ou None")
    if geocode_limit is not None and geocode_limit < 0:
        raise ValueError("geocode_limit não pode ser negativo")

    processed_path = Path(processed_csv_path)
    if processed_path.exists() and not force:
        bars = load_bars(processed_path)
        changed = False
    else:
        bars = load_bars(raw_csv_path)
        changed = True

    if geocoder is not None:
        attempted = 0
        total_bars = len(bars)
        completed_before = sum(bar.geocoding_status != "pending" for bar in bars)
        if progress_callback is not None:
            progress_callback(completed_before, total_bars)

        for index, bar in enumerate(bars):
            if bar.geocoding_status != "pending":
                continue
            if geocode_limit is not None and attempted >= geocode_limit:
                break

            coordinates = geocoder.geocode(bar.geocoding_query)
            attempted += 1
            changed = True
            if coordinates is None:
                bars[index] = replace(bar, geocoding_status="not_found")
            else:
                latitude, longitude = coordinates
                bars[index] = replace(
                    bar,
                    latitude=latitude,
                    longitude=longitude,
                    geohash=encode(latitude, longitude),
                    geocoding_status="found",
                )

            if attempted % GEOCODING_CHECKPOINT_INTERVAL == 0:
                save_bars(bars, processed_path)
            if progress_callback is not None:
                progress_callback(completed_before + attempted, total_bars)

    if changed:
        save_bars(bars, processed_path)

    return bars
