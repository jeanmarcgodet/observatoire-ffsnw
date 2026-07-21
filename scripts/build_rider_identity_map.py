"""Construit la table complete des identites canoniques."""

from __future__ import annotations

import csv
import re
import sqlite3
import unicodedata
from pathlib import Path

from observatoire.config import DATABASE_FILE


AUTO_FILE = Path(
    "data/reference/rider_identity_aliases.csv"
)

OUTPUT_FILE = Path(
    "data/reference/rider_identity_map.csv"
)

MANUAL_PAIRS = (
    (1831, 604),  # Karine Emmett
    (1773, 10),   # Gaspard Gilg
    (776, 583),   # Joshua Verhaeghe-Pellicer
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value or "",
    )

    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    return re.sub(
        r"[^A-Z0-9]+",
        "",
        value.upper(),
    )


def main() -> None:
    if not AUTO_FILE.exists():
        raise FileNotFoundError(AUTO_FILE)

    with AUTO_FILE.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        automatic_rows = list(
            csv.DictReader(
                handle,
                delimiter=";",
            )
        )

    with sqlite3.connect(DATABASE_FILE) as database:
        riders = {
            row[0]: {
                "rider_id": row[0],
                "iwwf_id": row[1] or "",
                "nom": row[2] or "",
                "prenom": row[3] or "",
                "sexe": (row[4] or "").strip().upper(),
            }
            for row in database.execute(
                """
                SELECT
                    id,
                    iwwf_id,
                    nom,
                    prenom,
                    sexe
                FROM riders
                """
            )
        }

    manual_rows = []

    for alias_id, canonical_id in MANUAL_PAIRS:
        alias = riders.get(alias_id)
        canonical = riders.get(canonical_id)

        if alias is None or canonical is None:
            raise RuntimeError(
                f"Rider absent: {alias_id} ou {canonical_id}"
            )

        alias_key = (
            normalize_text(alias["nom"]),
            normalize_text(alias["prenom"]),
            alias["sexe"],
        )

        canonical_key = (
            normalize_text(canonical["nom"]),
            normalize_text(canonical["prenom"]),
            canonical["sexe"],
        )

        if alias_key != canonical_key:
            raise RuntimeError(
                "Identites incompatibles: "
                f"{alias_id} et {canonical_id}"
            )

        manual_rows.append(
            {
                "alias_rider_id": alias_id,
                "canonical_rider_id": canonical_id,
                "alias_iwwf_id": alias["iwwf_id"],
                "canonical_iwwf_id": (
                    canonical["iwwf_id"]
                ),
                "nom": canonical["nom"],
                "prenom": canonical["prenom"],
                "sexe": canonical["sexe"],
                "regle": (
                    "validation_manuelle_"
                    "nom_sexe_chronologie"
                ),
            }
        )

    all_rows = automatic_rows + manual_rows
    alias_map = {}

    for row in all_rows:
        alias_id = int(row["alias_rider_id"])
        canonical_id = int(
            row["canonical_rider_id"]
        )

        previous = alias_map.get(alias_id)

        if (
            previous is not None
            and previous != canonical_id
        ):
            raise RuntimeError(
                f"Conflit pour le rider {alias_id}"
            )

        alias_map[alias_id] = canonical_id

    if len(automatic_rows) != 114:
        raise RuntimeError(
            "114 correspondances automatiques "
            f"attendues, {len(automatic_rows)} obtenues."
        )

    if len(manual_rows) != 3:
        raise RuntimeError(
            "3 correspondances manuelles attendues."
        )

    if len(alias_map) != 117:
        raise RuntimeError(
            "117 alias uniques attendus, "
            f"{len(alias_map)} obtenus."
        )

    all_rows.sort(
        key=lambda row: (
            row["nom"],
            row["prenom"],
            int(row["alias_rider_id"]),
        )
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "alias_rider_id",
                "canonical_rider_id",
                "alias_iwwf_id",
                "canonical_iwwf_id",
                "nom",
                "prenom",
                "sexe",
                "regle",
            ],
            delimiter=";",
        )

        writer.writeheader()
        writer.writerows(all_rows)

    print("=" * 78)
    print("TABLE D'IDENTITES CANONIQUES")
    print("=" * 78)
    print(
        "Correspondances automatiques :",
        len(automatic_rows),
    )
    print(
        "Correspondances manuelles    :",
        len(manual_rows),
    )
    print(
        "Correspondances totales      :",
        len(alias_map),
    )
    print("Fichier :", OUTPUT_FILE)


if __name__ == "__main__":
    main()
