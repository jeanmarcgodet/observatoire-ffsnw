"""Repositories d'accès aux données de l'Observatoire FFSNW."""

from observatoire.repositories.base import BaseRepository
from observatoire.repositories.competition_repository import CompetitionRepository
from observatoire.repositories.result_repository import ResultRepository
from observatoire.repositories.rider_repository import RiderRepository

__all__ = [
    "BaseRepository",
    "CompetitionRepository",
    "ResultRepository",
    "RiderRepository",
]
