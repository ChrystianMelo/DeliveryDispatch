"""Trie compacta (radix tree) para chaves de texto.

Cada aresta armazena de uma vez o maior trecho comum das chaves abaixo
dela. Assim, caminhos sem bifurcações são representados por um único nó.
"""

from dataclasses import dataclass, field

# Define a API pública do módulo; importações com ``*`` exportam apenas esta classe.
__all__ = ["CompactTrie", "Node"]

# Deve ser um símbolo que não pertença ao alfabeto das chaves armazenadas.
_END = "$"


@dataclass(slots=True)
class Node[T]:
    # Trecho da chave armazenado na aresta que liga o nó pai a este nó.
    # Na raiz, o prefixo é uma string vazia.
    prefix: str

    # Associa o primeiro caractere de cada aresta ao respectivo nó filho.
    children: dict[str, "Node[T]"] = field(default_factory=dict)

    # Apenas a folha ligada pelo marcador ``_END`` armazena o valor da chave.
    value: T | None = None


class CompactTrie[T]:
    """Mapeamento de chaves de texto para valores implementado como trie compacta.

    ``insert``, ``remove`` e ``search_prefix`` explicitam as operações principais
    da estrutura. Chaves vazias são aceitas.
    Toda chave armazenada termina em uma folha especial ``_END``, que contém seu valor.
    """

    def __init__(self) -> None:
        self._root = Node[T]("")

    def insert(self, key: str, value: T) -> None:
        """Insere ``key`` associada a ``value``; não altera chaves existentes.

        Complexidade de tempo: O(m), em que m é o tamanho de ``key``,
        considerando acesso médio O(1) ao dicionário de filhos.
        """
        self._validate_key(key)
        self._insert_suffix(self._root, key, value)

    def _insert_suffix(self, node: Node[T], remaining: str, value: T) -> None:
        """Insere recursivamente a parte restante da chave a partir de ``node``."""
        if remaining == "":
            if _END in node.children:
                return
            node.children[_END] = Node("", value=value)
            return

        edge = remaining[0]
        child = node.children.get(edge)
        if child is None:
            node.children[edge] = self._terminal_node(remaining, value)
            return

        common_length = self._common_prefix_length(remaining, child.prefix)
        if common_length == len(child.prefix):
            suffix = remaining[common_length:]
            self._insert_suffix(child, suffix, value)
            return

        common_prefix = remaining[:common_length]
        old_suffix = child.prefix[common_length:]
        child.prefix = old_suffix

        branch = Node[T](common_prefix)
        branch.children[old_suffix[0]] = child
        node.children[edge] = branch

        new_suffix = remaining[common_length:]
        if new_suffix != "":
            branch.children[new_suffix[0]] = self._terminal_node(new_suffix, value)
        else:
            branch.children[_END] = Node("", value=value)

    def remove(self, key: str) -> None:
        """Remove ``key`` e compacta os caminhos unitários resultantes.

        Levanta ``KeyError`` se a chave não estiver armazenada.
        Complexidade de tempo: O(m), em que m é o tamanho de ``key``.
        """
        self._validate_key(key)
        try:
            self._remove_suffix(self._root, key)
        except KeyError:
            raise KeyError(key) from None

    def _remove_suffix(self, node: Node[T], remaining: str) -> None:
        """Remove a parte restante da chave a partir de ``node``."""
        if remaining == "":
            if _END not in node.children:
                raise KeyError(remaining)
            del node.children[_END]
            return

        edge = remaining[0]
        child = node.children.get(edge)
        if child is None or not remaining.startswith(child.prefix):
            raise KeyError(remaining)

        suffix = remaining[len(child.prefix) :]
        self._remove_suffix(child, suffix)

        if not child.children:
            del node.children[edge]
            return

        if len(child.children) == 1 and _END not in child.children:
            only_child = next(iter(child.children.values()))
            child.prefix += only_child.prefix
            child.children = only_child.children

    def search_prefix(self, prefix: str) -> list[Node[T]]:
        """Retorna as folhas e seus valores para chaves iniciadas por ``prefix``.

        Complexidade de tempo: O(m + k), em que m é o tamanho de ``prefix``
        e k é o número de nós percorridos na subárvore encontrada.
        """
        self._validate_key(prefix)
        if prefix == "":
            raise ValueError("prefix não pode ser vazio")

        node = self._root
        remaining = prefix

        while remaining != "":
            child = node.children.get(remaining[0])
            if child is None:
                return []

            common_length = self._common_prefix_length(remaining, child.prefix)
            if common_length == len(remaining):
                nodes: list[Node[T]] = []
                self._collect_terminal_nodes(child, nodes)
                return nodes
            elif common_length != len(child.prefix):
                return []

            remaining = remaining[common_length:]
            node = child

    def _collect_terminal_nodes(self, node: Node[T], nodes: list[Node[T]]) -> None:
        """Adiciona a ``nodes`` todas as folhas terminais abaixo de ``node``."""
        terminal = node.children.get(_END)
        if terminal is not None:
            nodes.append(terminal)

        for edge, child in node.children.items():
            if edge != _END:
                self._collect_terminal_nodes(child, nodes)

    @staticmethod
    def _terminal_node(prefix: str, value: T) -> Node[T]:
        return Node(prefix, {_END: Node("", value=value)})

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key deve ser uma string")
        if _END in key:
            raise ValueError(
                f"key não pode conter {_END!r}: esse símbolo é reservado como marcador de fim"
            )

    @staticmethod
    def _common_prefix_length(first: str, second: str) -> int:
        length = 0
        for first_character, second_character in zip(first, second, strict=False):
            if first_character != second_character:
                break
            length += 1
        return length
