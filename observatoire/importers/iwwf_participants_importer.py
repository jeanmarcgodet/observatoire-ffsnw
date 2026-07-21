from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.importers.iwwf_results import parse_results_file
from observatoire.importers.iwwf_results_importer import find_result_files
from observatoire.importers.iwwf_participants import (
    Participant,
    normalize_category,
    parse_competition_metadata,
    parse_participants,
    parse_startlist_participants,
    split_participant_name,
)



def parse_identity_candidates_json(
    json_file: Path,
) -> list[Participant]:
    """
    Charge une liste d'identit?s IWWF r?solues depuis un JSON.

    Ce format est utilis? lorsque l'ancienne page de r?sultats
    ne contient pas de liens skier=... dans ses tableaux.
    """
    data = json.loads(
        json_file.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Format JSON invalide : {json_file}"
        )

    participants: list[Participant] = []

    for raw_name, identity in data.items():
        if not isinstance(identity, dict):
            raise RuntimeError(
                f"Identit? invalide pour {raw_name}"
            )

        iwwf_id = str(
            identity.get("ranking_id")
            or ""
        ).strip().upper()

        if not iwwf_id:
            raise RuntimeError(
                "Identifiant IWWF manquant pour "
                f"{raw_name}"
            )

        full_name = str(
            identity.get("source_name")
            or raw_name
        ).strip()

        # Privil?gie le nom fourni par la page officielle
        # de classement lorsqu'il correspond ? l'identifiant.
        candidates = identity.get("candidates")

        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue

                candidate_id = str(
                    candidate.get("ranking_id")
                    or ""
                ).strip().upper()

                candidate_name = str(
                    candidate.get("candidate_name")
                    or ""
                ).strip()

                if (
                    candidate_id == iwwf_id
                    and candidate_name
                ):
                    full_name = candidate_name
                    break

        categorie = normalize_category(
            str(
                identity.get("category")
                or ""
            ).strip()
        )

        sexe = str(
            identity.get("sex")
            or ""
        ).strip().upper()

        if not categorie:
            raise RuntimeError(
                f"Cat?gorie manquante pour {raw_name}"
            )

        if sexe not in {"M", "F"}:
            raise RuntimeError(
                f"Sexe invalide pour {raw_name}"
            )

        nom, prenom = split_participant_name(
            full_name
        )

        nation = (
            iwwf_id[:3]
            if (
                len(iwwf_id) >= 3
                and iwwf_id[:3].isalpha()
            )
            else ""
        )

        participants.append(
            Participant(
                iwwf_id=iwwf_id,
                nom=nom,
                prenom=prenom,
                nation=nation,
                categorie=categorie,
                sexe=sexe,
                annee_naissance=None,
            )
        )

    return participants


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



def find_hors_championnat_only_iwwf_ids(
    competition_directory: Path,
) -> set[str]:
    """
    Identifie les riders pr?sents uniquement dans une page
    de r?sultats ? hors Championnat de France ?.

    Un rider ?galement pr?sent dans un classement officiel
    reste conserv?.
    """
    import re

    from observatoire.importers.iwwf_results_importer import (
        find_result_files,
    )

    skier_pattern = re.compile(
        r"[?&]skier=([A-Z]{3}\d+)",
        re.IGNORECASE,
    )

    def extract_ids(html_file: Path) -> set[str]:
        html = html_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return {
            match.upper()
            for match in skier_pattern.findall(html)
        }

    hors_files = sorted(
        competition_directory.glob(
            "*_results_hf.html"
        )
    )

    if not hors_files:
        return set()

    hors_ids: set[str] = set()

    for html_file in hors_files:
        hors_ids.update(extract_ids(html_file))

    official_ids: set[str] = set()

    for html_file in find_result_files(
        competition_directory
    ):
        official_ids.update(extract_ids(html_file))

    return hors_ids - official_ids



def merge_result_participants(
    result_files: list[Path],
) -> list[Participant]:
    """
    Reconstruit les participants depuis les pages de r?sultats
    lorsque la liste g?n?rale IWWF ne contient pas de cat?gorie.
    """
    merged: dict[
        tuple[str, str, str],
        Participant,
    ] = {}

    category_prefixes = {
        "8": "U8",
        "10": "U10",
        "12": "U12",
        "14": "U14",
        "17": "U17",
        "18": "U18",
        "21": "U21",
        "35": "35+",
        "45": "45+",
        "55": "55+",
        "65": "65+",
        "70": "70+",
        "75": "75+",
        "80": "80+",
    }

    for html_file in result_files:
        filename_parts = (
            html_file.stem
            .lower()
            .split("_")
        )

        inferred_category = None
        inferred_sex = ""

        if filename_parts:
            first = filename_parts[0]
            second = (
                filename_parts[1]
                if len(filename_parts) > 1
                else ""
            )

            if first in category_prefixes:
                inferred_category = (
                    category_prefixes[first]
                )

                if second in {"m", "f"}:
                    inferred_sex = second.upper()

            elif first in {"allf", "women"}:
                inferred_sex = "F"

            elif first in {"allm", "men"}:
                inferred_sex = "M"

        for result in parse_results_file(html_file):
            categorie = normalize_category(
                result.categorie
                or inferred_category
                or ""
            )

            sexe = (
                result.sexe
                or inferred_sex
                or ""
            ).strip().upper()

            if not categorie:
                # Les pages f?minines group?es de 19FRA03
                # doivent ?tre rattach?es ? l'inscription
                # r?ellement port?e par la skieuse lorsqu'elle
                # existe d?j? dans la base.
                continue

            if sexe not in {"M", "F"}:
                continue

            nom, prenom = split_participant_name(
                result.nom_complet
            )

            nation = (
                result.iwwf_id[:3]
                if (
                    len(result.iwwf_id) >= 3
                    and result.iwwf_id[:3].isalpha()
                )
                else ""
            )

            key = (
                result.iwwf_id,
                categorie,
                sexe,
            )

            merged.setdefault(
                key,
                Participant(
                    iwwf_id=result.iwwf_id,
                    nom=nom,
                    prenom=prenom,
                    nation=nation,
                    categorie=categorie,
                    sexe=sexe,
                    annee_naissance=None,
                ),
            )

    return list(merged.values())


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
        if html_file.suffix.lower() == ".json":
            parser = parse_identity_candidates_json
        elif html_file.name.lower().endswith(
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

    if not participants:
        result_files = find_result_files(
            competition_directory
        )

        participants = merge_result_participants(
            result_files
        )

    if not participants:
        raise RuntimeError(
            "Aucun participant identifiable pour "
            f"{competition_code}"
        )

    hors_championnat_ids = (
        find_hors_championnat_only_iwwf_ids(
            competition_directory
        )
    )

    if hors_championnat_ids:
        participants = [
            participant
            for participant in participants
            if participant.iwwf_id
            not in hors_championnat_ids
        ]

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
                    participant.sexe or None,
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