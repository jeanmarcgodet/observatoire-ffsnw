"""Genere les graphiques de participation 2017-2026."""

from __future__ import annotations

import csv
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "Matplotlib absent. Installer avec: "
        "python -m pip install matplotlib"
    ) from exc


INPUT_FILE = Path(
    "data/exports/participation_annuelle_2017_2026.csv"
)

OUTPUT_DIRECTORY = Path("reports/figures")

POPULATIONS = (
    "Jeunes/U21",
    "Open",
    "Seniors",
)


def load_rows():
    with INPUT_FILE.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        return list(
            csv.DictReader(
                handle,
                delimiter=";",
            )
        )


def rows_for(rows, population):
    return sorted(
        (
            row
            for row in rows
            if row["population"] == population
        ),
        key=lambda row: int(row["annee"]),
    )


def save_figure(filename):
    path = OUTPUT_DIRECTORY / filename

    plt.tight_layout()
    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    print(" -", path)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = load_rows()
    total_rows = rows_for(rows, "Tous")

    years = [
        int(row["annee"])
        for row in total_rows
    ]

    participants = [
        int(row["participants"])
        for row in total_rows
    ]

    women = [
        int(row["femmes"])
        for row in total_rows
    ]

    men = [
        int(row["hommes"])
        for row in total_rows
    ]

    fidelity = [
        float(row["taux_fidelisation_pct"])
        if row["taux_fidelisation_pct"]
        else 0
        for row in total_rows
    ]

    print("=" * 72)
    print("GENERATION DES GRAPHIQUES")
    print("=" * 72)

    plt.figure(figsize=(10, 6))
    plt.plot(
        years,
        participants,
        marker="o",
    )
    plt.title(
        "Participation aux championnats de France "
        "de ski nautique"
    )
    plt.xlabel("Annee")
    plt.ylabel("Participants uniques")
    plt.xticks(years)
    plt.grid(axis="y", alpha=0.3)

    for year, value in zip(
        years,
        participants,
    ):
        plt.annotate(
            str(value),
            (year, value),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
        )

    save_figure(
        "participation_totale_2017_2026.png"
    )

    plt.figure(figsize=(10, 6))

    for population in POPULATIONS:
        population_rows = rows_for(
            rows,
            population,
        )

        plt.plot(
            [
                int(row["annee"])
                for row in population_rows
            ],
            [
                int(row["participants"])
                for row in population_rows
            ],
            marker="o",
            label=population,
        )

    plt.title(
        "Participation par population sportive"
    )
    plt.xlabel("Annee")
    plt.ylabel("Participants uniques")
    plt.xticks(years)
    plt.grid(axis="y", alpha=0.3)
    plt.legend()

    save_figure(
        "participation_par_population_2017_2026.png"
    )

    plt.figure(figsize=(10, 6))
    plt.plot(
        years,
        women,
        marker="o",
        label="Femmes",
    )
    plt.plot(
        years,
        men,
        marker="o",
        label="Hommes",
    )
    plt.title(
        "Evolution de la participation par sexe"
    )
    plt.xlabel("Annee")
    plt.ylabel("Participants uniques")
    plt.xticks(years)
    plt.grid(axis="y", alpha=0.3)
    plt.legend()

    save_figure(
        "participation_par_sexe_2017_2026.png"
    )

    plt.figure(figsize=(10, 6))
    plt.bar(
        years[1:],
        fidelity[1:],
    )
    plt.title(
        "Taux annuel de fidelisation"
    )
    plt.xlabel("Annee")
    plt.ylabel(
        "Participants de l'annee precedente "
        "revenus (%)"
    )
    plt.xticks(years[1:])
    plt.ylim(0, 100)
    plt.grid(axis="y", alpha=0.3)

    for year, value in zip(
        years[1:],
        fidelity[1:],
    ):
        plt.annotate(
            f"{value:.1f} %",
            (year, value),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
        )

    save_figure(
        "taux_fidelisation_2018_2026.png"
    )

    print()
    print("Graphiques generes :", 4)


if __name__ == "__main__":
    main()
