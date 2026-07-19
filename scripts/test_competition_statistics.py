"""Test manuel des statistiques d'une compétition."""

from observatoire.services import HistoryService


def display_best_result(
    label: str,
    result,
    statistics,
    suffix: str = "",
) -> None:
    """Affiche un meilleur résultat."""
    if result is None:
        print(f"{label:<8}: aucun résultat")
        return

    rider_name = statistics.rider_name(result) or "Rider inconnu"

    print(
        f"{label:<8}: {result.score}{suffix} "
        f"— {rider_name}"
    )


def main() -> None:
    service = HistoryService()
    competitions = service.list_competitions()

    if not competitions:
        print("Aucune compétition trouvée.")
        return

    competition = competitions[0]

    report = service.get_competition_report(
        competition.iwwf_id
    )

    if report is None:
        print("Compétition introuvable.")
        return

    statistics = report.statistics

    print(report.competition.nom)
    print("=" * len(report.competition.nom))
    print()

    print(f"Résultats     : {statistics.number_of_results}")
    print(f"Riders        : {statistics.number_of_riders}")
    print(f"Nations       : {statistics.number_of_nations}")
    print(
        "Disciplines   : "
        + ", ".join(statistics.disciplines)
    )
    print(f"Finales       : {statistics.number_of_finals}")

    print()
    print("Meilleures performances")
    print("------------------------")

    display_best_result(
        "Slalom",
        statistics.best_slalom(),
        statistics,
    )

    display_best_result(
        "Tricks",
        statistics.best_tricks(),
        statistics,
    )

    display_best_result(
        "Jump",
        statistics.best_jump(),
        statistics,
    )

    display_best_result(
        "Overall",
        statistics.best_overall_component(),
        statistics,
    )

    print()
    print("Riders par discipline")
    print("----------------------")

    for discipline in statistics.disciplines:
        riders = statistics.riders_for(discipline)

        print(
            f"{discipline.capitalize():<12}: "
            f"{len(riders)}"
        )

    print()
    print("Répartition par nation")
    print("----------------------")

    if statistics.nation_counts:
        for nation, count in statistics.nation_counts.items():
            print(f"{nation:<12}: {count}")
    else:
        print("Aucune nation renseignée.")

    print()
    print("Répartition par sexe")
    print("--------------------")

    if statistics.gender_counts:
        for gender, count in statistics.gender_counts.items():
            print(f"{gender:<12}: {count}")
    else:
        print("Aucun sexe renseigné.")

    print()
    print("Répartition par tour")
    print("--------------------")

    for tour, count in statistics.tour_counts.items():
        print(f"{tour:<15}: {count}")


if __name__ == "__main__":
    main()