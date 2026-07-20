from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests


EMS_PARTICIPATIONS_URL = (
    "https://ems.iwwf.sport/"
    "Competitions/GetCompetitionParticipations"
)


@dataclass(frozen=True)
class EmsDisciplineEntry:
    discipline: str
    detail: str | None = None


@dataclass(frozen=True)
class EmsParticipant:
    ems_athlete_id: str
    nom_complet: str
    nation: str
    federation: str
    categorie: str
    sexe: str | None
    age_affiche: int | None
    annee_naissance: int | None
    disciplines: tuple[EmsDisciplineEntry, ...]


CATEGORY_PATTERN = re.compile(
    r"^(?P<categorie>.+?)\s+"
    r"(?P<sexe>[MF])"
    r"(?:\s+\((?P<age>\d+)\))?\s*$"
)

EVENT_PATTERN = re.compile(
    r"^(?P<discipline>[A-Za-z]+)"
    r"(?:\s+\((?P<detail>[^)]+)\))?$"
)


def fetch_competition_participations(
    competition_id: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    response = requests.get(
        EMS_PARTICIPATIONS_URL,
        params={"competitionId": competition_id},
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "observatoire-ffsnw/1.0 "
                "(public IWWF EMS data collector)"
            ),
        },
        timeout=timeout,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("Réponse EMS inattendue : objet JSON attendu.")

    if not isinstance(payload.get("data"), list):
        raise ValueError("Réponse EMS inattendue : champ 'data' absent.")

    return payload


def parse_category(
    raw_category: str,
) -> tuple[str, str | None, int | None]:
    value = raw_category.strip()
    match = CATEGORY_PATTERN.match(value)

    if match is None:
        return value, None, None

    age_text = match.group("age")

    return (
        match.group("categorie").strip(),
        match.group("sexe"),
        int(age_text) if age_text else None,
    )


def normalize_discipline(
    raw_event: str | None,
) -> EmsDisciplineEntry | None:
    if raw_event is None:
        return None

    value = raw_event.strip()

    if not value or value == "-":
        return None

    match = EVENT_PATTERN.match(value)

    if match is None:
        return EmsDisciplineEntry(
            discipline=value.lower(),
            detail=None,
        )

    return EmsDisciplineEntry(
        discipline=match.group("discipline").lower(),
        detail=match.group("detail"),
    )


def parse_participant(raw: dict[str, Any]) -> EmsParticipant:
    category, sex, displayed_age = parse_category(
        str(raw.get("Category", ""))
    )

    birth_year: int | None

    try:
        birth_year = int(raw["YearOfBirthday"])
    except (KeyError, TypeError, ValueError):
        birth_year = None

    disciplines: list[EmsDisciplineEntry] = []

    for index in range(1, 6):
        discipline = normalize_discipline(
            raw.get(f"Event_{index}")
        )

        if discipline is not None:
            disciplines.append(discipline)

    athlete_id = str(raw.get("AthleteId", "")).strip()

    if not athlete_id:
        raise ValueError("Participant EMS sans AthleteId.")

    return EmsParticipant(
        ems_athlete_id=athlete_id,
        nom_complet=str(raw.get("Name", "")).strip(),
        nation=str(raw.get("Country", "")).strip(),
        federation=str(
            raw.get("AthleteFedarationAbbr", "")
        ).strip(),
        categorie=category,
        sexe=sex,
        age_affiche=displayed_age,
        annee_naissance=birth_year,
        disciplines=tuple(disciplines),
    )


def load_competition_participations(
    competition_id: str,
) -> list[EmsParticipant]:
    payload = fetch_competition_participations(
        competition_id
    )

    return [
        parse_participant(raw_participant)
        for raw_participant in payload["data"]
    ]