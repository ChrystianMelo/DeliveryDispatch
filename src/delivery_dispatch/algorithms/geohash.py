"""Conversão de coordenadas para Geohash por subdivisão binária de intervalos."""

from math import isfinite

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
MAX_LEVELS = 8


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
    if not -90 <= latitude <= 90 or not isfinite(latitude):
        raise ValueError("latitude deve ser finita e estar entre -90 e 90")

    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
        raise TypeError("longitude deve ser um número")
    if not -180 <= longitude <= 180 or not isfinite(longitude):
        raise ValueError("longitude deve ser finita e estar entre -180 e 180")

    longitude_min = -180.0
    longitude_max = 180.0
    latitude_min = -90.0
    latitude_max = 90.0
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

        # Acrescenta o bit ao valor binário que formará o próximo caractere.
        character_value = character_value * 2 + bit

        # Cada grupo de 5 bits corresponde a um caractere Base32.
        if bit_index % 5 == 4:
            result += BASE32[character_value]
            character_value = 0

    return result
