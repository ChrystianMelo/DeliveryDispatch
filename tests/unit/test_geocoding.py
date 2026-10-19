"""Testes do cliente Nominatim sem acesso à rede."""

import json
from pathlib import Path

from delivery_dispatch.services import geocoding
from delivery_dispatch.services.geocoding import NominatimGeocoder


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def test_geocode_queries_nominatim_and_saves_cache(tmp_path: Path, monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse([{"lat": "-19.9", "lon": "-43.9"}])

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    cache_path = tmp_path / "geocoding.json"
    client = NominatimGeocoder(
        user_agent="DeliveryDispatch/tests",
        cache_path=cache_path,
        request_interval=0,
    )

    assert client.geocode("Avenida Portugal, Belo Horizonte") == (-19.9, -43.9)
    assert len(requests) == 1
    assert requests[0][0].get_header("User-agent") == "DeliveryDispatch/tests"
    assert "countrycodes=br" in requests[0][0].full_url
    assert json.loads(cache_path.read_text(encoding="utf-8")) == {
        "Avenida Portugal, Belo Horizonte": [-19.9, -43.9]
    }


def test_geocode_reuses_cached_result_without_network(tmp_path: Path, monkeypatch):
    cache_path = tmp_path / "geocoding.json"
    cache_path.write_text('{"endereço": [-19.9, -43.9]}', encoding="utf-8")
    client = NominatimGeocoder(user_agent="DeliveryDispatch/tests", cache_path=cache_path)

    def unexpected_urlopen(*args, **kwargs):
        raise AssertionError("a rede não deveria ser consultada")

    monkeypatch.setattr(geocoding, "urlopen", unexpected_urlopen)

    assert client.geocode("endereço") == (-19.9, -43.9)
