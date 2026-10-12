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
class Node:
    # Trecho da chave armazenado na aresta que liga o nó pai a este nó.
    # Na raiz, o prefixo é uma string vazia.
    prefix: str

    # Associa o primeiro caractere de cada aresta ao respectivo nó filho.
    children: dict[str, "Node"] = field(default_factory=dict)


class CompactTrie:
    """Conjunto de strings implementado como uma trie compacta.

    ``insert`` e ``search_prefix`` explicitam as operações principais da estrutura.
    Chaves vazias são aceitas.
    Toda chave armazenada termina em um filho especial ``_END``.
    """

    def __init__(self) -> None:
        self._root = Node("")

    def insert(self, key: str) -> None:
        """Insere ``key``; não faz nada se ela já existir.

        Complexidade de tempo: O(m), em que m é o tamanho de ``key``,
        considerando acesso médio O(1) ao dicionário de filhos.
        """
        self._validate_key(key)
        self._insert_suffix(self._root, key)

    def _insert_suffix(self, node: Node, remaining: str) -> None:
        """Insere recursivamente a parte restante da chave a partir de ``node``."""
        if remaining == "":
            if _END in node.children:
                return
            node.children[_END] = Node("")
            return

        edge = remaining[0]
        child = node.children.get(edge)
        if child is None:
            node.children[edge] = self._terminal_node(remaining)
            return

        common_length = self._common_prefix_length(remaining, child.prefix)
        if common_length == len(child.prefix):
            suffix = remaining[common_length:]
            self._insert_suffix(child, suffix)
            return

        common_prefix = remaining[:common_length]
        old_suffix = child.prefix[common_length:]
        child.prefix = old_suffix

        branch = Node(common_prefix)
        branch.children[old_suffix[0]] = child
        node.children[edge] = branch

        new_suffix = remaining[common_length:]
        if new_suffix != "":
            branch.children[new_suffix[0]] = self._terminal_node(new_suffix)
        else:
            branch.children[_END] = Node("")

    def search_prefix(self, prefix: str) -> list[Node]:
        """Retorna os nós terminais das chaves que começam com ``prefix``.

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
                nodes: list[Node] = []
                self._collect_terminal_nodes(child, nodes)
                return nodes
            elif common_length != len(child.prefix):
                return []

            remaining = remaining[common_length:]
            node = child

    def _collect_terminal_nodes(self, node: Node, nodes: list[Node]) -> None:
        """Adiciona a ``nodes`` todos os nós terminais abaixo de ``node``."""
        if _END in node.children:
            nodes.append(node)

        for edge, child in node.children.items():
            if edge != _END:
                self._collect_terminal_nodes(child, nodes)

    @staticmethod
    def _terminal_node(prefix: str) -> Node:
        return Node(prefix, {_END: Node("")})

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
