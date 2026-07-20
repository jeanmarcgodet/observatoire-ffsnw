from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from observatoire.repository import ParticipationRepository


ALLOWED_COLLECTION_STATUSES = {
    "a_collecter",
    "partielle",
    "complete",
    "controlee",
    "exclue",
}

ALLOWED_LEVELS = {
    "championnat_france",
    "competition_nationale",
    "competition_regionale",
    "competition_internationale",
}

ALLOWED_TARGET_POPULATIONS = {
    "open_u21",
    "open",
    "open_open_de_france",
    "open_senior_handi",
}


@dataclass(frozen=True)
class CompetitionInventoryRow:
    iwwf_id: str
    nom: str
    date_debut: str | None
    date_fin: str | None
    annee: int | None
    pays: str | None
    ville: str | None
    discipline: str | None
    niveau: str | None
    population_cible: str | None
    statut_collecte: str
    source_url: str | None


@dataclass
class ImportStats:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def parse_year(
    value: str | None,
    *,
    date_debut: str | None,
) -> int | None:
    cleaned = clean_text(value)

    if cleaned:
        try:
            year = int(cleaned)
        except ValueError as error:
            raise ValueError(
                f"Année invalide : {cleaned!r}"
            ) from error

        if year < 1900 or year > 2100:
            raise ValueError(
                f"Année hors plage : {year}"
            )

        return year

    if date_debut and len(date_debut) >= 4:
        prefix = date_debut[:4]

        if prefix.isdigit():
            return int(prefix)

    return None


def validate_date(
    value: str | None,
    field_name: str,
) -> str | None:
    cleaned = clean_text(value)

    if cleaned is None:
        return None

    if len(cleaned) != 10:
        raise ValueError(
            f"{field_name} invalide : "
            f"{cleaned!r}. Format attendu : YYYY-MM-DD"
        )

    year, separator_1, month, separator_2, day = (
        cleaned[:4],
        cleaned[4],
        cleaned[5:7],
        cleaned[7],
        cleaned[8:10],
    )

    if (
        separator_1 != "-"
        or separator_2 != "-"
        or not year.isdigit()
        or not month.isdigit()
        or not day.isdigit()
    ):
        raise ValueError(
            f"{field_name} invalide : "
            f"{cleaned!r}. Format attendu : YYYY-MM-DD"
        )

    month_number = int(month)
    day_number = int(day)

    if not 1 <= month_number <= 12:
        raise ValueError(
            f"Mois invalide dans {field_name} : {cleaned!r}"
        )

    if not 1 <= day_number <= 31:
        raise ValueError(
            f"Jour invalide dans {field_name} : {cleaned!r}"
        )

    return cleaned


def row_from_csv(
    raw_row: dict[str, str],
    line_number: int,
) -> CompetitionInventoryRow:
    iwwf_id = clean_text(raw_row.get("iwwf_id"))
    nom = clean_text(raw_row.get("nom"))

    if not iwwf_id:
        raise ValueError(
            f"Ligne {line_number} : iwwf_id manquant"
        )

    if not nom:
        raise ValueError(
            f"Ligne {line_number} : nom manquant"
        )

    date_debut = validate_date(
        raw_row.get("date_debut"),
        "date_debut",
    )

    date_fin = validate_date(
        raw_row.get("date_fin"),
        "date_fin",
    )

    annee = parse_year(
        raw_row.get("annee"),
        date_debut=date_debut,
    )

    niveau = clean_text(raw_row.get("niveau"))

    if (
        niveau is not None
        and niveau not in ALLOWED_LEVELS
    ):
        raise ValueError(
            f"Ligne {line_number} : "
            f"niveau inconnu {niveau!r}"
        )

    population_cible = clean_text(
        raw_row.get("population_cible")
    )

    if (
        population_cible is not None
        and population_cible
        not in ALLOWED_TARGET_POPULATIONS
    ):
        raise ValueError(
            f"Ligne {line_number} : "
            f"population_cible inconnue "
            f"{population_cible!r}"
        )

    statut_collecte = (
        clean_text(
            raw_row.get("statut_collecte")
        )
        or "a_collecter"
    )

    if statut_collecte not in ALLOWED_COLLECTION_STATUSES:
        raise ValueError(
            f"Ligne {line_number} : "
            f"statut_collecte inconnu "
            f"{statut_collecte!r}"
        )

    return CompetitionInventoryRow(
        iwwf_id=iwwf_id,
        nom=nom,
        date_debut=date_debut,
        date_fin=date_fin,
        annee=annee,
        pays=clean_text(raw_row.get("pays")),
        ville=clean_text(raw_row.get("ville")),
        discipline=clean_text(
            raw_row.get("discipline")
        ),
        niveau=niveau,
        population_cible=population_cible,
        statut_collecte=statut_collecte,
        source_url=clean_text(
            raw_row.get("source_url")
        ),
    )


