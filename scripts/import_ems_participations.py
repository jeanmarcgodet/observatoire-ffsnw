from __future__ import annotations

import argparse
import sqlite3
import unicodedata
from dataclasses import dataclass

from observatoire.config import DATABASE_FILE
from observatoire.importers.iwwf_ems_participations import (
    EmsParticipant,
    load_competition_participations,
)


@dataclass(frozen=True)
class LocalRider:
    id: int
    ems_athlete_id: str | None
    nom: str
    prenom: str
    sexe: str | None
    nation: str | None
    annee_naissance: int | None


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    decomposed = unicodedata.normalize("NFKD", value)

    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )

    return " ".join(
        without_accents
        .upper()
        .replace("-", " ")
        .replace("'", " ")
        .split()
    )


def person_name_key(value: str | None) -> tuple[str, ...]:
    """
    Produit une clé indépendante de l'ordre nom/prénom.

    Exemple :
        'GERMAIN Pierre Louis'
        'Pierre Louis Germain'

    donnent la même clé.
    """
    normalized = normalize_text(value)

    if not normalized:
        return ()

    return tuple(sorted(normalized.split()))


def local_rider_name_key(rider: LocalRider) -> tuple[str, ...]:
    full_name = f"{rider.nom or ''} {rider.prenom or ''}"
    return person_name_key(full_name)


def load_local_riders(
    connection: sqlite3.Connection,
) -> list[LocalRider]:
    rows = connection.execute(
        """
        SELECT
            id,
            ems_athlete_id,
            nom,
            prenom,
            sexe,
            nation,
            annee_naissance
        FROM riders
        ORDER BY id
        """
    ).fetchall()

    return [
        LocalRider(
            id=row[0],
            ems_athlete_id=row[1],
            nom=row[2] or "",
            prenom=row[3] or "",
            sexe=row[4],
            nation=row[5],
            annee_naissance=row[6],
        )
        for row in rows
    ]


def find_matching_rider(
    participant: EmsParticipant,
    riders: list[LocalRider],
) -> tuple[LocalRider | None, str]:
    # Priorité absolue à l'identifiant EMS.
    by_ems_id = [
        rider
        for rider in riders
        if rider.ems_athlete_id == participant.ems_athlete_id
    ]

    if len(by_ems_id) == 1:
        return by_ems_id[0], "ems_athlete_id"

    if len(by_ems_id) > 1:
        return None, "duplicate_ems_athlete_id"

    participant_name_key = person_name_key(
        participant.nom_complet
    )

    candidates = [
        rider
        for rider in riders
        if local_rider_name_key(rider) == participant_name_key
    ]

    # Filtrage par année de naissance lorsque disponible.
    if participant.annee_naissance is not None:
        birth_year_candidates = [
            rider
            for rider in candidates
            if rider.annee_naissance
            in (None, participant.annee_naissance)
        ]

        if birth_year_candidates:
            candidates = birth_year_candidates

    # Filtrage par nation lorsque disponible.
    participant_nation = normalize_text(participant.nation)

    if participant_nation:
        nation_candidates = [
            rider
            for rider in candidates
            if normalize_text(rider.nation)
            in ("", participant_nation)
        ]

        if nation_candidates:
            candidates = nation_candidates

    if len(candidates) == 1:
        return candidates[0], "name_birth_country"

    if len(candidates) > 1:
        return None, "ambiguous_name"

    return None, "not_found"


def update_rider_from_ems(
    connection: sqlite3.Connection,
    rider: LocalRider,
    participant: EmsParticipant,
) -> None:
    connection.execute(
        """
        UPDATE riders
        SET
            ems_athlete_id = ?,
            sexe = COALESCE(sexe, ?),
            nation = COALESCE(NULLIF(nation, ''), ?),
            annee_naissance = COALESCE(
                annee_naissance,
                ?
            )
        WHERE id = ?
        """,
        (
            participant.ems_athlete_id,
            participant.sexe,
            participant.nation,
            participant.annee_naissance,
            rider.id,
        ),
    )


