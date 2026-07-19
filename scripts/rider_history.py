from __future__ import annotations
from datetime import date

import argparse
import sys

from observatoire.queries.rider_history import (
    RiderHistory,
    get_rider_history,
    search_riders,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Afficher l'historique des performances d'un rider."
    )

    parser.add_argument(
        "recherche",
        help="Nom, prénom ou identifiant IWWF du rider.",
    )

    return parser


def format_rider_name(
    prenom: str | None,
    nom: str,
) -> str:
    if prenom:
        return f"{prenom} {nom}"

    return nom

def format_date_fr(value: str) -> str:
    months = (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    )

    parsed_date = date.fromisoformat(value)

    return (
        f"{parsed_date.day} "
        f"{months[parsed_date.month - 1]} "
        f"{parsed_date.year}"
    )

def display_history(history: RiderHistory) -> None:
    rider_name = format_rider_name(
        history.prenom,
        history.nom,
    )

    print()
    print(rider_name)
    print("=" * len(rider_name))
    print(f"Identifiant IWWF : {history.iwwf_id}")

    if history.nation:
        print(f"Nation : {history.nation}")

    if history.annee_naissance:
        print(f"Année de naissance : {history.annee_naissance}")

    print(f"Nombre de performances : {len(history.performances)}")

    if not history.performances:
        print()
        print("Aucune performance enregistrée.")
        return

    for performance in history.performances:
        print()
        print(
            f"{performance.competition_code} — "
            f"{performance.competition_nom}"
        )

        location_parts = [
            part
            for part in (
                performance.ville,
                performance.pays,
            )
            if part
        ]

        if location_parts:
            print(f"Lieu : {', '.join(location_parts)}")

        if performance.date_debut:
            date_debut = format_date_fr(performance.date_debut)

            if (
                performance.date_fin
                and performance.date_fin != performance.date_debut
            ):
                date_fin = format_date_fr(performance.date_fin)

                print(f"Dates : du {date_debut} au {date_fin}")
            else:
                print(f"Date : le {date_debut}")

        print(f"Discipline : {performance.discipline}")
        print(f"Tour : {performance.tour}")
        print(f"Score : {performance.score}")

        if performance.classifications:
            print("Classements :")

            for classification in performance.classifications:
                details: list[str] = []

                if classification.categorie:
                    details.append(classification.categorie)

                if classification.sexe:
                    details.append(classification.sexe)

                if classification.ligue:
                    details.append(classification.ligue)

                label = classification.classement

                if details:
                    label += f" — {' / '.join(details)}"

                rank = (
                    str(classification.rang)
                    if classification.rang is not None
                    else "non classé"
                )

                print(f"  - {label} : rang {rank}")
        else:
            print("Classements : aucun classement associé")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    matches = search_riders(args.recherche)

    if not matches:
        print(
            f"Aucun rider trouvé pour : {args.recherche}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if len(matches) > 1:
        print("Plusieurs riders correspondent à la recherche :")
        print()

        for rider in matches:
            name = format_rider_name(
                rider["prenom"],
                rider["nom"],
            )

            details = [
                value
                for value in (
                    rider["nation"],
                    str(rider["annee_naissance"])
                    if rider["annee_naissance"]
                    else None,
                    rider["iwwf_id"],
                )
                if value
            ]

            print(
                f"- ID base {rider['id']} : "
                f"{name} ({', '.join(details)})"
            )

        print()
        print(
            "Relance la commande avec le nom complet "
            "ou l'identifiant IWWF."
        )
        raise SystemExit(2)

    rider_id = matches[0]["id"]
    history = get_rider_history(rider_id)

    if history is None:
        print(
            "Le rider a été trouvé, mais son historique "
            "n'a pas pu être chargé.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    display_history(history)


if __name__ == "__main__":
    main()