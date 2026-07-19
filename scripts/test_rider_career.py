from observatoire.services import HistoryService


def main() -> None:
    service = HistoryService()

    career = service.get_rider_career("FRA692015508")

    if career is None:
        print("Rider introuvable.")
        return

    print("Carrière")
    print("--------")
    print(f"Rider                 : {career.rider.nom_complet}")
    print(f"Identifiant IWWF      : {career.rider.iwwf_id}")
    print(f"Nombre de résultats   : {career.number_of_results}")
    print(f"Nombre de compétitions: {career.number_of_competitions}")
    print(f"Disciplines            : {', '.join(career.disciplines)}")
    print(
        "Saisons                : "
        + ", ".join(str(season) for season in career.seasons)
    )

    print()
    print("Première compétition")
    print("--------------------")

    if career.first_competition is None:
        print("Aucune compétition.")
    else:
        print(career.first_competition.nom)
        print(career.first_competition.periode)

    print()
    print("Dernière compétition")
    print("--------------------")

    if career.last_competition is None:
        print("Aucune compétition.")
    else:
        print(career.last_competition.nom)
        print(career.last_competition.periode)

    print()
    print("Résultats")
    print("---------")

    if not career.results:
        print("Aucun résultat enregistré.")
    else:
        for result in career.results:
            print(
                f"{result.competition.periode} | "
                f"{result.competition.nom} | "
                f"{result.discipline} | "
                f"{result.tour} | "
                f"{result.score}"
            )


if __name__ == "__main__":
    main()
