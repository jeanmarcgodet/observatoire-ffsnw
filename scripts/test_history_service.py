from observatoire.services import HistoryService


def main() -> None:
    service = HistoryService()

    rider = service.get_rider("FRA692015508")

    print("Rider")
    print("-----")

    if rider is None:
        print("Rider introuvable.")
    else:
        print(f"ID interne : {rider.id}")
        print(f"ID IWWF    : {rider.iwwf_id}")
        print(f"Nom        : {rider.nom_complet}")

    print()
    print("Compétition")
    print("-----------")

    competition = service.get_competition("26FRA021")

    if competition is None:
        print("Compétition introuvable.")
    else:
        print(f"ID interne : {competition.id}")
        print(f"ID IWWF    : {competition.iwwf_id}")
        print(f"Nom        : {competition.nom}")
        print(f"Lieu       : {competition.lieu}")
        print(f"Dates      : {competition.periode}")

    print()
    print("Recherche de riders")
    print("--------------------")

    for result in service.search_riders("Anguenot"):
        print(f"{result.id:>3} | {result.iwwf_id} | {result.nom_complet}")


if __name__ == "__main__":
    main()
