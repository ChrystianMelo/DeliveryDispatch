"""Geocodificação de endereços usando uma instância do Nominatim."""

import json
import time
from math import isfinite
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PUBLIC_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class GeocodingError(RuntimeError):
    """Indica que uma consulta de geocodificação não pôde ser concluída."""


class NominatimGeocoder:
    """Cliente sequencial do Nominatim com intervalo mínimo e cache persistente."""

    def __init__(
        self,
        *,
        user_agent: str,
        cache_path: str | Path,
        endpoint: str = PUBLIC_NOMINATIM_URL,
        request_interval: float = 1.0,
        timeout: float = 15.0,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("user_agent não pode ser vazio")
        if request_interval < 0:
            raise ValueError("request_interval não pode ser negativo")
        if timeout <= 0:
            raise ValueError("timeout deve ser positivo")

        self.user_agent = user_agent
        self.cache_path = Path(cache_path)
        self.endpoint = endpoint
        self.request_interval = request_interval
        self.timeout = timeout
        self._last_request_at: float | None = None
        self._cache = self._load_cache()

    def _load_cache(self) -> dict[str, list[float] | None]:
        if not self.cache_path.exists():
            return {}
        try:
            content = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise GeocodingError(f"cache de geocodificação inválido: {self.cache_path}") from error
        if not isinstance(content, dict):
            raise GeocodingError(f"cache de geocodificação inválido: {self.cache_path}")
        return content

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(self.cache_path)

    def _respect_request_interval(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.request_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def geocode(self, query: str) -> tuple[float, float] | None:
        """Retorna ``(latitude, longitude)`` para um endereço ou ``None``."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query não pode ser vazia")

        if normalized_query in self._cache:
            cached = self._cache[normalized_query]
            return tuple(cached) if cached is not None else None

        parameters = urlencode(
            {
                "q": normalized_query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "br",
            }
        )
        request = Request(
            f"{self.endpoint}?{parameters}",
            headers={"Accept-Language": "pt-BR", "User-Agent": self.user_agent},
        )

        self._respect_request_interval()
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise GeocodingError(f"falha ao geocodificar {normalized_query!r}") from error
        finally:
            self._last_request_at = time.monotonic()

        coordinates: tuple[float, float] | None = None
        if isinstance(payload, list) and payload:
            try:
                latitude = float(payload[0]["lat"])
                longitude = float(payload[0]["lon"])
            except (KeyError, TypeError, ValueError) as error:
                raise GeocodingError("resposta inválida do Nominatim") from error
            if not isfinite(latitude) or not isfinite(longitude):
                raise GeocodingError("resposta inválida do Nominatim")
            coordinates = latitude, longitude

        self._cache[normalized_query] = list(coordinates) if coordinates is not None else None
        self._save_cache()
        return coordinates
