"""Inventorie les sources disponibles pour reconstruire la filière U21 -> Open -> Senior.

Le script ne modifie aucune donnée existante. Il inspecte :
- la base SQLite data/observatoire.db ;
- les CSV présents dans data/processed, data/exports et data/reference ;
- les colonnes, volumes et quelques valeurs d'exemple utiles.

Sortie :
    data/exports/inventaire_sources_filiere_open.txt
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable


KEYWORDS = (
    "result",
    "classe",
    "participant",
    "participation",
    "ems",
    "champion",
    "ski",
    "rider",
    "athlete",
    "sportif",
    "category",
    "categorie",
    "birth",
    "yob",
    "year",
    "competition",
    "discipline",
    "event",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_relevant(name: str) -> bool:
    low = name.lower()
    return any(keyword in low for keyword in KEYWORDS)


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def safe_count(conn: sqlite3.Connection, table: str) -> str:
    try:
        value = conn.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table)}"
        ).fetchone()[0]
        return str(value)
    except sqlite3.Error as exc:
        return f"ERREUR: {exc}"


def inspect_database(db_path: Path) -> list[str]:
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append("BASE SQLITE")
    lines.append("=" * 100)
    lines.append(f"Chemin : {db_path}")

    if not db_path.exists():
        lines.append("ABSENTE")
        return lines

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        tables = [
            row[0]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]

        lines.append(f"Tables : {len(tables)}")
        lines.append("")

        for table in tables:
            columns = conn.execute(
                f"PRAGMA table_info({quote_identifier(table)})"
            ).fetchall()
            column_names = [str(row[1]) for row in columns]

            relevant = is_relevant(table) or any(is_relevant(col) for col in column_names)
            marker = "PERTINENTE" if relevant else "autre"

            lines.append(f"[{marker}] {table}")
            lines.append(f"  Lignes : {safe_count(conn, table)}")
            lines.append(
                "  Colonnes : "
                + ", ".join(
                    f"{row[1]} ({row[2] or 'type non déclaré'})"
                    for row in columns
                )
            )

            if relevant and column_names:
                selected_columns = column_names[:12]
                select_sql = ", ".join(
                    quote_identifier(col) for col in selected_columns
                )
                try:
                    rows = conn.execute(
                        f"SELECT {select_sql} "
                        f"FROM {quote_identifier(table)} "
                        "LIMIT 3"
                    ).fetchall()
                except sqlite3.Error as exc:
                    lines.append(f"  Exemples : ERREUR {exc}")
                else:
                    if not rows:
                        lines.append("  Exemples : aucune ligne")
                    for index, row in enumerate(rows, start=1):
                        values = []
                        for col in selected_columns:
                            value = row[col]
                            rendered = repr(value)
                            if len(rendered) > 120:
                                rendered = rendered[:117] + "..."
                            values.append(f"{col}={rendered}")
                        lines.append(f"  Exemple {index} : " + " | ".join(values))

            lines.append("")
    finally:
        conn.close()

    return lines


def csv_row_count(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        for _ in reader:
            count += 1
    return count


def inspect_csv(path: Path, root: Path) -> list[str]:
    lines: list[str] = []
    relative = path.relative_to(root)

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
            errors="replace",
        ) as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            samples = []
            for _, row in zip(range(3), reader):
                samples.append(row)
    except Exception as exc:
        return [f"[ERREUR] {relative} : {exc}", ""]

    relevant = is_relevant(path.name) or any(is_relevant(col) for col in headers)
    if not relevant:
        return []

    lines.append(f"[CSV] {relative}")
    try:
        lines.append(f"  Lignes : {csv_row_count(path)}")
    except Exception as exc:
        lines.append(f"  Lignes : ERREUR {exc}")

    lines.append("  Colonnes : " + ", ".join(headers))

    for index, row in enumerate(samples, start=1):
        values = []
        for col in headers[:12]:
            rendered = repr(row.get(col))
            if len(rendered) > 120:
                rendered = rendered[:117] + "..."
            values.append(f"{col}={rendered}")
        lines.append(f"  Exemple {index} : " + " | ".join(values))

    lines.append("")
    return lines


def iter_csv_files(root: Path) -> Iterable[Path]:
    for relative_dir in (
        Path("data/processed"),
        Path("data/exports"),
        Path("data/reference"),
        Path("data/raw"),
    ):
        directory = root / relative_dir
        if not directory.exists():
            continue
        yield from sorted(directory.rglob("*.csv"))


def main() -> None:
    root = repo_root()
    output = root / "data/exports/inventaire_sources_filiere_open.txt"
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("INVENTAIRE DES SOURCES — FILIÈRE U21 → OPEN → SENIOR")
    lines.append(f"Dépôt : {root}")
    lines.append("")

    lines.extend(inspect_database(root / "data/observatoire.db"))
    lines.append("")
    lines.append("=" * 100)
    lines.append("FICHIERS CSV PERTINENTS")
    lines.append("=" * 100)
    lines.append("")

    csv_count = 0
    for csv_path in iter_csv_files(root):
        block = inspect_csv(csv_path, root)
        if block:
            csv_count += 1
            lines.extend(block)

    lines.append(f"Nombre de CSV pertinents inventoriés : {csv_count}")
    lines.append("")
    lines.append("FIN DE L'INVENTAIRE")

    text = "\n".join(lines)
    output.write_text(text, encoding="utf-8")

    print("=" * 88)
    print("INVENTAIRE TERMINE")
    print("=" * 88)
    print(f"Sortie : {output}")
    print(f"Caractères : {len(text)}")
    print("")
    print("Copiez ensuite le contenu du fichier ou au minimum les blocs")
    print("'BASE SQLITE' et 'FICHIERS CSV PERTINENTS' dans la conversation.")


if __name__ == "__main__":
    main()
