"""Ponto de entrada do fluxo inicial do DeliveryDispatch."""

import argparse
import logging
import sys
import unicodedata
from collections.abc import Sequence
from io import TextIOBase
from pathlib import Path

from delivery_dispatch.algorithms.compact_trie import CompactTrie
from delivery_dispatch.data.bar_loader import load_bars, prepare_bars_csv
from delivery_dispatch.models.bar import Bar
from delivery_dispatch.models.courier import Courier
from delivery_dispatch.services.courier_generation import generate_couriers
from delivery_dispatch.services.geocoding import GeocodingError, NominatimGeocoder
from delivery_dispatch.services.road_network import OSMnxRoadProjector, RoadNetworkError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "bares.csv"
DEFAULT_PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "bares_geocodificados.csv"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "bar_geocoding.json"
DEFAULT_ROAD_GRAPH_PATH = PROJECT_ROOT / "data" / "cache" / "belo_horizonte_drive.graphml"
DEFAULT_USER_AGENT = "DeliveryDispatch/0.1 (projeto acadêmico)"
LOGGER = logging.getLogger(__name__)


def normalize_text(value: str) -> str:
    """Normaliza texto para indexação sem distinguir caixa, acentos ou espaços."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_accents.split())


class _CurrentStdout(TextIOBase):
    """Encaminha logs ao stdout atual, inclusive durante captura em testes."""

    def write(self, text: str) -> int:
        return sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()


def _configure_logging() -> None:
    if LOGGER.handlers:
        return
    handler = logging.StreamHandler(_CurrentStdout())
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def _non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("o número de entregadores não pode ser negativo")
    return number


class ProgressBar:
    """Renderiza uma barra em uma única linha do terminal."""

    def __init__(self, label: str, *, width: int = 30) -> None:
        self.label = label
        self.width = width
        self._active = False

    def update(self, processed: int, total: int) -> None:
        percentage = processed / total * 100 if total else 100
        filled = round(self.width * processed / total) if total else self.width
        bar = "#" * filled + "-" * (self.width - filled)
        complete = processed >= total
        line_end = "\n" if complete else ""
        sys.stdout.write(
            f"\r{self.label} [{bar}] {percentage:5.1f}% ({processed}/{total}){line_end}"
        )
        sys.stdout.flush()
        self._active = not complete

    def finish(self) -> None:
        if self._active:
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._active = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "couriers",
        type=_non_negative_integer,
        help="quantidade de entregadores a simular",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="arquivo CSV original de bares",
    )
    parser.add_argument(
        "--processed-csv",
        type=Path,
        default=DEFAULT_PROCESSED_CSV_PATH,
        help="arquivo CSV enriquecido com coordenadas e estado da geocodificação",
    )
    parser.add_argument(
        "--rebuild-processed",
        action="store_true",
        help="recria o CSV processado a partir da base original",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    progress = ProgressBar("Carregando bares")

    try:
        LOGGER.info("Preparando os dados")
        if args.rebuild_processed or not args.processed_csv.exists():
            prepare_bars_csv(
                args.csv,
                args.processed_csv,
                force=args.rebuild_processed,
            )
            LOGGER.info("Arquivo processado criado: %s", args.processed_csv)

        bars = load_bars(args.processed_csv)
        has_pending_bars = any(bar.geocoding_status == "pending" for bar in bars)
        geocoding_performed = has_pending_bars
        pending_count = sum(bar.geocoding_status == "pending" for bar in bars)
        completed_count = len(bars) - pending_count
        if geocoding_performed:
            LOGGER.info("Processando %d endereços pendentes", pending_count)
        progress.update(completed_count, len(bars))

        if geocoding_performed:
            geocoder = NominatimGeocoder(
                user_agent=DEFAULT_USER_AGENT,
                cache_path=DEFAULT_CACHE_PATH,
            )
            prepare_bars_csv(
                args.csv,
                args.processed_csv,
                geocoder=geocoder,
                progress_callback=progress.update,
            )
            bars = load_bars(args.processed_csv)
            progress.finish()
            LOGGER.info("Processamento geográfico concluído")
        else:
            progress.finish()
            LOGGER.info("Nenhum endereço pendente")

        located_bars = [bar for bar in bars if bar.coordinates is not None]
        if args.couriers:
            LOGGER.info(
                "Posicionando %d entregadores na malha viária (%s)",
                args.couriers,
                ("usando mapa salvo" if DEFAULT_ROAD_GRAPH_PATH.exists() else "baixando mapa"),
            )
            road_projector = OSMnxRoadProjector(DEFAULT_ROAD_GRAPH_PATH)
            couriers = generate_couriers(args.couriers, located_bars, road_projector)
            courier_tree = CompactTrie[Courier]()
            for courier in couriers:
                if courier.geohash is None:
                    raise ValueError("entregador gerado sem Geohash")
                courier_tree.insert(courier.geohash, courier)

        bar_name_tree = CompactTrie[Bar]()
        restaurant_address_tree = CompactTrie[Bar]()
        for bar in bars:
            normalized_name = normalize_text(bar.name)
            normalized_address = normalize_text(bar.address)
            if normalized_name:
                bar_name_tree.insert(normalized_name, bar)
            if normalized_address:
                restaurant_address_tree.insert(normalized_address, bar)
    except (OSError, ValueError, GeocodingError, RoadNetworkError) as error:
        progress.finish()
        LOGGER.error("Execução interrompida: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
