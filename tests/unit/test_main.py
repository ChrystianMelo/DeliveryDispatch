from delivery_dispatch.data.bar_loader import load_bars
from delivery_dispatch.main import main
from delivery_dispatch.models.bar import Bar
from delivery_dispatch.models.courier import Courier


def test_main_builds_typed_indexes_from_processed_bars(tmp_path, monkeypatch):
    processed_path = tmp_path / "bares_geocodificados.csv"
    processed_path.write_text(
        "_id,CNAE_PRINCIPAL,DESCRICAO_CNAE_PRINCIPAL,DESC_LOGRADOURO,"
        "NOME_LOGRADOURO,NUMERO_IMOVEL,COMPLEMENTO,NOME_BAIRRO,NOME,NOME_FANTASIA,"
        "LATITUDE,LONGITUDE,GEOCODING_STATUS\n"
        "1,5611201,RESTAURANTE,RUA,SÃO JOÃO,10,,CENTRO,BAR AÇÃO LTDA,,"
        "-19.9,-43.9,found\n",
        encoding="utf-8",
    )

    class IdentityRoadProjector:
        def __init__(self, cache_path):
            self.cache_path = cache_path

        def project(self, coordinates):
            return list(coordinates)

    trie_contents = []

    class RecordingTrie:
        @classmethod
        def __class_getitem__(cls, item):
            return cls

        def __init__(self):
            self.entries = []
            trie_contents.append(self.entries)

        def insert(self, key, value):
            self.entries.append((key, value))

    monkeypatch.setattr("delivery_dispatch.main.OSMnxRoadProjector", IdentityRoadProjector)
    monkeypatch.setattr("delivery_dispatch.main.CompactTrie", RecordingTrie)

    assert main(["3", "--processed-csv", str(processed_path)]) == 0

    entries = [entry for trie in trie_contents for entry in trie]
    courier_entries = [(key, value) for key, value in entries if isinstance(value, Courier)]
    bar_entries = [(key, value) for key, value in entries if isinstance(value, Bar)]

    assert len(courier_entries) == 3
    assert all(key == courier.geohash for key, courier in courier_entries)
    assert {key for key, _ in bar_entries} == {
        "bar acao ltda",
        "rua sao joao, 10, centro, belo horizonte - mg, brasil",
    }
    assert len({id(bar) for _, bar in bar_entries}) == 1


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

    assert main(["0", "--csv", str(csv_path), "--processed-csv", str(processed_path)]) == 0

    bars = load_bars(processed_path)
    assert len(queries) == 2
    assert all(bar.geocoding_status == "found" for bar in bars)
    assert all(bar.coordinates == (-19.9, -43.9) for bar in bars)
    assert all(bar.geohash is not None for bar in bars)