def load_inventory(
    csv_path: Path,
) -> list[CompetitionInventoryRow]:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        required_columns = {
            "iwwf_id",
            "nom",
            "date_debut",
            "date_fin",
            "annee",
            "pays",
            "ville",
            "discipline",
            "niveau",
            "population_cible",
            "statut_collecte",
            "source_url",
        }

        fieldnames = set(reader.fieldnames or [])

        missing_columns = (
            required_columns - fieldnames
        )

        if missing_columns:
            raise ValueError(
                "Colonnes absentes du CSV : "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        inventory: list[
            CompetitionInventoryRow
        ] = []

        seen_iwwf_ids: set[str] = set()

        for line_number, raw_row in enumerate(
            reader,
            start=2,
        ):
            if not any(
                clean_text(value)
                for value in raw_row.values()
            ):
                continue

            row = row_from_csv(
                raw_row,
                line_number,
            )

            if row.iwwf_id in seen_iwwf_ids:
                raise ValueError(
                    f"Ligne {line_number} : "
                    f"iwwf_id dupliqué dans le CSV : "
                    f"{row.iwwf_id}"
                )

            seen_iwwf_ids.add(row.iwwf_id)
            inventory.append(row)

    return inventory


def table_columns(
    connection: Any,
    table_name: str,
) -> set[str]:
    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def ensure_source_url_column(
    connection: Any,
) -> None:
    columns = table_columns(
        connection,
        "competitions",
    )

    if "source_url" in columns:
        return

    connection.execute(
        """
        ALTER TABLE competitions
        ADD COLUMN source_url TEXT
        """
    )

    print(
        "Colonne ajoutée : "
        "competitions.source_url"
    )


def ensure_population_cible_column(
    connection: Any,
) -> None:
    columns = table_columns(
        connection,
        "competitions",
    )

    if "population_cible" in columns:
        return

    connection.execute(
        """
        ALTER TABLE competitions
        ADD COLUMN population_cible TEXT
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_population_cible
        ON competitions(population_cible)
        """
    )

    print(
        "Colonne ajoutée : "
        "competitions.population_cible"
    )


def ensure_competition_columns(
    connection: Any,
) -> None:
    ensure_source_url_column(connection)
    ensure_population_cible_column(connection)

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_competitions_population_cible
        ON competitions(population_cible)
        """
    )


def get_existing_competition(
    connection: Any,
    iwwf_id: str,
) -> Any | None:
    return connection.execute(
        """
        SELECT
            id,
            iwwf_id,
            nom,
            date_debut,
            date_fin,
            annee,
            pays,
            ville,
            discipline,
            niveau,
            population_cible,
            statut_collecte,
            source_url
        FROM competitions
        WHERE iwwf_id = ?
        """,
        (iwwf_id,),
    ).fetchone()


def normalized_existing_value(
    value: Any,
) -> Any:
    if isinstance(value, str):
        return value.strip() or None

    return value


def changed_fields(
    existing: Any,
    inventory_row: CompetitionInventoryRow,
) -> dict[str, Any]:
    desired = {
        "nom": inventory_row.nom,
        "date_debut": inventory_row.date_debut,
        "date_fin": inventory_row.date_fin,
        "annee": inventory_row.annee,
        "pays": inventory_row.pays,
        "ville": inventory_row.ville,
        "discipline": inventory_row.discipline,
        "niveau": inventory_row.niveau,
        "population_cible": (
            inventory_row.population_cible
        ),
        "statut_collecte": (
            inventory_row.statut_collecte
        ),
        "source_url": inventory_row.source_url,
    }

    changes: dict[str, Any] = {}

    for field_name, desired_value in desired.items():
        current_value = normalized_existing_value(
            existing[field_name]
        )

        if current_value != desired_value:
            changes[field_name] = desired_value

    return changes


def create_competition(
    connection: Any,
    row: CompetitionInventoryRow,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO competitions (
            iwwf_id,
            nom,
            date_debut,
            date_fin,
            annee,
            pays,
            ville,
            discipline,
            niveau,
            population_cible,
            statut_collecte,
            source_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.iwwf_id,
            row.nom,
            row.date_debut,
            row.date_fin,
            row.annee,
            row.pays,
            row.ville,
            row.discipline,
            row.niveau,
            row.population_cible,
            row.statut_collecte,
            row.source_url,
        ),
    )

    return int(cursor.lastrowid)


def update_competition(
    connection: Any,
    competition_id: int,
    changes: dict[str, Any],
) -> None:
    assignments = ", ".join(
        f'"{field_name}" = ?'
        for field_name in changes
    )

    values = list(changes.values())
    values.append(competition_id)

    connection.execute(
        f"""
        UPDATE competitions
        SET {assignments}
        WHERE id = ?
        """,
        values,
    )


def import_inventory(
    connection: Any,
    rows: list[CompetitionInventoryRow],
    *,
    apply_changes: bool,
) -> ImportStats:
    stats = ImportStats()

    for row in rows:
        existing = get_existing_competition(
            connection,
            row.iwwf_id,
        )

        if existing is None:
            if apply_changes:
                competition_id = create_competition(
                    connection,
                    row,
                )

                print(
                    f"[CRÉÉE] id={competition_id} "
                    f"{row.iwwf_id} — {row.nom}"
                )
            else:
                print(
                    f"[À CRÉER] {row.iwwf_id} — "
                    f"{row.nom}"
                )

            stats.created += 1
            continue

        changes = changed_fields(
            existing,
            row,
        )

        if not changes:
            print(
                f"[INCHANGÉE] id={existing['id']} "
                f"{row.iwwf_id} — {row.nom}"
            )

            stats.unchanged += 1
            continue

        if apply_changes:
            update_competition(
                connection,
                int(existing["id"]),
                changes,
            )

            print(
                f"[MISE À JOUR] id={existing['id']} "
                f"{row.iwwf_id} — {row.nom}"
            )
        else:
            print(
                f"[À METTRE À JOUR] "
                f"id={existing['id']} "
                f"{row.iwwf_id} — {row.nom}"
            )

        for field_name, new_value in changes.items():
            old_value = normalized_existing_value(
                existing[field_name]
            )

            print(
                f"    {field_name}: "
                f"{old_value!r} -> {new_value!r}"
            )

        stats.updated += 1

    return stats


def print_summary(
    stats: ImportStats,
    *,
    apply_changes: bool,
) -> None:
    print()
    print("RÉSUMÉ")
    print("======")

    mode = (
        "APPLICATION"
        if apply_changes
        else "SIMULATION"
    )

    print(f"Mode        : {mode}")
    print(f"Créées      : {stats.created}")
    print(f"Mises à jour: {stats.updated}")
    print(f"Inchangées  : {stats.unchanged}")
    print(f"Ignorées    : {stats.skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Importe l'inventaire longitudinal "
            "des compétitions."
        )
    )

    parser.add_argument(
        "csv_path",
        nargs="?",
        default="data/competition_inventory.csv",
        help=(
            "Chemin du fichier CSV. "
            "Valeur par défaut : "
            "data/competition_inventory.csv"
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Applique réellement les créations "
            "et les mises à jour."
        ),
    )

    args = parser.parse_args()

    csv_path = Path(args.csv_path)

    inventory = load_inventory(csv_path)

    print()
    print("IMPORT DE L'INVENTAIRE")
    print("======================")
    print()
    print(f"Fichier      : {csv_path}")
    print(f"Compétitions: {len(inventory)}")
    print(
        "Mode         :",
        (
            "APPLICATION"
            if args.apply
            else "SIMULATION"
        ),
    )
    print()

    repository = ParticipationRepository()

    with repository.connect() as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        ensure_competition_columns(connection)

        stats = import_inventory(
            connection,
            inventory,
            apply_changes=args.apply,
        )

        if args.apply:
            connection.commit()
        else:
            connection.rollback()

    print_summary(
        stats,
        apply_changes=args.apply,
    )


if __name__ == "__main__":
    main()