"""Génère les figures du module fidélisation EMS 2023-2025."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTPUT = ROOT / "reports" / "figures" / "fidelisation"
OUTPUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def as_float(value: str) -> float:
    return float(str(value).replace(",", "."))


def save_current(filename: str) -> None:
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=220, bbox_inches="tight")
    plt.close()


def figure_retention_intensity() -> None:
    rows = [
        row
        for row in read_csv(DATA / "ems_retention_selon_intensite_2023_2025.csv")
        if row["Population"] == "ALL"
    ]

    order = [
        "1_COMPETITION",
        "2_COMPETITIONS",
        "3_4_COMPETITIONS",
        "5_PLUS_COMPETITIONS",
    ]
    labels = ["1", "2", "3–4", "5 ou plus"]

    transitions = [
        ("2023", "2024"),
        ("2024", "2025"),
    ]

    x = list(range(len(order)))
    width = 0.36

    plt.figure(figsize=(9, 5.5))

    for index, (from_year, to_year) in enumerate(transitions):
        lookup = {
            row["IntensityBand"]: as_float(row["RetentionRatePercent"])
            for row in rows
            if row["FromYear"] == from_year and row["ToYear"] == to_year
        }

        positions = [
            value + (index - 0.5) * width
            for value in x
        ]

        values = [lookup[item] for item in order]

        bars = plt.bar(
            positions,
            values,
            width=width,
            label=f"{from_year}→{to_year}",
        )

        for bar, value in zip(bars, values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                value + 1.3,
                f"{value:.1f} %",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.xticks(x, labels)
    plt.ylim(0, 105)
    plt.xlabel("Nombre de compétitions pendant la saison initiale")
    plt.ylabel("Taux de rétention l’année suivante (%)")
    plt.title("La fidélisation augmente fortement avec la fréquence de compétition")
    plt.legend()

    save_current("01_retention_selon_intensite.png")


def figure_profile_weight() -> None:
    rows = read_csv(DATA / "ems_poids_profils_fidelisation_2023_2025.csv")

    labels_map = {
        "CORE_3_YEARS": "Présents 3 saisons",
        "TWO_YEARS_2023_2024": "2023–2024",
        "TWO_YEARS_2024_2025": "2024–2025",
        "RETURN_AFTER_GAP": "Retour après interruption",
        "ONE_SEASON_2023": "2023 seulement",
        "ONE_SEASON_2024": "2024 seulement",
        "ONE_SEASON_2025": "2025 seulement",
    }

    labels = [
        labels_map.get(row["FidelityProfile"], row["FidelityProfile"])
        for row in rows
    ]
    athlete_share = [as_float(row["AthleteSharePercent"]) for row in rows]
    activity_share = [as_float(row["CompetitionSharePercent"]) for row in rows]

    x = list(range(len(rows)))
    width = 0.36

    plt.figure(figsize=(11, 6))
    plt.bar(
        [value - width / 2 for value in x],
        athlete_share,
        width=width,
        label="Part du vivier",
    )
    plt.bar(
        [value + width / 2 for value in x],
        activity_share,
        width=width,
        label="Part de l’activité",
    )

    plt.xticks(x, labels, rotation=25, ha="right")
    plt.ylabel("Part (%)")
    plt.title("Le noyau présent trois saisons concentre l’activité")
    plt.legend()

    save_current("02_poids_profils_fidelisation.png")


def figure_lorenz() -> None:
    rows = read_csv(DATA / "ems_courbe_lorenz_activite_2023_2025.csv")

    population = [as_float(row["AthletePopulationPercent"]) for row in rows]
    activity = [as_float(row["CumulativeActivityPercent"]) for row in rows]

    plt.figure(figsize=(7, 7))
    plt.plot(population, activity, linewidth=2, label="Activité observée")
    plt.plot([0, 100], [0, 100], linestyle="--", label="Égalité parfaite")
    plt.xlabel("Part cumulée des sportifs, des moins aux plus actifs (%)")
    plt.ylabel("Part cumulée de l’activité (%)")
    plt.title("Concentration de l’activité compétitive — Gini 0,498")
    plt.legend()

    save_current("03_courbe_lorenz_activite.png")


def figure_cohort_age() -> None:
    rows = [
        row
        for row in read_csv(DATA / "ems_cohorte_2023_sexe_age.csv")
        if row["Dimension"] == "AGE_BAND"
    ]

    order = ["RELEVES", "JUNIOR", "U21", "OPEN", "SENIOR"]
    labels = ["Relevés", "Junior", "U21", "Open", "Senior"]
    lookup = {
        row["Group"]: as_float(row["PresentAllThreeYearsPercent"])
        for row in rows
    }
    values = [lookup[item] for item in order]

    plt.figure(figsize=(8.5, 5.5))
    bars = plt.bar(labels, values)

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.2,
            f"{value:.1f} %",
            ha="center",
            va="bottom",
        )

    plt.ylim(0, 70)
    plt.ylabel("Présents pendant les trois saisons (%)")
    plt.title("La population Open présente la fidélisation la plus faible")

    save_current("04_fidelisation_cohorte_2023_par_age.png")


def main() -> None:
    figure_retention_intensity()
    figure_profile_weight()
    figure_lorenz()
    figure_cohort_age()

    print("Figures créées dans :", OUTPUT)

    for path in sorted(OUTPUT.glob("*.png")):
        print("-", path)


if __name__ == "__main__":
    main()
