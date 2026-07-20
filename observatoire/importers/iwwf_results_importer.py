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
    Déduit le type de classement à partir du nom du fichier IWWF.
    """
    stem = Path(filename).stem.lower()

    if stem.startswith("allm_"):
        return "Open Men"

    if stem.startswith("allf_"):
        return "Open Women"

    if stem.startswith("21_m_"):
        return "U21 Men"

    if stem.startswith("21_f_"):
        return "U21 Women"

    if stem.startswith("21_"):
        return "U21"

    return stem.removesuffix("_results")

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
    competition_directory: Path,
) -> list[Path]:
    """
    Écarte volontairement les pages de résultats live et les fichiers
    qui ne correspondent pas à des résultats.
    """
    files: list[Path] = []

    for path in competition_directory.glob("*_results.html"):
        lower_name = path.name.lower()

        if "live" in lower_name:
            continue

        files.append(path)

    return sorted(files)


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

                try:
                    result_id, result_created = get_or_create_result(
                        connection,
                        competition_id,
                        rider_id,
                        result,
                    )

                    if result_created:
                        report.resultats_ajoutes += 1
                    else:
                        report.resultats_existants += 1

                    classification_created = insert_classification(
                        connection,
                        result_id,
                        result,
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