"""Repositories d'accès aux données de l'Observatoire FFSNW."""

from observatoire.repositories.base import BaseRepository
from observatoire.repositories.rider_repository import RiderRepository

__all__ = [
    "BaseRepository",
    "RiderRepository",
]