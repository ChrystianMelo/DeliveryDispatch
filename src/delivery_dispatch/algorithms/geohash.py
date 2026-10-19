"""Conversão de coordenadas para Geohash por subdivisão binária de intervalos."""

from math import isfinite

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
MAX_LEVELS = 8
LATITUDE_BOUNDS = (-90.0, 90.0)
LONGITUDE_BOUNDS = (-180.0, 180.0)


def encode(latitude: float, longitude: float, levels: int = MAX_LEVELS) -> str:
    """Retorna um Geohash com 1 a 8 níveis (caracteres Base32).

    Intercala bits de longitude e latitude, começando pela longitude.
    Cada bit divide o intervalo ao meio: 0 seleciona a metade inferior,
    e 1 a superior, incluindo o ponto médio. Cada grupo de 5 bits gera
    um caractere do alfabeto Base32 do Geohash.

    Latitude deve estar em [-90, 90] e longitude em [-180, 180], em graus.
    Entradas não numéricas causam TypeError; valores fora dos intervalos,
    não finitos ou níveis fora de [1, 8] causam ValueError.
    """
    if isinstance(levels, bool) or not isinstance(levels, int):
        raise TypeError("levels deve ser um inteiro")
    if not 1 <= levels <= MAX_LEVELS:
        raise ValueError("levels deve estar entre 1 e 8")

    if isinstance(latitude, bool) or not isinstance(latitude, (int, float)):
        raise TypeError("latitude deve ser um número")
    if not LATITUDE_BOUNDS[0] <= latitude <= LATITUDE_BOUNDS[1] or not isfinite(latitude):
        raise ValueError("latitude deve ser finita e estar entre -90 e 90")

    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
        raise TypeError("longitude deve ser um número")
    if not LONGITUDE_BOUNDS[0] <= longitude <= LONGITUDE_BOUNDS[1] or not isfinite(longitude):
        raise ValueError("longitude deve ser finita e estar entre -180 e 180")

    longitude_min, longitude_max = LONGITUDE_BOUNDS
    latitude_min, latitude_max = LATITUDE_BOUNDS
    result = ""
    character_value = 0

    for bit_index in range(levels * 5):
        # Bits de índice par representam longitude; os de índice ímpar, latitude.
        if bit_index % 2 == 0:
            longitude_midpoint = (longitude_min + longitude_max) / 2

            if longitude >= longitude_midpoint:
                bit = 1
                longitude_min = longitude_midpoint
            else:
                bit = 0
                longitude_max = longitude_midpoint
        else:
            latitude_midpoint = (latitude_min + latitude_max) / 2

            if latitude >= latitude_midpoint:
                bit = 1
                latitude_min = latitude_midpoint
            else:
                bit = 0
                latitude_max = latitude_midpoint

        # Atualiza o valor do caractere com o próximo bit: x = (x << 1) | bit.
        character_value = (character_value << 1) | bit

        # Cada grupo de 5 bits corresponde a um caractere Base32.
        if bit_index % 5 == 4:
            result += BASE32[character_value]
            character_value = 0

    return result


def decode(geohash: str) -> tuple[float, float]:
    """Retorna o centro da célula de um Geohash como ``(latitude, longitude)``.

    Cada caractere é convertido em cinco bits, que refinam alternadamente os
    intervalos de longitude e latitude. O resultado é o ponto médio dos
    intervalos finais.

    O Geohash deve ser uma string de 1 a 8 caracteres do alfabeto Base32.
    Valores de outro tipo causam TypeError; tamanho ou caracteres inválidos
    causam ValueError.
    """
    if not isinstance(geohash, str):
        raise TypeError("geohash deve ser uma string")
    if not 1 <= len(geohash) <= MAX_LEVELS:
        raise ValueError("geohash deve ter entre 1 e 8 caracteres")

    longitude_min, longitude_max = LONGITUDE_BOUNDS
    latitude_min, latitude_max = LATITUDE_BOUNDS
    bit_index = 0

    for character in geohash:
        try:
            character_value = BASE32.index(character)
        except ValueError:
            raise ValueError(f"caractere inválido no geohash: {character!r}") from None

        for shift in range(4, -1, -1):
            bit = (character_value >> shift) & 1

            if bit_index % 2 == 0:
                longitude_midpoint = (longitude_min + longitude_max) / 2
                if bit:
                    longitude_min = longitude_midpoint
                else:
                    longitude_max = longitude_midpoint
            else:
                latitude_midpoint = (latitude_min + latitude_max) / 2
                if bit:
                    latitude_min = latitude_midpoint
                else:
                    latitude_max = latitude_midpoint

            bit_index += 1

    latitude = (latitude_min + latitude_max) / 2
    longitude = (longitude_min + longitude_max) / 2
    return latitude, longitude
