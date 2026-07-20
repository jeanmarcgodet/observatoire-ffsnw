from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from observatoire.config import DATABASE_FILE
from observatoire.importers.iwwf_results import (
    IWWFResult,
    parse_results_file,
)


@dataclass
class ImportReport:
    competition_code: str
    fichiers_detectes: int = 0
    fichiers_importes: int = 0
    resultats_parses: int = 0
    resultats_ajoutes: int = 0
    resultats_existants: int = 0
    classifications_ajoutees: int = 0
    classifications_existantes: int = 0
    riders_introuvables: int = 0
    erreurs: int = 0


def get_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {str(row[1]) for row in rows}


def resolve_competition_code_column(
    connection: sqlite3.Connection,
) -> str:
    columns = get_table_columns(connection, "competitions")

    candidates = (
        "iwwf_id",
        "code",
        "competition_code",
        "iwwf_code",
        "code_iwwf",
    )

    for candidate in candidates:
        if candidate in columns:
            return candidate

    raise RuntimeError(
        "Impossible d'identifier la colonne du code IWWF dans "
        f"competitions. Colonnes présentes : {sorted(columns)}"
    )


def get_competition_id(
    connection: sqlite3.Connection,
    competition_code: str,
) -> int:
    code_column = resolve_competition_code_column(connection)

    row = connection.execute(
        f"""
        SELECT id
        FROM competitions
        WHERE {code_column} = ?
        """,
        (competition_code,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Compétition {competition_code} absente de la base. "
            "Importe d'abord les participants."
        )

    return int(row[0])


def normalize_category(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        return None

    aliases = {
        "Ope": "Open",
        "OPEN": "Open",
        "open": "Open",
        "-10": "U10",
        "-12": "U12",
        "-14": "U14",
        "-17": "U17",
        "-18": "U18",
        "-21": "U21",
        "u10": "U10",
        "u12": "U12",
        "u14": "U14",
        "u17": "U17",
        "u18": "U18",
        "u21": "U21",
    }

    return aliases.get(
        normalized,
        aliases.get(
            normalized.lower(),
            normalized,
        ),
    )


def get_entry_identity(
    connection: sqlite3.Connection,
    competition_id: int,
    rider_id: int,
) -> tuple[str | None, str | None]:
    rows = connection.execute(
        """
        SELECT
            e.categorie,
            r.sexe
        FROM entries e
        JOIN riders r
          ON r.id = e.rider_id
        WHERE e.competition_id = ?
          AND e.rider_id = ?
        ORDER BY e.id
        """,
        (
            competition_id,
            rider_id,
        ),
    ).fetchall()

    categories = {
        category
        for raw_category, _ in rows
        if (
            category := normalize_category(
                raw_category
            )
        )
    }

    sexes = {
        str(raw_sex).strip().upper()
        for _, raw_sex in rows
        if (
            raw_sex is not None
            and str(raw_sex).strip().upper()
            in {"M", "F"}
        )
    }

    categorie = (
        next(iter(categories))
        if len(categories) == 1
        else None
    )

    sexe = (
        next(iter(sexes))
        if len(sexes) == 1
        else None
    )

    return categorie, sexe


def complete_result_identity(
    connection: sqlite3.Connection,
    competition_id: int,
    rider_id: int,
    result: IWWFResult,
) -> IWWFResult:
    entry_category, entry_sex = get_entry_identity(
        connection,
        competition_id,
        rider_id,
    )

    categorie = normalize_category(
        result.categorie
        or entry_category
    )

    sexe = result.sexe or entry_sex

    if sexe is not None:
        sexe = sexe.strip().upper() or None

    return IWWFResult(
        iwwf_id=result.iwwf_id,
        nom_complet=result.nom_complet,
        ligue=result.ligue,
        categorie=categorie,
        sexe=sexe,
        discipline=result.discipline,
        tour=result.tour,
        rang_classement=result.rang_classement,
        score=result.score,
        document_url=result.document_url,
        fichier_source=result.fichier_source,
    )


def get_rider_id(
    connection: sqlite3.Connection,
    iwwf_id: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT id
        FROM riders
        WHERE iwwf_id = ?
        """,
        (iwwf_id,),
    ).fetchone()

    return int(row[0]) if row is not None else None


def get_classement_from_filename(
    filename: str,
) -> str:
    """
    D?duit le classement ? partir du nom du fichier IWWF.
    """
    stem = (
        Path(filename)
        .stem
        .lower()
        .removesuffix("_results")
    )

    if stem == "all_slalom_results_45":
        return "45+/55+ Men"

    if stem.startswith("all_skiers_"):
        return "All Skiers"

    if stem.startswith("65_m_70_m_75_m_"):
        return "65+/70+/75+ Men"

    if stem.startswith("65_70_75_"):
        return "65+/70+/75+"

    if stem.startswith("70_m_75_m_"):
        return "70+/75+ Men"

    if stem.startswith(("allm_", "men_")):
        return "Open Men"

    if stem.startswith(("allf_", "women_")):
        return "Open Women"

    parts = stem.split("_")
    first = parts[0]
    second = parts[1] if len(parts) > 1 else None

    categories = {
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

    categorie = categories.get(first)
    sexe = {
        "m": "Men",
        "f": "Women",
    }.get(second)

    if categorie and sexe:
        return f"{categorie} {sexe}"

    if categorie:
        return categorie

    return stem



def get_or_create_result(
    connection: sqlite3.Connection,
    competition_id: int,
    rider_id: int,
    result: IWWFResult,
) -> tuple[int, bool]:
    """
    Retourne :
        (result_id, created)

    Une performance est identifiée par :
        compétition
        rider
        discipline
        tour
        score
    """
    row = connection.execute(
        """
        SELECT id
        FROM results
        WHERE competition_id = ?
          AND rider_id = ?
          AND discipline = ?
          AND tour = ?
          AND score = ?
        LIMIT 1
        """,
        (
            competition_id,
            rider_id,
            result.discipline,
            result.tour,
            result.score,
        ),
    ).fetchone()

    if row is not None:
        return int(row[0]), False

    cursor = connection.execute(
        """
        INSERT INTO results (
            competition_id,
            rider_id,
            discipline,
            tour,
            score,
            document_url
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            competition_id,
            rider_id,
            result.discipline,
            result.tour,
            result.score,
            result.document_url,
        ),
    )

    if cursor.lastrowid is None:
        raise RuntimeError(
            "Impossible de récupérer l'identifiant du résultat inséré."
        )

    return int(cursor.lastrowid), True


def insert_classification(
    connection: sqlite3.Connection,
    result_id: int,
    result: IWWFResult,
    classement: str,
    fichier_source: str,
) -> bool:
    """
    Insère une classification.

    Retourne True si une ligne a été ajoutée, False si elle existait
    déjà.
    """
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO result_classifications (
            result_id,
            classement,
            categorie,
            sexe,
            rang,
            ligue,
            fichier_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_id,
            classement,
            result.categorie,
            result.sexe,
            result.rang_classement,
            result.ligue,
            fichier_source,
        ),
    )

    return cursor.rowcount == 1


def find_result_files(
    competition_directory: str | Path,
) -> list[Path]:
    """
    S?lectionne les pages de r?sultats.

    Les variantes _fra et _gbr sont retenues uniquement
    lorsqu'aucun fichier principal *_results.html
    n'existe pour le m?me classement.
    """
    directory = Path(competition_directory)

    candidates = {
        *directory.glob("*_results.html"),
        *directory.glob("*_results_fra.html"),
        *directory.glob("*_results_gbr.html"),
    }

    # Classement officiel Seniors 2026 dont le suffixe
    # ne suit pas la convention habituelle *_results.html.
    combined_senior_file = (
        directory / "all_slalom_results_45.html"
    )

    if combined_senior_file.exists():
        candidates.add(combined_senior_file)

    # Le fichier *_hf correspond au classement
    # hors Championnat de France et reste exclu.
    candidates.discard(
        directory / "all_slalom_results_hf.html"
    )

    groups: dict[str, list[Path]] = {}

    for candidate in candidates:
        canonical_stem = candidate.stem.lower()

        for suffix in ("_fra", "_gbr"):
            if canonical_stem.endswith(suffix):
                canonical_stem = canonical_stem[
                    : -len(suffix)
                ]
                break

        groups.setdefault(
            canonical_stem,
            [],
        ).append(candidate)

    selected: list[Path] = []

    for canonical_stem, group in groups.items():
        principal = [
            candidate
            for candidate in group
            if candidate.stem.lower()
            == canonical_stem
        ]

        if principal:
            selected.extend(principal)
        else:
            selected.extend(group)

    return sorted(
        selected,
        key=lambda candidate: candidate.name.lower(),
    )



def import_competition_results(
    competition_code: str,
    raw_root: str | Path = "data/raw/iwwf",
    database_file: str | Path = DATABASE_FILE,
    verbose: bool = False,
) -> ImportReport:
    competition_code = competition_code.strip()
    competition_directory = Path(raw_root) / competition_code

    if not competition_directory.exists():
        raise FileNotFoundError(
            "Dossier de compétition introuvable : "
            f"{competition_directory}"
        )

    files = find_result_files(competition_directory)

    if not files:
        raise RuntimeError(
            "Aucun fichier *_results.html trouvé dans "
            f"{competition_directory}"
        )

    report = ImportReport(
        competition_code=competition_code,
        fichiers_detectes=len(files),
    )

    connection = sqlite3.connect(database_file)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        competition_id = get_competition_id(
            connection,
            competition_code,
        )

        for html_file in files:
            try:
                results = parse_results_file(html_file)

            except RuntimeError as exc:
                message = str(exc)

                if "Aucune table de résultats reconnue" in message:
                    if verbose:
                        print(
                            f"[IGNORÉ] {html_file.name} : "
                            "aucune table de résultats"
                        )
                    continue

                report.erreurs += 1

                if verbose:
                    print(
                        f"[ERREUR] {html_file.name} : "
                        f"{type(exc).__name__}: {exc}"
                    )

                continue

            except Exception as exc:
                report.erreurs += 1

                if verbose:
                    print(
                        f"[ERREUR] {html_file.name} : "
                        f"{type(exc).__name__}: {exc}"
                    )

                continue

            report.fichiers_importes += 1
            report.resultats_parses += len(results)

            classement = get_classement_from_filename(
                html_file.name
            )

            if verbose:
                print(
                    f"[OK] {html_file.name} : "
                    f"{len(results)} résultat(s) — "
                    f"{classement}"
                )

            for result in results:
                rider_id = get_rider_id(
                    connection,
                    result.iwwf_id,
                )

                if rider_id is None:
                    report.riders_introuvables += 1

                    if verbose:
                        print(
                            "  [RIDER ABSENT] "
                            f"{result.iwwf_id} — "
                            f"{result.nom_complet}"
                        )

                    continue

                completed_result = complete_result_identity(
                    connection,
                    competition_id,
                    rider_id,
                    result,
                )

                try:
                    result_id, result_created = get_or_create_result(
                        connection,
                        competition_id,
                        rider_id,
                        completed_result,
                    )

                    if result_created:
                        report.resultats_ajoutes += 1
                    else:
                        report.resultats_existants += 1

                    classification_created = insert_classification(
                        connection,
                        result_id,
                        completed_result,
                        classement,
                        html_file.name,
                    )

                    if classification_created:
                        report.classifications_ajoutees += 1
                    else:
                        report.classifications_existantes += 1

                except Exception as exc:
                    report.erreurs += 1

                    if verbose:
                        print(
                            "  [ERREUR RÉSULTAT] "
                            f"{result.iwwf_id} — "
                            f"{result.nom_complet} — "
                            f"{type(exc).__name__}: {exc}"
                        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return report