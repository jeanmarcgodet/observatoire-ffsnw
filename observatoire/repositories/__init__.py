"""Repositories d'accès aux données."""

from observatoire.repositories.competition_repository import (
    CompetitionRepository,
)
from observatoire.repositories.result_repository import (
    ResultRepository,
)
from observatoire.repositories.rider_repository import (
    RiderRepository,
)

__all__ = [
    "CompetitionRepository",
    "ResultRepository",
    "RiderRepository",
]