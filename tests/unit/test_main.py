import pytest

from delivery_dispatch.data.bar_loader import load_bars
from delivery_dispatch.main import main


def test_main_rejects_the_removed_terminal_courier_argument():
    with pytest.raises(SystemExit):
        main(["3"])


def test_main_geocodes_and_persists_all_pending_bars(tmp_path, monkeypatch):
    csv_path = tmp_path / "bares.csv"
    processed_path = tmp_path / "bares_geocodificados.csv"
    csv_path.write_text(
        "_id,CNAE_PRINCIPAL,DESCRICAO_CNAE_PRINCIPAL,DESC_LOGRADOURO,"
        "NOME_LOGRADOURO,NUMERO_IMOVEL,COMPLEMENTO,NOME_BAIRRO,NOME,NOME_FANTASIA\n"
        "1,5611201,RESTAURANTE,RUA,UM,10,,CENTRO,BAR UM,\n"
        "2,5611201,RESTAURANTE,RUA,DOIS,20,,CENTRO,BAR DOIS,\n",
        encoding="utf-8",
    )

    queries = []

    class FakeGeocoder:
        def __init__(self, **kwargs):
            pass

        def geocode(self, query):
            queries.append(query)
            return -19.9, -43.9

    monkeypatch.setattr("delivery_dispatch.main.NominatimGeocoder", FakeGeocoder)

    class FakeApp:
        def run(self, **kwargs):
            pass

    monkeypatch.setattr(
        "delivery_dispatch.dashboard.create_app",
        lambda bars, projector: FakeApp(),
    )

    assert main(["--csv", str(csv_path), "--processed-csv", str(processed_path)]) == 0

    bars = load_bars(processed_path)
    assert len(queries) == 2
    assert all(bar.geocoding_status == "found" for bar in bars)
    assert all(bar.coordinates == (-19.9, -43.9) for bar in bars)
    assert all(bar.geohash is not None for bar in bars)


def test_main_always_opens_dashboard(tmp_path, monkeypatch):
    processed_path = tmp_path / "bares_geocodificados.csv"
    processed_path.write_text(
        "_id,CNAE_PRINCIPAL,DESCRICAO_CNAE_PRINCIPAL,DESC_LOGRADOURO,"
        "NOME_LOGRADOURO,NUMERO_IMOVEL,COMPLEMENTO,NOME_BAIRRO,NOME,NOME_FANTASIA,"
        "LATITUDE,LONGITUDE,GEOCODING_STATUS\n"
        "1,5611201,RESTAURANTE,RUA,UM,10,,CENTRO,BAR UM,,"
        "-19.9,-43.9,found\n",
        encoding="utf-8",
    )
    calls = {}

    class FakeApp:
        def run(self, **kwargs):
            calls["run"] = kwargs

    def fake_create_app(bars, projector):
        calls["bars"] = bars
        calls["projector"] = projector
        return FakeApp()

    monkeypatch.setattr("delivery_dispatch.dashboard.create_app", fake_create_app)
    monkeypatch.setattr(
        "delivery_dispatch.main.webbrowser.open_new_tab",
        lambda url: calls.setdefault("browser_url", url),
    )

    assert (
        main(
            [
                "--processed-csv",
                str(processed_path),
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
            ]
        )
        == 0
    )
    assert len(calls["bars"]) == 1
    assert calls["browser_url"] == "http://127.0.0.1:9000"
    assert calls["run"] == {"host": "0.0.0.0", "port": 9000, "debug": False}
