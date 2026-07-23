"""Génère le rapport principal illustré de la filière U21 -> Open.

Entrée
------
data/processed/indicateurs_consolides_filiere_open_2017_2026.csv

Sorties
-------
reports/rapport_filiere_open_2017_2026_v2.md
reports/figures/filiere_open_v2/01_effectifs_open_championnat.png
reports/figures/filiere_open_v2/02_conversion_u21_open.png
reports/figures/filiere_open_v2/03_persistance_open.png
reports/figures/filiere_open_v2/04_origine_u21_persistance.png
reports/figures/filiere_open_v2/05_calendrier_profondeur_fragmentation.png
reports/figures/filiere_open_v2/06_captation_championnat_open.png

Le script ne modifie aucun fichier existant en dehors de la version v2
et de son dossier de figures.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def integer(value: object) -> int | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def number(value: object) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def format_fr(value: object, decimals: int = 1) -> str:
    if value is None or value == "":
        return "n.d."

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if math.isclose(value, round(value)):
            return str(int(round(value)))
        return f"{value:.{decimals}f}".replace(".", ",")

    return str(value).replace(".", ",")


def indicator_lookup(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["IndicatorCode"], row["Period"]): row
        for row in rows
    }


def require(
    lookup: dict[tuple[str, str], dict[str, str]],
    code: str,
    period: str,
) -> dict[str, str]:
    key = (code, period)
    if key not in lookup:
        raise KeyError(f"Indicateur absent : {code} / {period}")
    return lookup[key]


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def label_bars(ax, bars, suffix: str = "") -> None:
    labels = []
    for bar in bars:
        height = bar.get_height()
        labels.append(f"{format_fr(float(height))}{suffix}")
    ax.bar_label(bars, labels=labels, padding=3, fontsize=9)


def figure_open_volume(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    years = list(range(2017, 2027))
    values = [
        number(require(lookup, "OPEN_CHAMP_TOTAL", str(year))["Value"]) or 0
        for year in years
    ]

    plt.figure(figsize=(9.5, 5.2))
    plt.plot(years, values, marker="o", linewidth=2)
    for year, value in zip(years, values):
        plt.annotate(
            format_fr(value),
            (year, value),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9,
        )
    plt.title("Présences Open au Championnat, 2017-2026")
    plt.xlabel("Année")
    plt.ylabel("Nombre de participants")
    plt.xticks(years)
    plt.grid(axis="y", alpha=0.25)
    save_figure(output)


def figure_u21_conversion(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    horizons = [1, 2, 3]
    rows = [
        require(lookup, f"U21_OPEN_H{h}", f"horizon_{h}_an")
        for h in horizons
    ]
    rates = [number(row["Value"]) or 0 for row in rows]
    labels = [
        f"{row['Numerator']}/{row['Denominator']}\n"
        f"{format_fr(number(row['Value']))} %"
        for row in rows
    ]

    plt.figure(figsize=(8.4, 5.2))
    ax = plt.gca()
    bars = ax.bar(
        [f"Sous {h} an" if h == 1 else f"Sous {h} ans" for h in horizons],
        rates,
    )
    ax.bar_label(bars, labels=labels, padding=4, fontsize=10)
    ax.set_ylim(0, max(rates) + 12)
    ax.set_title("Sorties U21 retrouvées en Open")
    ax.set_ylabel("Part des sorties U21 observées (%)")
    ax.grid(axis="y", alpha=0.25)
    save_figure(output)


def figure_open_persistence(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    horizons = [1, 2, 3]
    reappearance = [
        number(
            require(
                lookup,
                f"OPEN_REAPPARITION_H{h}",
                f"horizon_{h}_an",
            )["Value"]
        )
        or 0
        for h in horizons
    ]
    continuity = [
        number(
            require(
                lookup,
                f"OPEN_CONTINUITE_H{h}",
                f"horizon_{h}_an",
            )["Value"]
        )
        or 0
        for h in horizons
    ]

    x = list(range(len(horizons)))
    width = 0.36

    plt.figure(figsize=(9, 5.4))
    ax = plt.gca()
    bars_a = ax.bar(
        [position - width / 2 for position in x],
        reappearance,
        width,
        label="Réapparition au moins une fois",
    )
    bars_b = ax.bar(
        [position + width / 2 for position in x],
        continuity,
        width,
        label="Présence chaque année",
    )
    label_bars(ax, bars_a, " %")
    label_bars(ax, bars_b, " %")
    ax.set_xticks(x, [f"{h} an" if h == 1 else f"{h} ans" for h in horizons])
    ax.set_ylabel("Part des premières apparitions Open (%)")
    ax.set_title("Réapparition et continuité après l’entrée en Open")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(reappearance) + 14)
    save_figure(output)


def figure_u21_origin(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    groups = [
        ("U21 récent", "OPEN_ORIGINE_U21_RECENTE"),
        ("Aucun U21 récent observé", "OPEN_SANS_U21_RECENTE"),
    ]
    reappearance = [
        number(
            require(
                lookup,
                f"{code}_REAPPARITION_H3",
                "cohortes_open_2020_2023",
            )["Value"]
        )
        or 0
        for _, code in groups
    ]
    continuity = [
        number(
            require(
                lookup,
                f"{code}_CONTINUITE_H3",
                "cohortes_open_2020_2023",
            )["Value"]
        )
        or 0
        for _, code in groups
    ]

    x = list(range(len(groups)))
    width = 0.36

    plt.figure(figsize=(9.2, 5.4))
    ax = plt.gca()
    bars_a = ax.bar(
        [position - width / 2 for position in x],
        reappearance,
        width,
        label="Réapparition sous trois ans",
    )
    bars_b = ax.bar(
        [position + width / 2 for position in x],
        continuity,
        width,
        label="Présence annuelle continue",
    )
    label_bars(ax, bars_a, " %")
    label_bars(ax, bars_b, " %")
    ax.set_xticks(x, [label for label, _ in groups])
    ax.set_ylabel("Part des premières apparitions Open (%)")
    ax.set_title("Persistance Open selon l’origine U21 observable")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(reappearance) + 15)
    save_figure(output)


def figure_calendar(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    years = [2023, 2024, 2025]
    shallow = [
        number(require(lookup, "CAL_OPEN_CHAMPS_1_4", str(year))["Value"])
        or 0
        for year in years
    ]
    zero_overlap = [
        number(require(lookup, "CAL_ZERO_OVERLAP", str(year))["Value"])
        or 0
        for year in years
    ]

    x = list(range(len(years)))
    width = 0.36

    plt.figure(figsize=(9.3, 5.4))
    ax = plt.gca()
    bars_a = ax.bar(
        [position - width / 2 for position in x],
        shallow,
        width,
        label="Compétitions avec 1 à 4 Open",
    )
    bars_b = ax.bar(
        [position + width / 2 for position in x],
        zero_overlap,
        width,
        label="Paires sans participant commun",
    )
    label_bars(ax, bars_a, " %")
    label_bars(ax, bars_b, " %")
    ax.set_xticks(x, [str(year) for year in years])
    ax.set_ylabel("Part (%)")
    ax.set_title("Faible profondeur et fragmentation du calendrier Open")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, max(zero_overlap) + 14)
    save_figure(output)


def figure_capture(
    lookup: dict[tuple[str, str], dict[str, str]],
    output: Path,
) -> None:
    years = [2023, 2024, 2025]
    rows = [
        require(lookup, "CHAMP_OPEN_CAPTURE_FR", str(year))
        for year in years
    ]
    rates = [number(row["Value"]) or 0 for row in rows]
    labels = [
        f"{row['Numerator']}/{row['Denominator']}\n"
        f"{format_fr(number(row['Value']))} %"
        for row in rows
    ]

    plt.figure(figsize=(8.6, 5.3))
    ax = plt.gca()
    bars = ax.bar([str(year) for year in years], rates)
    ax.bar_label(bars, labels=labels, padding=4, fontsize=10)
    ax.set_ylim(0, max(rates) + 14)
    ax.set_title("Captation du vivier français par le Championnat Open")
    ax.set_ylabel("Part des Open français EMS (%)")
    ax.grid(axis="y", alpha=0.25)
    save_figure(output)


def build_report(
    lookup: dict[tuple[str, str], dict[str, str]],
    report_path: Path,
    figures_dir: Path,
) -> None:
    open_2017 = require(lookup, "OPEN_CHAMP_TOTAL", "2017")
    open_2026 = require(lookup, "OPEN_CHAMP_TOTAL", "2026")
    evolution = require(
        lookup,
        "OPEN_CHAMP_EVOLUTION",
        "2017-2026",
    )

    u21_h3 = require(lookup, "U21_OPEN_H3", "horizon_3_an")
    reapp_h3 = require(
        lookup,
        "OPEN_REAPPARITION_H3",
        "horizon_3_an",
    )
    cont_h3 = require(
        lookup,
        "OPEN_CONTINUITE_H3",
        "horizon_3_an",
    )

    u21_recent = require(
        lookup,
        "OPEN_ORIGINE_U21_RECENTE_REAPPARITION_H3",
        "cohortes_open_2020_2023",
    )
    no_u21_recent = require(
        lookup,
        "OPEN_SANS_U21_RECENTE_REAPPARITION_H3",
        "cohortes_open_2020_2023",
    )

    capture = {
        year: require(
            lookup,
            "CHAMP_OPEN_CAPTURE_FR",
            str(year),
        )
        for year in (2023, 2024, 2025)
    }

    senior = require(
        lookup,
        "OPEN_SENIOR_EVENTUEL",
        "jusqu_a_2026",
    )
    overlap = require(
        lookup,
        "OPEN_SENIOR_CHEVAUCHEMENT",
        "2017-2026",
    )

    relative_figures = figures_dir.relative_to(report_path.parent)

    lines: list[str] = []
    lines.append(
        "# Filière compétitive U21 → Open : diagnostic principal 2017-2026"
    )
    lines.append("")
    lines.append(
        "> Rapport principal illustré — la catégorie Open constitue l’objet "
        "central. Les Seniors sont traités comme une population d’aval."
    )
    lines.append("")
    lines.append("## Résumé exécutif")
    lines.append("")
    lines.append(
        f"Les présences Open enregistrées au Championnat passent de "
        f"**{open_2017['Value']} en 2017 à {open_2026['Value']} en 2026**, "
        f"soit **{format_fr(number(evolution['Value']))} %**. "
        "Cette série historique porte sur les participants présents dans les "
        "codes Open, toutes nationalités confondues."
    )
    lines.append("")
    lines.append(
        f"Parmi les sorties U21 disposant de trois années de recul, "
        f"**{u21_h3['Numerator']} sur {u21_h3['Denominator']}**, soit "
        f"**{format_fr(number(u21_h3['Value']))} %**, sont retrouvées en Open. "
        f"Après une première apparition Open, **{reapp_h3['Numerator']} sur "
        f"{reapp_h3['Denominator']}** réapparaissent sous trois ans, mais "
        f"seulement **{cont_h3['Numerator']} sur {cont_h3['Denominator']}** "
        "restent présents chaque année sans interruption."
    )
    lines.append("")
    lines.append(
        "Le calendrier EMS offre de nombreuses occasions de compétition, mais "
        "les répartit sur un vivier restreint et dans des champs généralement "
        "faibles. La captation du Championnat Open chute à **28,6 % en 2025**, "
        "malgré l’augmentation du nombre d’Open actifs."
    )
    lines.append("")
    lines.append(
        "**Diagnostic central.** La filière ne manque pas principalement "
        "d’épreuves. Elle manque de profondeur, de conversion vers Open et de "
        "continuité annuelle après l’entrée dans la catégorie reine."
    )
    lines.append("")

    lines.append("## 1. Périmètres et définitions")
    lines.append("")
    lines.append(
        "Trois objets sont distingués : les présences historiques dans les "
        "codes des Championnats, les inscriptions françaises approuvées dans "
        "l’EMS et les classements sportifs effectifs. Ils ne sont pas "
        "interchangeables."
    )
    lines.append("")
    lines.append(
        "La trajectoire étudiée est : **Relève/U17 → U21 → Open → Senior**. "
        "U21 constitue l’alimentation immédiate, Open la catégorie centrale, "
        "et Senior une population d’aval renseignant la continuité de pratique."
    )
    lines.append("")

    lines.append("## 2. Contraction de la catégorie Open")
    lines.append("")
    lines.append(
        f"![Présences Open au Championnat]("
        f"{relative_figures.as_posix()}/01_effectifs_open_championnat.png)"
    )
    lines.append("")
    lines.append(
        "*Source : registre longitudinal des Championnats, codes nationaux "
        "explicitement validés.*"
    )
    lines.append("")
    lines.append(
        f"Le volume passe de **{open_2017['Value']} à {open_2026['Value']}**, "
        f"soit **{format_fr(number(evolution['Value']))} %**. Le rebond de "
        "2022 ne modifie pas la tendance de contraction observée à partir de "
        "2023."
    )
    lines.append("")

    lines.append("## 3. Une alimentation U21 → Open partielle")
    lines.append("")
    lines.append(
        f"![Conversion U21 vers Open]("
        f"{relative_figures.as_posix()}/02_conversion_u21_open.png)"
    )
    lines.append("")
    lines.append(
        "*Lecture : le dénominateur diminue avec l’horizon, car seules les "
        "cohortes disposant d’un recul suffisant sont conservées.*"
    )
    lines.append("")
    lines.append(
        f"À trois ans, **{u21_h3['Numerator']} sur "
        f"{u21_h3['Denominator']}** sont retrouvés en Open ; "
        f"**{integer(u21_h3['Denominator']) - integer(u21_h3['Numerator'])}** "
        "ne le sont pas dans la fenêtre observable. Le passage existe, mais "
        "il n’est ni immédiat ni majoritaire."
    )
    lines.append("")

    lines.append("## 4. Une présence Open surtout intermittente")
    lines.append("")
    lines.append(
        f"![Persistance Open]("
        f"{relative_figures.as_posix()}/03_persistance_open.png)"
    )
    lines.append("")
    lines.append(
        "*Réapparition : présence au moins une fois dans la fenêtre. "
        "Continuité : présence chaque année sans interruption.*"
    )
    lines.append("")
    lines.append(
        f"Sous trois ans, **{format_fr(number(reapp_h3['Value']))} %** des "
        "premières apparitions Open réapparaissent au moins une fois, mais "
        f"seulement **{format_fr(number(cont_h3['Value']))} %** demeurent "
        "présentes chaque année. La catégorie fonctionne davantage par "
        "interruptions et retours que par intégration annuelle durable."
    )
    lines.append("")

    lines.append("## 5. Le passage par U21 favorise le retour, pas la continuité")
    lines.append("")
    lines.append(
        f"![Origine U21 et persistance Open]("
        f"{relative_figures.as_posix()}/04_origine_u21_persistance.png)"
    )
    lines.append("")
    lines.append(
        "*Fenêtre complète : premières apparitions Open 2020-2023, avec trois "
        "années d’historique avant et trois années de recul après.*"
    )
    lines.append("")
    lines.append(
        f"Parmi les Open issus récemment d’U21, "
        f"**{u21_recent['Numerator']} sur {u21_recent['Denominator']}** "
        f"réapparaissent sous trois ans, contre "
        f"**{no_u21_recent['Numerator']} sur "
        f"{no_u21_recent['Denominator']}** lorsqu’aucun U21 récent n’est "
        "observé. L’effectif U21 récent n’est cependant que de six sportifs ; "
        "le résultat reste descriptif."
    )
    lines.append("")

    lines.append("## 6. Un calendrier abondant, mais peu profond")
    lines.append("")
    lines.append(
        f"![Profondeur et fragmentation du calendrier]("
        f"{relative_figures.as_posix()}/"
        "05_calendrier_profondeur_fragmentation.png)"
    )
    lines.append("")
    lines.append(
        "*Source : inscriptions françaises approuvées EMS, 2023-2025.*"
    )
    lines.append("")
    lines.append(
        "Chaque saison compte 24 à 25 compétitions accueillant des Open "
        "français. Entre **52 % et 60 %** de ces épreuves réunissent au plus "
        "quatre Open, et entre **58 % et 67 %** des paires de compétitions ne "
        "partagent aucun participant."
    )
    lines.append("")
    lines.append(
        "Le calendrier n’est toutefois pas composé de circuits totalement "
        "étanches : une grande composante relie l’essentiel des épreuves par "
        "un petit noyau de sportifs multi-épreuves. Il s’agit d’un réseau "
        "faiblement connecté plutôt que d’une segmentation complète."
    )
    lines.append("")

    lines.append("## 7. Une captation nationale qui chute en 2025")
    lines.append("")
    lines.append(
        f"![Captation du Championnat Open]("
        f"{relative_figures.as_posix()}/06_captation_championnat_open.png)"
    )
    lines.append("")
    lines.append(
        "*Numérateur : Open français inscrits au code précis du Championnat. "
        "Dénominateur : Open français actifs dans le calendrier EMS.*"
    )
    lines.append("")
    lines.append(
        f"La captation est de **{format_fr(number(capture[2023]['Value']))} % "
        f"en 2023**, **{format_fr(number(capture[2024]['Value']))} % en 2024** "
        f"et **{format_fr(number(capture[2025]['Value']))} % en 2025**. "
        "L’élargissement du vivier EMS en 2025 ne renforce donc pas l’épreuve "
        "nationale centrale."
    )
    lines.append("")

    lines.append("## 8. Senior : continuité aval, non indicateur central")
    lines.append("")
    lines.append(
        f"Parmi les anciens Open disposant d’au moins une saison observable, "
        f"**{senior['Numerator']} sur {senior['Denominator']}**, soit "
        f"**{format_fr(number(senior['Value']))} %**, sont retrouvés "
        "ultérieurement en Senior. "
        f"**{overlap['Value']} sportifs** participent simultanément en Open et "
        "Senior une même saison."
    )
    lines.append("")
    lines.append(
        "Les catégories Seniors renseignent la continuité, la reprise ou la "
        "double pratique. Elles ne démontrent ni le renouvellement du vivier "
        "Open ni la capacité d’accès au haut niveau."
    )
    lines.append("")

    lines.append("<!-- PAGEBREAK -->")
    lines.append("")
    lines.append("## 9. Conclusion générale")
    lines.append("")
    lines.append(
        "La filière compétitive nationale ne transforme qu’une partie des "
        "sorties U21 en présence Open et transforme rarement une première "
        "apparition Open en participation annuelle continue. Le calendrier "
        "offre de nombreuses occasions de performance homologuée, mais les "
        "répartit sur un vivier restreint et dans des champs souvent faibles."
    )
    lines.append("")
    lines.append(
        "Les données sont donc davantage compatibles avec un **circuit "
        "intensif de performances pour une population déjà intégrée** qu’avec "
        "une filière démontrant sa capacité à élargir, convertir et stabiliser "
        "durablement la base Open."
    )
    lines.append("")

    lines.append("## Limites")
    lines.append("")
    lines.append(
        "- Les données EMS décrivent des inscriptions approuvées, pas "
        "nécessairement des départs ou des classements."
    )
    lines.append(
        "- Les séries historiques des Championnats et les séries EMS n’ont pas "
        "toujours le même périmètre de nationalité ou de statut."
    )
    lines.append(
        "- Une absence au Championnat de France ne signifie pas un arrêt de "
        "toute pratique compétitive."
    )
    lines.append(
        "- Les associations entre fréquence, origine U21 et rétention ne "
        "démontrent pas de causalité."
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    root = repo_root()
    source = (
        root
        / "data/processed/indicateurs_consolides_filiere_open_2017_2026.csv"
    )
    report = root / "reports/rapport_filiere_open_2017_2026_v2.md"
    figures = root / "reports/figures/filiere_open_v2"

    rows = read_csv(source)
    lookup = indicator_lookup(rows)

    figure_open_volume(
        lookup,
        figures / "01_effectifs_open_championnat.png",
    )
    figure_u21_conversion(
        lookup,
        figures / "02_conversion_u21_open.png",
    )
    figure_open_persistence(
        lookup,
        figures / "03_persistance_open.png",
    )
    figure_u21_origin(
        lookup,
        figures / "04_origine_u21_persistance.png",
    )
    figure_calendar(
        lookup,
        figures / "05_calendrier_profondeur_fragmentation.png",
    )
    figure_capture(
        lookup,
        figures / "06_captation_championnat_open.png",
    )
    build_report(lookup, report, figures)

    print("=" * 88)
    print("RAPPORT PRINCIPAL ILLUSTRÉ GÉNÉRÉ")
    print("=" * 88)
    print(f"Rapport : {report}")
    print(f"Figures : {figures}")
    print("Nombre de figures : 6")
    print("Aucun fichier v1 n'a été modifié.")


if __name__ == "__main__":
    main()
