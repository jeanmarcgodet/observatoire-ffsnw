"""Modèles métier."""

from observatoire.models.competition import Competition
from observatoire.models.result import Result
from observatoire.models.rider import Rider
from observatoire.models.rider_career import RiderCareer
from observatoire.models.slalom_score import SlalomScore
from observatoire.models.competition_report import CompetitionReport

__all__ = [
    "Competition",
    "Result",
    "Rider",
    "RiderCareer",
    "SlalomScore",
    "CompetitionReport",
]
