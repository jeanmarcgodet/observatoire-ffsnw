"""Modèles métier."""

from observatoire.models.competition import Competition
from observatoire.models.result import Result
from observatoire.models.rider import Rider
from observatoire.models.rider_career import RiderCareer
from observatoire.models.slalom_score import SlalomScore

__all__ = [
    "Competition",
    "Result",
    "Rider",
    "RiderCareer",
    "SlalomScore",
]
