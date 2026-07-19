from observatoire.services import HistoryService


def format_number(value: float | None) -> str:
    if value is None:
        return "Non disponible"

    if value.is_integer():
        return str(int(value))

    return str(value).replace(".", ",")


def main() -> None:
    service = HistoryService()

    career = service.get_rider_career("FRA692015508")

    if career is None:
        print("Rider introuvable.")
        return

    statistics = career.statistics

    print(career.rider.nom_complet)
    print("=" * len(career.rider.nom_complet))
    print()
    print(f"Compétitions : {statistics.number_of_competitions}")
    print(f"Résultats    : {statistics.number_of_results}")
    print(f"Finales      : {statistics.number_of_finals}")
    print(f"Disciplines  : {', '.join(statistics.disciplines)}")
    print(
        "Saisons      : "
        + ", ".join(str(season) for season in statistics.seasons)
    )

    print()
    print("Meilleures performances")
    print("------------------------")
    print(
        "Slalom  : "
        + (statistics.best_slalom_text() or "Non disponible")
    )
    print(
        "Tricks  : "
        + format_number(statistics.best_tricks())
    )
    print(
        "Jump    : "
        + format_number(statistics.best_jump())
        + (
            " m"
            if statistics.best_jump() is not None
            else ""
        )
    )
    print(
        "Overall : "
        + format_number(statistics.best_overall_component())
    )

    print()
    print("Présence en finale")
    print("-------------------")

    for discipline in ("slalom", "tricks", "jump"):
        status = "oui" if statistics.has_final(discipline) else "non"
        print(f"{discipline.capitalize():<8}: {status}")

    print()
    print("Répartition par tour")
    print("--------------------")

    for tour, count in statistics.tour_counts.items():
        print(f"{tour:<15}: {count}")


if __name__ == "__main__":
    main()

