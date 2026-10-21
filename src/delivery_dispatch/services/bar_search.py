"""Índice de busca por nome e endereço de bares e restaurantes."""

import unicodedata
from collections.abc import Callable, Iterable

from delivery_dispatch.algorithms.compact_trie import CompactTrie
from delivery_dispatch.models.bar import Bar

__all__ = ["BarSearchIndex", "normalize_text"]

DEFAULT_RESULT_LIMIT = 20
_END_MARKER = "$"
_ESCAPE = "\0"
_ESCAPED_END_MARKER = f"{_ESCAPE}e"
_UNIQUE_SEPARATOR = "\x01"


def normalize_text(value: str) -> str:
    """Normaliza caixa, acentos e espaços para buscas textuais."""
    if not isinstance(value, str):
        raise TypeError("value deve ser uma string")

    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_accents.split())


class BarSearchIndex:
    """Busca bares por nome ou por qualquer trecho do endereço normalizado.

    Cada texto recebe um sufixo interno único antes de ser inserido na Trie.
    Assim, estabelecimentos com o mesmo nome ou endereço não sobrescrevem uns
    aos outros. A busca remove a duplicação causada por um mesmo bar poder
    corresponder simultaneamente nos dois índices.
    """

    def __init__(
        self,
        bars: Iterable[Bar],
        *,
        normalizer: Callable[[str], str] = normalize_text,
    ) -> None:
        if not callable(normalizer):
            raise TypeError("normalizer deve ser chamável")

        self._normalizer = normalizer
        self._name_index = CompactTrie[Bar]()
        self._address_index = CompactTrie[Bar]()
        self._searchable_bars: list[tuple[Bar, tuple[str, ...]]] = []

        for position, bar in enumerate(bars):
            self._insert(self._name_index, bar.name, bar, position)
            if bar.legal_name != bar.name:
                self._insert(self._name_index, bar.legal_name, bar, position)
            self._insert(self._address_index, bar.address, bar, position)
            self._searchable_bars.append(
                (
                    bar,
                    (
                        self._normalize(bar.name),
                        self._normalize(bar.legal_name),
                        self._normalize(bar.address),
                    ),
                )
            )

    def search(self, query: str, *, limit: int = DEFAULT_RESULT_LIMIT) -> list[Bar]:
        """Retorna até ``limit`` bares compatíveis com nome ou endereço."""
        if not isinstance(query, str):
            raise TypeError("query deve ser uma string")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit deve ser um inteiro")
        if limit < 0:
            raise ValueError("limit não pode ser negativo")
        if limit == 0:
            return []

        normalized_query = self._normalize(query)
        if not normalized_query:
            return []

        prefix = self._escape_trie_text(normalized_query)
        results: list[Bar] = []
        seen_ids: set[int] = set()

        for index in (self._name_index, self._address_index):
            for node in index.search_prefix(prefix):
                bar = node.value
                if bar is None or bar.id in seen_ids:
                    continue
                results.append(bar)
                seen_ids.add(bar.id)
                if len(results) == limit:
                    return results

        # Endereços costumam ser procurados sem o tipo do logradouro (por
        # exemplo, "Portugal" em vez de "Avenida Portugal") ou pelo bairro.
        # O fallback mantém esses casos intuitivos sem multiplicar as chaves da
        # Trie por cada palavra da base.
        for bar, searchable_texts in self._searchable_bars:
            if bar.id in seen_ids or not any(normalized_query in text for text in searchable_texts):
                continue
            results.append(bar)
            seen_ids.add(bar.id)
            if len(results) == limit:
                break

        return results

    def _insert(
        self,
        index: CompactTrie[Bar],
        text: str,
        bar: Bar,
        position: int,
    ) -> None:
        normalized_text = self._normalize(text)
        if not normalized_text:
            return

        key = f"{self._escape_trie_text(normalized_text)}{_UNIQUE_SEPARATOR}{position}"
        index.insert(key, bar)

    def _normalize(self, value: str) -> str:
        normalized = self._normalizer(value)
        if not isinstance(normalized, str):
            raise TypeError("normalizer deve retornar uma string")
        return normalized

    @staticmethod
    def _escape_trie_text(value: str) -> str:
        """Escapa o marcador terminal reservado pela implementação da Trie."""
        return value.replace(_ESCAPE, _ESCAPE * 2).replace(
            _END_MARKER,
            _ESCAPED_END_MARKER,
        )
