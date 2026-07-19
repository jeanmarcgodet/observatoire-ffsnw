from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from observatoire.config import DATABASE_FILE


@dataclass(slots=True)
class Classification:
    classement: str
    categorie: str | None
    sexe: str | None
    rang: int | None
    ligue: str | None
    fichier_source: str


@dataclass(slots=True)
class Performance:
    result_id: int
    competition_code: str
    competition_nom: str
    date_debut: str | None
    date_fin: str | None
    ville: str | None
    pays: str | None
    discipline: str
    tour: str
    score: str
    document_url: str | None
    classifications: list[Classification] = field(default_factory=list)


@dataclass(slots=True)
class RiderHistory:
    rider_id: int
    iwwf_id: str
    nom: str
    prenom: str | None
    sexe: str | None
    nation: str | None
    annee_naissance: int | None
    performances: list[Performance] = field(default_factory=list)


def search_riders(
    search_term: str,
    DATABASE_FILE: Path = DATABASE_FILE,
) -> list[sqlite3.Row]:
    term = search_term.strip()

    if not term:
        return []

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        return connection.execute(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                prenom,
                sexe,
                nation,
                annee_naissance
            FROM riders
            WHERE
                nom LIKE ?
                OR prenom LIKE ?
                OR (COALESCE(prenom, '') || ' ' || nom) LIKE ?
                OR (nom || ' ' || COALESCE(prenom, '')) LIKE ?
                OR iwwf_id = ?
            ORDER BY nom, prenom
            """,
            (
                f"%{term}%",
                f"%{term}%",
                f"%{term}%",
                f"%{term}%",
                term,
            ),
        ).fetchall()
    finally:
        connection.close()


def get_rider_history(
    rider_id: int,
    DATABASE_FILE: Path = DATABASE_FILE,
) -> RiderHistory | None:
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        rider = connection.execute(
            """
            SELECT
                id,
                iwwf_id,
                nom,
                prenom,
                sexe,
                nation,
                annee_naissance
            FROM riders
            WHERE id = ?
            """,
            (rider_id,),
        ).fetchone()

        if rider is None:
            return None

        rows = connection.execute(
            """
            SELECT
                res.id AS result_id,
                c.iwwf_id AS competition_code,
                c.nom AS competition_nom,
                c.date_debut,
                c.date_fin,
                c.ville,
                c.pays,
                res.discipline,
                res.tour,
                res.score,
                res.document_url,
                rc.classement,
                rc.categorie,
                rc.sexe AS classement_sexe,
                rc.rang,
                rc.ligue,
                rc.fichier_source
            FROM results AS res
            INNER JOIN competitions AS c
                ON c.id = res.competition_id
            LEFT JOIN result_classifications AS rc
                ON rc.result_id = res.id
            WHERE res.rider_id = ?
            ORDER BY
                COALESCE(c.date_debut, '') DESC,
                c.iwwf_id DESC,
                res.discipline,
                res.tour,
                rc.rang
            """,
            (rider_id,),
        ).fetchall()

        performances_by_id: dict[int, Performance] = {}

        for row in rows:
            result_id = row["result_id"]

            performance = performances_by_id.get(result_id)

            if performance is None:
                performance = Performance(
                    result_id=result_id,
                    competition_code=row["competition_code"],
                    competition_nom=row["competition_nom"],
                    date_debut=row["date_debut"],
                    date_fin=row["date_fin"],
                    ville=row["ville"],
                    pays=row["pays"],
                    discipline=row["discipline"],
                    tour=row["tour"],
                    score=row["score"],
                    document_url=row["document_url"],
                )
                performances_by_id[result_id] = performance

            if row["classement"] is not None:
                performance.classifications.append(
                    Classification(
                        classement=row["classement"],
                        categorie=row["categorie"],
                        sexe=row["classement_sexe"],
                        rang=row["rang"],
                        ligue=row["ligue"],
                        fichier_source=row["fichier_source"],
                    )
                )

        return RiderHistory(
            rider_id=rider["id"],
            iwwf_id=rider["iwwf_id"],
            nom=rider["nom"],
            prenom=rider["prenom"],
            sexe=rider["sexe"],
            nation=rider["nation"],
            annee_naissance=rider["annee_naissance"],
            performances=list(performances_by_id.values()),
        )
    finally:
        connection.close()
