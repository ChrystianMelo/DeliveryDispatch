"""Prepara os dados e inicia a interface web do DeliveryDispatch."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from io import TextIOBase
from pathlib import Path

from delivery_dispatch import dashboard
from delivery_dispatch.data.bar_loader import load_bars, prepare_bars_csv
from delivery_dispatch.services.geocoding import GeocodingError, NominatimGeocoder
from delivery_dispatch.services.road_network import OSMnxRoadProjector

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "bares.csv"
DEFAULT_PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "bares_geocodificados.csv"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "bar_geocoding.json"
DEFAULT_ROAD_GRAPH_PATH = PROJECT_ROOT / "data" / "cache" / "belo_horizonte_drive.graphml"
DEFAULT_USER_AGENT = "DeliveryDispatch/0.1 (projeto acadêmico)"
LOGGER = logging.getLogger(__name__)


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


def _port_number(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("a porta deve estar entre 1 e 65535")
    return port


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
    parser.add_argument(
        "--host",
        default=os.environ.get("DELIVERY_DISPATCH_HOST", "127.0.0.1"),
        help="endereço da interface web (padrão: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=_port_number,
        default=os.environ.get("DELIVERY_DISPATCH_PORT", "8050"),
        help="porta da interface web (padrão: 8050)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="ativa o modo de desenvolvimento do Dash",
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

        LOGGER.info("Abrindo a interface em http://%s:%d", args.host, args.port)
        road_projector = OSMnxRoadProjector(DEFAULT_ROAD_GRAPH_PATH)
        app = dashboard.create_app(bars, road_projector)
        app.run(host=args.host, port=args.port, debug=args.debug)
    except (OSError, ValueError, GeocodingError) as error:
        progress.finish()
        LOGGER.error("Execução interrompida: %s", error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