def ensure_entry(
    connection: sqlite3.Connection,
    competition_id: int,
    rider_id: int,
    category: str,
) -> str:
    """
    Ajoute l'inscription EMS si elle n'existe pas déjà.

    Une catégorie existante n'est jamais remplacée. Cela permet de
    conserver les inscriptions multicatégories réelles telles que :

        Open + 35+
        Open + 45+
        Open + 55+
    """
    existing = connection.execute(
        """
        SELECT id
        FROM entries
        WHERE competition_id = ?
          AND rider_id = ?
          AND categorie = ?
        LIMIT 1
        """,
        (
            competition_id,
            rider_id,
            category,
        ),
    ).fetchone()

    if existing is not None:
        return "entry_exists"

    cursor = connection.execute(
        """
        INSERT INTO entries (
            competition_id,
            rider_id,
            categorie,
            club,
            equipe
        )
        VALUES (?, ?, ?, NULL, NULL)
        ON CONFLICT (
            competition_id,
            rider_id,
            categorie
        ) DO NOTHING
        """,
        (
            competition_id,
            rider_id,
            category,
        ),
    )

    if cursor.rowcount == 1:
        return "entry_created"

    return "entry_exists"


def replace_entry_disciplines(
    connection: sqlite3.Connection,
    competition_id: int,
    rider_id: int,
    participant: EmsParticipant,
) -> int:
    connection.execute(
        """
        DELETE FROM entry_disciplines
        WHERE competition_id = ?
          AND rider_id = ?
          AND source = 'ems'
        """,
        (
            competition_id,
            rider_id,
        ),
    )

    inserted = 0

    for discipline in participant.disciplines:
        connection.execute(
            """
            INSERT INTO entry_disciplines (
                competition_id,
                rider_id,
                discipline,
                detail,
                source
            )
            VALUES (?, ?, ?, ?, 'ems')
            ON CONFLICT (
                competition_id,
                rider_id,
                discipline
            )
            DO UPDATE SET
                detail = excluded.detail,
                source = excluded.source
            """,
            (
                competition_id,
                rider_id,
                discipline.discipline,
                discipline.detail,
            ),
        )

        inserted += 1

    return inserted


def competition_exists(
    connection: sqlite3.Connection,
    competition_id: int,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM competitions
        WHERE id = ?
        """,
        (competition_id,),
    ).fetchone()

    return row is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Importe les participations publiques EMS "
            "dans la base locale."
        )
    )

    parser.add_argument(
        "local_competition_id",
        type=int,
        help=(
            "Identifiant numérique de la compétition "
            "dans la table competitions"
        ),
    )

    parser.add_argument(
        "ems_competition_id",
        help="UUID EMS de la compétition",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Applique réellement les modifications. "
            "Sans cette option, le script fonctionne "
            "en simulation."
        ),
    )

    args = parser.parse_args()

    participants = load_competition_participations(
        args.ems_competition_id
    )

    connection = sqlite3.connect(DATABASE_FILE)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        if not competition_exists(
            connection,
            args.local_competition_id,
        ):
            raise ValueError(
                "Compétition locale introuvable : "
                f"{args.local_competition_id}"
            )

        riders = load_local_riders(connection)

        matched_count = 0
        unmatched_count = 0
        discipline_count = 0
        entry_actions: dict[str, int] = {}

        print()
        print(
            "MODE :",
            "ÉCRITURE" if args.apply else "SIMULATION",
        )
        print()

        for participant in participants:
            rider, matching_method = find_matching_rider(
                participant,
                riders,
            )

            if rider is None:
                unmatched_count += 1

                print(
                    "[NON RAPPROCHÉ] "
                    f"{participant.nom_complet:<30} "
                    f"{participant.annee_naissance or '-'} "
                    f"| raison={matching_method}"
                )

                continue

            matched_count += 1

            print(
                "[OK] "
                f"{participant.nom_complet:<30} "
                f"-> rider_id={rider.id:<3} "
                f"| méthode={matching_method}"
            )

            if args.apply:
                update_rider_from_ems(
                    connection,
                    rider,
                    participant,
                )

                entry_action = ensure_entry(
                    connection,
                    args.local_competition_id,
                    rider.id,
                    participant.categorie,
                )

                entry_actions[entry_action] = (
                    entry_actions.get(entry_action, 0) + 1
                )

                discipline_count += (
                    replace_entry_disciplines(
                        connection,
                        args.local_competition_id,
                        rider.id,
                        participant,
                    )
                )

        print()
        print("Participants EMS :", len(participants))
        print("Rapprochés       :", matched_count)
        print("Non rapprochés   :", unmatched_count)

        if args.apply:
            print(
                "Disciplines écrites :",
                discipline_count,
            )

            print("Actions entries :")

            for action, count in sorted(
                entry_actions.items()
            ):
                print(f"  {action}: {count}")

            connection.commit()
            print()
            print("Import appliqué.")
        else:
            connection.rollback()
            print()
            print(
                "Aucune modification effectuée. "
                "Relancer avec --apply après contrôle."
            )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()