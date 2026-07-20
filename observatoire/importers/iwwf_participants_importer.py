from __future__ import annotations

import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.importers.iwwf_participants import (
    Participant,
    parse_competition_metadata,
    parse_participants,
    parse_startlist_participants,
)


def find_participant_files(
    competition_directory: Path,
    main_html_file: Path,
) -> list[Path]:
    """
    Retourne toutes les sources permettant d'identifier les participants :

    - la liste générale des skieurs ;
    - les listes de départ.

    Certaines compétitions IWWF ont une liste générale incomplète.
    Les startlists permettent alors de récupérer les concurrents manquants.
    """
    files: list[Path] = []

    if main_html_file.exists():
        files.append(main_html_file)

    for path in sorted(competition_directory.glob("*_startlist.html")):
        if path not in files:
            files.append(path)

    return files


def merge_participants(
    participant_files: list[Path],
) -> list[Participant]:
    """
    Fusionne les participants provenant de plusieurs fichiers.

    Une participation est identifiée par :
        identifiant IWWF
        catégorie
        sexe
    """
    merged: dict[tuple[str, str, str], Participant] = {}

    for html_file in participant_files:
        if html_file.name.lower().endswith(
            "_startlist.html"
        ):
            parser = parse_startlist_participants
        else:
            parser = parse_participants

        for participant in parser(html_file):
            key = (
                participant.iwwf_id,
                participant.categorie,
                participant.sexe,
            )

            existing = merged.get(key)

            if existing is None:
                merged[key] = participant
                continue

            merged[key] = Participant(
                iwwf_id=participant.iwwf_id,
                nom=participant.nom or existing.nom,
                prenom=participant.prenom or existing.prenom,
                nation=participant.nation or existing.nation,
                categorie=(
                    participant.categorie
                    or existing.categorie
                ),
                sexe=participant.sexe or existing.sexe,
                annee_naissance=(
                    participant.annee_naissance
                    if participant.annee_naissance is not None
                    else existing.annee_naissance
                ),
            )

    return list(merged.values())


def import_participants(
    competition_code: str,
    html_file: Path,
) -> tuple[int, int]:
    competition_directory = html_file.parent

    participant_files = find_participant_files(
        competition_directory=competition_directory,
        main_html_file=html_file,
    )

    participants = merge_participants(participant_files)

    metadata = parse_competition_metadata(
        competition_directory / "index.html"
    )

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
            ON CONFLICT(iwwf_id) DO NOTHING
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

        competition_id = int(competition_row[0])

        for participant in participants:
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
                    nom = CASE
                        WHEN excluded.nom <> ''
                        THEN excluded.nom
                        ELSE riders.nom
                    END,
                    prenom = CASE
                        WHEN excluded.prenom <> ''
                        THEN excluded.prenom
                        ELSE riders.prenom
                    END,
                    sexe = CASE
                        WHEN excluded.sexe <> ''
                        THEN excluded.sexe
                        ELSE riders.sexe
                    END,
                    nation = CASE
                        WHEN excluded.nation <> ''
                        THEN excluded.nation
                        ELSE riders.nation
                    END,
                    annee_naissance = COALESCE(
                        excluded.annee_naissance,
                        riders.annee_naissance
                    )
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

            rider_id = int(rider_row[0])

            cursor = connection.execute(
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

            if cursor.rowcount == 1:
                entries_imported += 1

        riders_imported_row = connection.execute(
            """
            SELECT COUNT(DISTINCT rider_id)
            FROM entries
            WHERE competition_id = ?
            """,
            (competition_id,),
        ).fetchone()

        riders_imported = (
            int(riders_imported_row[0])
            if riders_imported_row is not None
            else 0
        )

    return riders_imported, entries_imported