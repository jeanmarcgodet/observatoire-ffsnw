"""Rapport longitudinal comparatif 2017-2026 - version 2."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


GLOBAL_FILE = Path(
    "data/exports/diagnostic_annuel_champs_2017_2026.csv"
)

AXES_FILE = Path(
    "data/exports/diagnostic_annuel_par_axes_2017_2026.csv"
)

REPORT_FILE = Path(
    "reports/rapport_longitudinal_participation_2017_2026_v2.md"
)

DEPTH_FIGURE = Path(
    "reports/figures/"
    "longitudinal_moyenne_mediane_champs_2017_2026.png"
)

YEARS = list(range(2017, 2027))

POPULATIONS = [
    ("RELEVE", "Relève"),
    ("U21_OPEN", "U21 / Open"),
    ("SENIORS", "Seniors"),
]

SEXES = [
    ("FEMMES", "Femmes"),
    ("HOMMES", "Hommes"),
]

EVENTS = [
    ("SLALOM", "Slalom"),
    ("FIGURES", "Figures"),
    ("SAUT", "Saut"),
    ("COMBINE", "Combiné"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        return list(
            csv.DictReader(
                handle,
                delimiter=";",
            )
        )


def as_int(row: dict[str, str], field: str) -> int:
    return int(row[field])


def as_float(
    row: dict[str, str],
    field: str,
) -> float:
    return float(
        str(row[field]).replace(
            ",",
            ".",
        )
    )


def fr(value: float) -> str:
    return f"{value:.1f}".replace(
        ".",
        ",",
    )


def fr_pct(value: float) -> str:
    return fr(value) + " %"


def evolution(
    start_value: int,
    end_value: int,
) -> tuple[int, float]:
    difference = end_value - start_value

    rate = (
        100 * difference / start_value
        if start_value
        else 0.0
    )

    return difference, rate


def signed_integer(value: int) -> str:
    if value > 0:
        return f"+{value}"

    return str(value)


def signed_percentage(value: float) -> str:
    prefix = "+" if value > 0 else ""

    return prefix + fr(value) + " %"


global_rows = read_csv(GLOBAL_FILE)
axis_rows = read_csv(AXES_FILE)

global_lookup = {
    int(row["annee"]): row
    for row in global_rows
}

axis_lookup = {
    (
        int(row["annee"]),
        row["axe"],
        row["groupe"],
    ): row
    for row in axis_rows
}


for year in YEARS:
    if year not in global_lookup:
        raise RuntimeError(
            f"Diagnostic global absent pour {year}."
        )

    if as_int(
        global_lookup[year],
        "champs_possibles",
    ) != 104:
        raise RuntimeError(
            f"Grille annuelle incorrecte en {year}."
        )


def axis_row(
    year: int,
    axis: str,
    group: str,
) -> dict[str, str]:
    key = (
        year,
        axis,
        group,
    )

    if key not in axis_lookup:
        raise RuntimeError(
            f"Diagnostic absent : {key}"
        )

    return axis_lookup[key]


participants = [
    as_int(
        global_lookup[year],
        "participants_distincts",
    )
    for year in YEARS
]

field_participations = [
    as_int(
        global_lookup[year],
        "participations_dans_les_champs",
    )
    for year in YEARS
]

effective_fields = [
    as_int(
        global_lookup[year],
        "champs_effectifs",
    )
    for year in YEARS
]

mean_effective = [
    as_float(
        global_lookup[year],
        "moyenne_par_champ_effectif",
    )
    for year in YEARS
]

median_effective = [
    as_float(
        global_lookup[year],
        "mediane_par_champ_effectif",
    )
    for year in YEARS
]

small_field_rates = [
    as_float(
        global_lookup[year],
        "part_champs_1_a_3_parmi_effectifs_pct",
    )
    for year in YEARS
]

podium_rates = [
    as_float(
        global_lookup[year],
        "part_des_participations_couverte_pct",
    )
    for year in YEARS
]



def plot_series(
    series: dict[str, list[float]],
    title: str,
    ylabel: str,
    output_path: Path,
    ylim: tuple[float, float] | None = None,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(
        figsize=(10.5, 6)
    )

    for label, values in series.items():
        plt.plot(
            YEARS,
            values,
            marker="o",
            label=label,
        )

    plt.title(title)
    plt.xlabel("Ann?e")
    plt.ylabel(ylabel)
    plt.xticks(YEARS)
    plt.grid(alpha=0.3)

    if len(series) > 1:
        plt.legend()

    if ylim is not None:
        plt.ylim(*ylim)

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


FIGURE_DIR = Path("reports/figures")

plot_series(
    {
        "Participants distincts": participants,
    },
    "Participants distincts par Championnat de France",
    "Participants distincts",
    FIGURE_DIR
    / "longitudinal_participants_distincts_2017_2026.png",
)

plot_series(
    {
        "Participations dans les champs": field_participations,
    },
    "Participations class?es dans les champs",
    "Participations dans les champs",
    FIGURE_DIR
    / "longitudinal_participations_champs_2017_2026.png",
)

occupation_rates = [
    as_float(
        global_lookup[year],
        "taux_occupation_pct",
    )
    for year in YEARS
]

plot_series(
    {
        "Champs occup?s": occupation_rates,
        "Champs de 1 ? 3 parmi les champs occup?s": small_field_rates,
    },
    "Occupation et faible profondeur des champs",
    "Part des champs (%)",
    FIGURE_DIR
    / "longitudinal_structure_champs_2017_2026.png",
    ylim=(0, 100),
)

plot_series(
    {
        "Part couverte par les podiums": podium_rates,
    },
    "Poids num?rique des podiums",
    "Part des participations couverte (%)",
    FIGURE_DIR
    / "longitudinal_poids_podiums_2017_2026.png",
    ylim=(0, 100),
)

population_series = {
    label: [
        as_int(
            axis_row(
                year,
                "POPULATION",
                code,
            ),
            "participations_dans_les_champs",
        )
        for year in YEARS
    ]
    for code, label in POPULATIONS
}

plot_series(
    population_series,
    "Participations dans les champs par population",
    "Participations dans les champs",
    FIGURE_DIR
    / "longitudinal_populations_2017_2026.png",
)

sex_series = {
    label: [
        as_int(
            axis_row(
                year,
                "SEXE",
                code,
            ),
            "participations_dans_les_champs",
        )
        for year in YEARS
    ]
    for code, label in SEXES
}

plot_series(
    sex_series,
    "Participations dans les champs par sexe",
    "Participations dans les champs",
    FIGURE_DIR
    / "longitudinal_sexes_2017_2026.png",
)

event_series = {
    label: [
        as_int(
            axis_row(
                year,
                "EPREUVE",
                code,
            ),
            "participations_dans_les_champs",
        )
        for year in YEARS
    ]
    for code, label in EVENTS
}

plot_series(
    event_series,
    "Participations dans les champs par ?preuve",
    "Participations dans les champs",
    FIGURE_DIR
    / "longitudinal_epreuves_2017_2026.png",
)


DEPTH_FIGURE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(
    figsize=(10.5, 6)
)

plt.plot(
    YEARS,
    mean_effective,
    marker="o",
    label="Moyenne par champ effectif",
)

plt.plot(
    YEARS,
    median_effective,
    marker="o",
    label="Médiane par champ effectif",
)

plt.title(
    "Profondeur moyenne et médiane des champs disputés"
)

plt.xlabel("Année")
plt.ylabel("Participants par champ")
plt.xticks(YEARS)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig(
    DEPTH_FIGURE,
    dpi=200,
    bbox_inches="tight",
)

plt.close()


participants_difference, participants_rate = evolution(
    participants[0],
    participants[-1],
)

fields_difference, fields_rate = evolution(
    field_participations[0],
    field_participations[-1],
)


lines: list[str] = []


def add(*values: str) -> None:
    lines.extend(values)


add(
    "# Évolution de la participation et de la profondeur des champs",
    "",
    "## Championnats de France de ski nautique classique — 2017-2026",
    "",
    "**Rapport longitudinal comparatif — version 2**",
    "",
    "## 1. Objet du rapport",
    "",
    (
        "Ce rapport analyse séparément chacun des Championnats de "
        "France de ski nautique classique organisés entre 2017 et "
        "2026, puis confronte les dix diagnostics annuels."
    ),
    "",
    (
        "L’objectif n’est pas d’additionner les dix années dans une "
        "population statistique unique, mais d’observer l’évolution "
        "du système compétitif : contractions, rebonds, ruptures et "
        "transformations de la profondeur des champs."
    ),
    "",
    (
        "L’unité de comparaison reste le Championnat de France annuel."
    ),
    "",
    "## 2. Méthode",
    "",
    "### 2.1 Participants distincts",
    "",
    (
        "Le nombre de **participants distincts** correspond au nombre "
        "de personnes différentes recensées au cours d’un championnat."
    ),
    "",
    (
        "Un même sportif n’est compté qu’une fois dans cet indicateur, "
        "même s’il participe dans plusieurs catégories et plusieurs "
        "épreuves."
    ),
    "",
    "### 2.2 Participations dans les champs",
    "",
    (
        "Les **participations dans les champs** correspondent à la "
        "somme des sportifs observés dans chaque champ "
        "(= catégorie × sexe × épreuve). Une même personne peut donc "
        "être comptée dans plusieurs champs."
    ),
    "",
    (
        "Cet indicateur repose sur les résultats classés par épreuve. "
        "Un sportif recensé dans le championnat sans résultat classé "
        "dans une épreuve contribue au nombre de participants "
        "distincts, mais pas nécessairement aux participations dans "
        "les champs."
    ),
    "",
    "### 2.3 Grille annuelle de référence",
    "",
    (
        "Une grille analytique identique est appliquée à chaque année : "
        "13 catégories × 2 sexes × 4 épreuves, soit "
        "**104 champs de référence par année**."
    ),
    "",
    (
        "Cette grille standardisée est un outil de comparaison. "
        "Elle ne signifie pas que chacun des 104 champs figurait "
        "nécessairement au programme réglementaire de chaque édition."
    ),
    "",
    (
        "Un champ sans résultat classé conserve un effectif nul. "
        "Le dénominateur constant permet de confronter directement "
        "les années."
    ),
    "",
    "### 2.4 Indicateurs de profondeur",
    "",
    (
        "La profondeur annuelle est appréciée à partir du nombre de "
        "champs effectifs, de l’effectif moyen et médian par champ, "
        "de la proportion de champs comptant de 1 à 3 participants "
        "et de l’effectif maximal observé."
    ),
    "",
    "### 2.5 Poids numérique des podiums",
    "",
    (
        "Pour une année `a`, la part des participations couverte par "
        "les podiums est calculée ainsi :"
    ),
    "",
    (
        "`P_a = [Σ_i min(3, n_(a,i)) / Σ_i n_(a,i)] × 100`"
    ),
    "",
    (
        "Dans cette formule, `n_(a,i)` représente l’effectif du champ "
        "`i` pendant l’année `a`."
    ),
    "",
    (
        "Le calcul est pondéré par les participations : un champ de "
        "dix participants pèse davantage qu’un champ d’un participant."
    ),
    "",
    (
        "Cet indicateur ne mesure ni la valeur sportive d’une médaille "
        "ni la probabilité individuelle d’en obtenir une."
    ),
    "",
    "## 3. Diagnostic annuel global",
    "",
    (
        "| Année | Participants distincts | F | H | Champs effectifs | "
        "Occupation | Participations dans les champs | Moyenne/champ | "
        "Médiane | Champs de 1 à 3 | Part de 1 à 3 | Maximum | Podiums |"
    ),
    (
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        "---:|---:|---:|"
    ),
)


for year in YEARS:
    row = global_lookup[year]

    add(
        "| "
        + " | ".join(
            [
                str(year),
                row["participants_distincts"],
                row["femmes_distinctes"],
                row["hommes_distincts"],
                row["champs_effectifs"] + " / 104",
                fr_pct(
                    as_float(
                        row,
                        "taux_occupation_pct",
                    )
                ),
                row["participations_dans_les_champs"],
                fr(
                    as_float(
                        row,
                        "moyenne_par_champ_effectif",
                    )
                ),
                fr(
                    as_float(
                        row,
                        "mediane_par_champ_effectif",
                    )
                ),
                row["champs_1_a_3_participants"],
                fr_pct(
                    as_float(
                        row,
                        "part_champs_1_a_3_parmi_effectifs_pct",
                    )
                ),
                row["effectif_maximal_d_un_champ"],
                fr_pct(
                    as_float(
                        row,
                        "part_des_participations_couverte_pct",
                    )
                ),
            ]
        )
        + " |"
    )


add(
    "",
    (
        f"Entre 2017 et 2026, les participants distincts passent de "
        f"**{participants[0]} à {participants[-1]}**, soit "
        f"**{abs(participants_difference)} personnes de moins** "
        f"et une évolution de "
        f"**{signed_percentage(participants_rate)}**."
    ),
    "",
    (
        f"Les participations dans les champs passent de "
        f"**{field_participations[0]} à "
        f"{field_participations[-1]}**, soit "
        f"**{abs(fields_difference)} de moins** et une évolution de "
        f"**{signed_percentage(fields_rate)}**."
    ),
    "",
    (
        "Cette comparaison entre les extrémités ne suffit pas à "
        "décrire l’évolution. La série fait apparaître plusieurs "
        "séquences distinctes."
    ),
    "",
    (
        "![Participants distincts]"
        "(figures/longitudinal_participants_distincts_2017_2026.png)"
    ),
    "",
    (
        "![Participations dans les champs]"
        "(figures/longitudinal_participations_champs_2017_2026.png)"
    ),
    "",
    (
        "![Moyenne et médiane par champ]"
        "(figures/longitudinal_moyenne_mediane_champs_2017_2026.png)"
    ),
    "",
    "## 4. Périodisation de l’évolution",
    "",
    "### 4.1 De 2017 à 2019 : stabilité des effectifs, amincissement des champs",
    "",
    (
        "Les participants distincts demeurent relativement stables : "
        "**103 en 2017, 101 en 2018 et 99 en 2019**."
    ),
    "",
    (
        "Les participations dans les champs passent toutefois de "
        "**256 à 224 puis 229**. La médiane diminue de **4 à 3**, "
        "tandis que le poids des podiums passe de **57,0 %** à "
        "**71,0 %**, puis **69,4 %**."
    ),
    "",
    (
        "La fragilisation de la profondeur apparaît donc avant la "
        "contraction récente du nombre de participants."
    ),
    "",
    "### 4.2 L’année 2020 : contraction générale",
    "",
    (
        "En 2020, le championnat réunit **82 participants distincts**, "
        "**48 champs effectifs** et **172 participations dans les "
        "champs**."
    ),
    "",
    (
        "Cette édition constitue une rupture statistique. Le rapport "
        "décrit cette rupture sans lui attribuer de cause."
    ),
    "",
    "### 4.3 Les années 2021 et 2022 : deux configurations atypiques",
    "",
    (
        "En 2021, le nombre de participants distincts atteint le "
        "maximum de la période avec **110 personnes**, mais les "
        "participations dans les champs restent limitées à **176**, "
        "réparties dans **57 champs effectifs**."
    ),
    "",
    (
        "En 2022, seulement **49 champs** sont effectifs, mais ils "
        "réunissent **189 participations** et l’un d’eux atteint "
        "**18 participants**. Le poids des podiums revient à "
        "**60,3 %**."
    ),
    "",
    (
        "Les deux éditions présentent donc des structures très "
        "différentes."
    ),
    "",
    "### 4.4 L’année 2023 : élargissement sans retour à la profondeur de 2017",
    "",
    (
        "En 2023, le nombre de champs effectifs atteint son maximum "
        "avec **69 champs sur 104**, et le championnat réunit "
        "**109 participants distincts**."
    ),
    "",
    (
        "Cependant, **44 champs sur 69**, soit **63,8 %**, ne comptent "
        "que 1 à 3 participants. L’effectif moyen est de **3,2 par "
        "champ**, contre **4,3 en 2017**."
    ),
    "",
    (
        "L’architecture compétitive s’élargit donc sans retrouver la "
        "profondeur du début de période."
    ),
    "",
    "### 4.5 De 2024 à 2026 : contraction sur trois éditions successives",
    "",
    (
        "| Année | Participants distincts | Participations dans les "
        "champs | Champs effectifs | Champs de 1 à 3 | Podiums |"
    ),
    "|---:|---:|---:|---:|---:|---:|",
)


for year in (2023, 2024, 2025, 2026):
    row = global_lookup[year]

    add(
        "| "
        + " | ".join(
            [
                str(year),
                row["participants_distincts"],
                row["participations_dans_les_champs"],
                row["champs_effectifs"] + " / 104",
                (
                    row["champs_1_a_3_participants"]
                    + " / "
                    + row["champs_effectifs"]
                ),
                fr_pct(
                    as_float(
                        row,
                        "part_des_participations_couverte_pct",
                    )
                ),
            ]
        )
        + " |"
    )


add(
    "",
    (
        "Entre 2023 et 2026, les participants distincts passent de "
        "**109 à 69**, les participations dans les champs de "
        "**221 à 141** et les champs effectifs de **69 à 52**."
    ),
    "",
    (
        "Cette succession constitue la contraction récente la plus "
        "lisible de la période."
    ),
    "",
    (
        "![Occupation et profondeur]"
        "(figures/longitudinal_structure_champs_2017_2026.png)"
    ),
    "",
    (
        "![Poids des podiums]"
        "(figures/longitudinal_poids_podiums_2017_2026.png)"
    ),
    "",
    "## 5. Comparaison par population",
    "",
    (
        "| Année | Relève : participations | Relève : champs | "
        "U21/Open : participations | U21/Open : champs | "
        "Seniors : participations | Seniors : champs |"
    ),
    "|---:|---:|---:|---:|---:|---:|---:|",
)


for year in YEARS:
    values = [str(year)]

    for code, _label in POPULATIONS:
        row = axis_row(
            year,
            "POPULATION",
            code,
        )

        values.extend(
            [
                row["participations_dans_les_champs"],
                (
                    row["champs_effectifs"]
                    + " / "
                    + row["champs_possibles"]
                ),
            ]
        )

    add(
        "| "
        + " | ".join(values)
        + " |"
    )


releve_2017 = axis_row(
    2017,
    "POPULATION",
    "RELEVE",
)

releve_2026 = axis_row(
    2026,
    "POPULATION",
    "RELEVE",
)

releve_mean_2017 = (
    as_int(
        releve_2017,
        "participations_dans_les_champs",
    )
    / as_int(
        releve_2017,
        "champs_effectifs",
    )
)

releve_mean_2026 = (
    as_int(
        releve_2026,
        "participations_dans_les_champs",
    )
    / as_int(
        releve_2026,
        "champs_effectifs",
    )
)


add(
    "",
    "### 5.1 Relève : maintien des champs, amincissement de leur profondeur",
    "",
    (
        "La Relève compte **28 champs effectifs et 134 participations "
        "en 2017**, contre **31 champs et 81 participations en 2026**."
    ),
    "",
    (
        f"L’effectif moyen passe de **{fr(releve_mean_2017)} à "
        f"{fr(releve_mean_2026)} participants par champ effectif**."
    ),
    "",
    (
        "La part des champs de 1 à 3 participants passe parallèlement "
        "de **32,1 % à 71,0 %**."
    ),
    "",
    "### 5.2 U21 / Open : une structure très volatile",
    "",
    (
        "En 2018, l’ensemble U21/Open compte **46 participations "
        "réparties dans les 16 champs de référence**, avec une médiane "
        "de **2,5** et un poids des podiums de **80,4 %**."
    ),
    "",
    (
        "En 2022, il compte **66 participations dans seulement "
        "8 champs**, avec une médiane de **7,5**, un maximum de "
        "**18 participants** et un poids des podiums de **36,4 %**."
    ),
    "",
    (
        "Des volumes proches peuvent donc correspondre à des structures "
        "compétitives très différentes."
    ),
    "",
    "### 5.3 Seniors : une rupture propre à 2026",
    "",
    (
        "Les Seniors passent de **83 participations dans 25 champs en "
        "2025** à **15 participations dans 8 champs en 2026**."
    ),
    "",
    (
        "Tous les champs Seniors disputés en 2026 comptent de 1 à "
        "3 participants. Cette situation ne doit pas être présentée "
        "comme l’aboutissement d’une baisse continue sur dix ans."
    ),
    "",
    (
        "![Évolution par population]"
        "(figures/longitudinal_populations_2017_2026.png)"
    ),
    "",
    "## 6. Comparaison par sexe",
    "",
    (
        "Les données de cette section sont des participations dans "
        "les champs et non des personnes distinctes."
    ),
    "",
    (
        "| Année | Femmes : participations | Femmes : champs | "
        "Femmes : médiane | Femmes : podiums | Hommes : participations | "
        "Hommes : champs | Hommes : médiane | Hommes : podiums |"
    ),
    "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
)


for year in YEARS:
    women = axis_row(
        year,
        "SEXE",
        "FEMMES",
    )

    men = axis_row(
        year,
        "SEXE",
        "HOMMES",
    )

    add(
        "| "
        + " | ".join(
            [
                str(year),
                women["participations_dans_les_champs"],
                women["champs_effectifs"] + " / 52",
                fr(
                    as_float(
                        women,
                        "mediane_par_champ_effectif",
                    )
                ),
                fr_pct(
                    as_float(
                        women,
                        "part_des_participations_couverte_pct",
                    )
                ),
                men["participations_dans_les_champs"],
                men["champs_effectifs"] + " / 52",
                fr(
                    as_float(
                        men,
                        "mediane_par_champ_effectif",
                    )
                ),
                fr_pct(
                    as_float(
                        men,
                        "part_des_participations_couverte_pct",
                    )
                ),
            ]
        )
        + " |"
    )


add(
    "",
    (
        "Les champs féminins sont, sur la plupart des éditions, moins "
        "nombreux et moins profonds que les champs masculins."
    ),
    "",
    (
        "L’année 2025 est particulièrement fragile : "
        "**38 participations féminines**, **23 champs effectifs**, "
        "une médiane de **1 participante** et un poids des podiums "
        "de **97,4 %**."
    ),
    "",
    (
        "En 2026, les participations féminines remontent à **54**, "
        "mais le poids des podiums reste élevé, à **87,0 %**."
    ),
    "",
    (
        "![Évolution par sexe]"
        "(figures/longitudinal_sexes_2017_2026.png)"
    ),
    "",
    "## 7. Comparaison par épreuve",
    "",
    (
        "| Épreuve | Participations 2017 | Participations 2026 | "
        "Évolution | Médiane 2017 | Médiane 2026 | "
        "Podiums 2017 | Podiums 2026 |"
    ),
    "|---|---:|---:|---:|---:|---:|---:|---:|",
)


for code, label in EVENTS:
    start_row = axis_row(
        2017,
        "EPREUVE",
        code,
    )

    end_row = axis_row(
        2026,
        "EPREUVE",
        code,
    )

    start_value = as_int(
        start_row,
        "participations_dans_les_champs",
    )

    end_value = as_int(
        end_row,
        "participations_dans_les_champs",
    )

    difference, rate = evolution(
        start_value,
        end_value,
    )

    add(
        "| "
        + " | ".join(
            [
                label,
                str(start_value),
                str(end_value),
                (
                    signed_integer(difference)
                    + " ("
                    + signed_percentage(rate)
                    + ")"
                ),
                fr(
                    as_float(
                        start_row,
                        "mediane_par_champ_effectif",
                    )
                ),
                fr(
                    as_float(
                        end_row,
                        "mediane_par_champ_effectif",
                    )
                ),
                fr_pct(
                    as_float(
                        start_row,
                        "part_des_participations_couverte_pct",
                    )
                ),
                fr_pct(
                    as_float(
                        end_row,
                        "part_des_participations_couverte_pct",
                    )
                ),
            ]
        )
        + " |"
    )


add(
    "",
    (
        "Le slalom demeure l’épreuve la plus fournie, mais ses "
        "participations passent de **101 à 61**, sa médiane de "
        "**6 à 3** et le poids de ses podiums de **41,6 % à 72,1 %**."
    ),
    "",
    (
        "En figures, la médiane tombe à **1 participant en 2026**."
    ),
    "",
    (
        "Le saut et le combiné demeurent durablement fragiles. "
        "En 2026, leurs podiums couvrent respectivement "
        "**90,9 % et 90,5 %** des participations."
    ),
    "",
    (
        "![Évolution par épreuve]"
        "(figures/longitudinal_epreuves_2017_2026.png)"
    ),
    "",
    "## 8. Lecture longitudinale",
    "",
    (
        "L’évolution 2017-2026 ne se résume ni à une baisse régulière "
        "ni à la seule situation de 2026."
    ),
    "",
    (
        "Elle combine un amincissement précoce des champs entre "
        "2017 et 2019, une rupture générale en 2020, deux configurations "
        "atypiques en 2021 et 2022, un élargissement sans réelle "
        "profondeur en 2023, puis une contraction continue entre "
        "2023 et 2026."
    ),
    "",
    (
        "Le nombre de champs occupés ne permet donc pas, à lui seul, "
        "d’apprécier la solidité du système compétitif."
    ),
    "",
    "## 9. Limites",
    "",
    (
        "Les participations dans les champs reposent sur les résultats "
        "classés et ne représentent pas nécessairement la totalité "
        "des inscriptions."
    ),
    "",
    (
        "La grille de 104 champs est une grille analytique standardisée "
        "et ne préjuge pas du programme réglementaire exact de chaque "
        "édition."
    ),
    "",
    (
        "L’absence d’un sportif dans un Championnat de France ne permet "
        "pas de conclure à un abandon de la pratique."
    ),
    "",
    (
        "Les pourcentages doivent toujours être lus avec les effectifs "
        "et leurs dénominateurs, particulièrement lorsque les champs "
        "comptent moins de dix participants."
    ),
    "",
    "## 10. Conclusion provisoire",
    "",
    (
        "Sur la période étudiée, la contraction de la participation "
        "nationale s’accompagne d’une réduction plus forte des "
        "participations classées et d’une augmentation du poids "
        "numérique des podiums."
    ),
    "",
    (
        "Cette transformation n’est cependant ni régulière ni uniforme. "
        "Elle affecte différemment les populations, les sexes et les "
        "quatre épreuves."
    ),
    "",
    (
        "La solidité de la filière ne peut donc pas être appréciée à "
        "partir du seul nombre de champs ouverts ou du nombre de "
        "médailles distribuées."
    ),
    "",
    "## Sources de données",
    "",
    f"- `{GLOBAL_FILE.as_posix()}`",
    f"- `{AXES_FILE.as_posix()}`",
    "",
)


REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)


print("=" * 96)
print("RAPPORT LONGITUDINAL V2 GENERE")
print("=" * 96)
print("Rapport :", REPORT_FILE)
print("Figure  :", DEPTH_FIGURE)
print()
print(
    "2017 :",
    participants[0],
    "participants ;",
    field_participations[0],
    "participations dans les champs ; moyenne",
    fr(mean_effective[0]),
)
print(
    "2023 :",
    participants[6],
    "participants ;",
    field_participations[6],
    "participations dans les champs ; moyenne",
    fr(mean_effective[6]),
)
print(
    "2026 :",
    participants[-1],
    "participants ;",
    field_participations[-1],
    "participations dans les champs ; moyenne",
    fr(mean_effective[-1]),
)
print()
print("Aucun commit n'a ete cree.")
