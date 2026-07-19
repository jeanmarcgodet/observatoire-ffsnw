"""Modèle métier représentant un score de slalom."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlalomScore:
    """
    Score de slalom exprimé sous la forme :

        bouées / vitesse / longueur de corde

    Exemple :

        2,00/55/11.25
    """

    buoys: float
    speed: float
    rope_length: float
    raw_value: str

    SCORE_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<buoys>\d+(?:[.,]\d+)?)
        \s*/\s*
        (?P<speed>\d+(?:[.,]\d+)?)
        \s*/\s*
        (?P<rope_length>\d+(?:[.,]\d+)?)
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(cls, value: str) -> SlalomScore | None:
        """
        Analyse la première performance présente dans une chaîne.

        Une éventuelle mention de tie-break entre parenthèses est ignorée
        pour la comparaison de la performance principale.
        """
        if not value:
            return None

        match = cls.SCORE_PATTERN.match(value)

        if match is None:
            return None

        try:
            buoys = float(
                match.group("buoys").replace(",", ".")
            )
            speed = float(
                match.group("speed").replace(",", ".")
            )
            rope_length = float(
                match.group("rope_length").replace(",", ".")
            )
        except ValueError:
            return None

        return cls(
            buoys=buoys,
            speed=speed,
            rope_length=rope_length,
            raw_value=value,
        )

    @property
    def comparison_key(self) -> tuple[float, float, float]:
        """
        Retourne la clé de comparaison sportive.

        Priorités :

        1. corde la plus courte ;
        2. nombre de bouées le plus élevé ;
        3. vitesse la plus élevée.

        La longueur de corde est inversée car une valeur plus faible
        correspond à une difficulté supérieure.
        """
        return (
            -self.rope_length,
            self.buoys,
            self.speed,
        )

    def is_better_than(self, other: SlalomScore) -> bool:
        """Indique si le score est supérieur à un autre score."""
        return self.comparison_key > other.comparison_key

    def __str__(self) -> str:
        return self.raw_value
