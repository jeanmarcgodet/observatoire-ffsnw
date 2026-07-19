import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.importers.iwwf_participants import (
    parse_competition_metadata,
    parse_participants,
)


def import_participants(
    competition_code: str,
    html_file: Path,
) -> tuple[int, int]:
    participants = parse_participants(html_file)
    metadata = parse_competition_metadata(
        html_file.parent / "index.html"
    )
    riders_imported = 0
    entries_imported = 0

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute(
            """
            INSERT INTO competitions (
                iwwf_id,
                nom,
                date_debut,
                date_fin,
                ville,
                discipline
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(iwwf_id) DO UPDATE SET
                nom = excluded.nom,
                date_debut = excluded.date_debut,
                date_fin = excluded.date_fin,
                ville = excluded.ville,
                discipline = excluded.discipline
        """,
        (
            competition_code,
            metadata.nom,
            metadata.date_debut,
            metadata.date_fin,
            metadata.lieu,
            "classic",
        ),
    )

        competition_row = connection.execute(
            """
            SELECT id
            FROM competitions
            WHERE iwwf_id = ?
            """,
            (competition_code,),
        ).fetchone()

        if competition_row is None:
            raise RuntimeError(
                f"Compétition introuvable : {competition_code}"
            )

        competition_id = competition_row[0]

        for participant in participants:
            # La page ne distingue pas sans ambiguïté nom et prénom.
            # On conserve donc provisoirement le nom complet dans `nom`.
            connection.execute(
                """
                INSERT INTO riders (
                    iwwf_id,
                    nom,
                    prenom,
                    sexe,
                    nation,
                    annee_naissance
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(iwwf_id) DO UPDATE SET
                    nom = excluded.nom,
                    prenom = excluded.prenom,
                    sexe = excluded.sexe,
                    nation = excluded.nation,
                    annee_naissance = excluded.annee_naissance
                """,
                (
                    participant.iwwf_id,
                    participant.nom,
                    participant.prenom,
                    participant.sexe,
                    participant.nation,
                    participant.annee_naissance,
                ),
            )

            rider_row = connection.execute(
                """
                SELECT id
                FROM riders
                WHERE iwwf_id = ?
                """,
                (participant.iwwf_id,),
            ).fetchone()

            if rider_row is None:
                raise RuntimeError(
                    f"Rider introuvable : {participant.iwwf_id}"
                )

            rider_id = rider_row[0]

            rider_changes_before = connection.total_changes

            connection.execute(
                """
                INSERT INTO entries (
                    competition_id,
                    rider_id,
                    categorie
                )
                VALUES (?, ?, ?)
                ON CONFLICT(
                    competition_id,
                    rider_id,
                    categorie
                ) DO NOTHING
                """,
                (
                    competition_id,
                    rider_id,
                    participant.categorie,
                ),
            )

            if connection.total_changes > rider_changes_before:
                entries_imported += 1

        riders_imported = connection.execute(
            """
            SELECT COUNT(DISTINCT rider_id)
            FROM entries
            WHERE competition_id = ?
            """,
            (competition_id,),
        ).fetchone()[0]

    return riders_imported, entries_imported