from observatoire.repositories.base import BaseRepository


def main() -> None:
    repository = BaseRepository()

    row = repository.fetch_one(
        """
        SELECT
            COUNT(*) AS rider_count
        FROM riders
        """
    )

    if row is None:
        raise RuntimeError("La requête n'a retourné aucune ligne.")

    print(f"Riders présents dans la base : {row['rider_count']}")

    competition = repository.fetch_one(
        """
        SELECT
            iwwf_id,
            nom,
            ville,
            date_debut,
            date_fin
        FROM competitions
        WHERE iwwf_id = ?
        """,
        ("26FRA021",),
    )

    if competition is None:
        print("Compétition 26FRA021 introuvable.")
        return

    print()
    print(f"Compétition : {competition['nom']}")
    print(f"Code IWWF   : {competition['iwwf_id']}")
    print(f"Lieu        : {competition['ville']}")
    print(
        "Dates       : "
        f"{competition['date_debut']} → {competition['date_fin']}"
    )


if __name__ == "__main__":
    main()