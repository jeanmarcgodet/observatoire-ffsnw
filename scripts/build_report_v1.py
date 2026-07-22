"""Construit le rapport V1 sur la participation et la profondeur des podiums."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ANNUAL_FILE = Path(
    "data/exports/participation_annuelle_2017_2026.csv"
)

DETAILED_FILE = Path(
    "data/exports/podiums_par_categorie_sexe_epreuve_2017_2026.csv"
)

GROUPED_FILE = Path(
    "data/exports/podiums_groupes_releve_u21_open_seniors_2017_2026.csv"
)

REPORT_FILE = Path(
    "reports/rapport_v1_participation_podiums_2017_2026.md"
)

FIGURE_FILE = Path(
    "reports/figures/couverture_podiums_groupes_2026.png"
)


CATEGORIES = [
    "U8",
    "U10",
    "U12",
    "U14",
    "U17",
    "U21",
    "OPEN",
    "35+",
    "45+",
    "55+",
    "65+",
    "70+",
    "75+",
]

SEXES = [
    "Femmes",
    "Hommes",
]

EVENTS = [
    "Slalom",
    "Figures",
    "Saut",
    "Combiné",
]

POPULATIONS = [
    "Relève",
    "U21 / Open",
    "Seniors",
]

SEX_SCOPES = [
    "F",
    "H",
    "H/F",
]


def read_csv(path):
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


def annual_count(row):
    for field in (
        "participants",
        "participants_distincts",
        "total",
    ):
        if field in row and row[field] != "":
            return int(row[field])

    raise RuntimeError(
        "Colonne d'effectif annuel introuvable."
    )


def fr_decimal(value, digits=1):
    return f"{value:.{digits}f}".replace(
        ".",
        ",",
    )


def fr_percentage(value):
    return (
        fr_decimal(float(value), 1) + " %"
        if value not in ("", None)
        else "—"
    )


annual_rows = read_csv(ANNUAL_FILE)
detailed_rows = read_csv(DETAILED_FILE)
grouped_rows = read_csv(GROUPED_FILE)


annual = {
    int(row["annee"]): annual_count(row)
    for row in annual_rows
}


detailed_2026 = [
    row
    for row in detailed_rows
    if int(row["annee"]) == 2026
]


detailed_lookup = {
    (
        row["categorie"],
        row["sexe"],
        row["epreuve"],
    ): row
    for row in detailed_2026
}


grouped_2026 = [
    row
    for row in grouped_rows
    if int(row["annee"]) == 2026
]


grouped_lookup = {
    (
        row["population"],
        row["sexe"],
        row["epreuve"],
    ): row
    for row in grouped_2026
}


field_counts = [
    int(row["participants"])
    for row in detailed_2026
]

theoretical_fields = (
    len(CATEGORIES)
    * len(SEXES)
    * len(EVENTS)
)

if len(field_counts) != theoretical_fields:
    raise RuntimeError(
        f"{len(field_counts)} champs trouvés au lieu de "
        f"{theoretical_fields}."
    )


effective_fields = sum(
    count > 0
    for count in field_counts
)

empty_fields = sum(
    count == 0
    for count in field_counts
)

fields_one_to_three = sum(
    1 <= count <= 3
    for count in field_counts
)

fields_four_or_less = sum(
    1 <= count <= 4
    for count in field_counts
)

fields_five_or_less = sum(
    1 <= count <= 5
    for count in field_counts
)

maximum_field = max(field_counts)

total_field_participations = sum(
    field_counts
)

covered_podium_places = sum(
    min(3, count)
    for count in field_counts
)

overall_coverage = (
    100
    * covered_podium_places
    / total_field_participations
)


change_2017_2026 = (
    annual[2026]
    - annual[2017]
)

change_2017_2026_pct = (
    100
    * change_2017_2026
    / annual[2017]
)

change_2023_2026 = (
    annual[2026]
    - annual[2023]
)

change_2023_2026_pct = (
    100
    * change_2023_2026
    / annual[2023]
)


# Figure : couverture des podiums, lignes H/F uniquement.
chart_rows = [
    grouped_lookup[
        (
            population,
            "H/F",
            event,
        )
    ]
    for population in POPULATIONS
    for event in EVENTS
]

chart_labels = [
    (
        row["population"]
        + "\n"
        + row["epreuve"]
    )
    for row in chart_rows
]

chart_values = [
    float(
        row["part_du_champ_couverte_pct"]
    )
    if row["part_du_champ_couverte_pct"]
    else 0
    for row in chart_rows
]


FIGURE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.figure(
    figsize=(13, 7)
)

plt.bar(
    chart_labels,
    chart_values,
)

plt.title(
    "Part des participations couverte par les podiums en 2026"
)

plt.ylabel(
    "Part couverte (%)"
)

plt.ylim(
    0,
    110,
)

plt.grid(
    axis="y",
    alpha=0.3,
)

plt.xticks(
    rotation=45,
    ha="right",
)

for index, value in enumerate(
    chart_values
):
    if value:
        plt.text(
            index,
            value + 2,
            fr_decimal(value) + " %",
            ha="center",
            fontsize=8,
        )

plt.tight_layout()

plt.savefig(
    FIGURE_FILE,
    dpi=200,
    bbox_inches="tight",
)

plt.close()


lines = [
    "# Participation et profondeur des podiums",
    "",
    "## Championnats de France de ski nautique classique — 2017-2026",
    "",
    "**Rapport V1 — juillet 2026**",
    "",
    "## 1. Objet et périmètre",
    "",
    (
        "Ce rapport analyse les sportifs distincts effectivement "
        "recensés dans les Championnats de France de ski nautique "
        "classique intégrés à la base pour la période 2017-2026."
    ),
    "",
    (
        "Un même sportif n’est compté qu’une fois par année dans "
        "l’indicateur de participation annuelle, même s’il participe "
        "dans plusieurs catégories et plusieurs épreuves."
    ),
    "",
    (
        "Conformément à la terminologie du PPF 2025-2029, le ski "
        "nautique constitue la discipline reconnue de haut niveau. "
        "Le slalom, les figures, le saut et le combiné sont des "
        "épreuves du ski nautique ; ils ne sont pas traités ici "
        "comme des disciplines autonomes."
    ),
    "",
    (
        "Le combiné est une épreuve fondée sur les performances "
        "réalisées dans le slalom, les figures et le saut."
    ),
    "",
    "### Participants distincts et participations dans les champs",
    "",
    (
        "Le nombre de **participants distincts** correspond au "
        "nombre de personnes différentes recensées au cours d’une "
        "année."
    ),
    "",
    (
        "Les **participations dans les champs** correspondent à la "
        "somme des sportifs observés dans chaque champ "
        "catégorie × sexe × épreuve. Une même personne peut donc "
        "être comptée dans plusieurs champs."
    ),
    "",
    (
        "Ces deux indicateurs ne doivent pas être additionnés ni "
        "interprétés comme s’ils mesuraient la même réalité."
    ),
    "",
    "## 2. Évolution de la participation annuelle",
    "",
    "| Année | Participants distincts |",
    "|---:|---:|",
]

for year in range(2017, 2027):
    lines.append(
        f"| {year} | {annual[year]} |"
    )


lines.extend(
    [
        "",
        (
            f"Entre 2017 et 2026, la participation annuelle passe "
            f"de **{annual[2017]} à {annual[2026]} sportifs "
            f"distincts**, soit **{abs(change_2017_2026)} personnes "
            f"de moins** et une évolution de "
            f"**{fr_decimal(change_2017_2026_pct)} %**."
        ),
        "",
        (
            f"La contraction récente est également visible entre "
            f"2023 et 2026 : **{annual[2023]} à {annual[2026]}**, "
            f"soit **{abs(change_2023_2026)} personnes de moins** "
            f"et **{fr_decimal(change_2023_2026_pct)} %**."
        ),
        "",
        (
            "![Évolution de la participation annuelle]"
            "(figures/participation_totale_2017_2026.png)"
        ),
        "",
        "## 3. Mesure de la profondeur des podiums",
        "",
        (
            "La part théorique du champ couverte par le podium est "
            "calculée séparément dans chaque champ catégorie × sexe "
            "× épreuve."
        ),
        "",
        (
            "Pour un champ de `n` participants, l’indicateur est : "
            "`min(100 ; 3 / n × 100)`."
        ),
        "",
        (
            "Cet indicateur ne mesure pas la probabilité sportive "
            "individuelle d’obtenir une médaille. Il mesure uniquement "
            "le poids des trois places du podium au regard de la taille "
            "du champ."
        ),
        "",
        "### Situation générale en 2026",
        "",
        (
            f"Le référentiel comprend **{len(CATEGORIES)} classes**, "
            f"deux sexes et quatre épreuves, soit "
            f"**{theoretical_fields} champs théoriquement possibles**."
        ),
        "",
        (
            f"En 2026, **{effective_fields} champs** comptent au moins "
            f"un résultat et **{empty_fields} champs** sont vides."
        ),
        "",
        (
            f"Parmi les {effective_fields} champs effectivement "
            f"disputés :"
        ),
        "",
        (
            f"- **{fields_one_to_three}**, soit "
            f"**{fr_decimal(100 * fields_one_to_three / effective_fields)} %**, "
            f"comptent de un à trois participants ;"
        ),
        (
            f"- **{fields_four_or_less}**, soit "
            f"**{fr_decimal(100 * fields_four_or_less / effective_fields)} %**, "
            f"comptent au maximum quatre participants ;"
        ),
        (
            f"- **{fields_five_or_less}**, soit "
            f"**{fr_decimal(100 * fields_five_or_less / effective_fields)} %**, "
            f"comptent au maximum cinq participants ;"
        ),
        (
            f"- le champ le plus fourni ne compte que "
            f"**{maximum_field} participants**."
        ),
        "",
        (
            f"Au total, les places effectivement couvertes par les "
            f"podiums représentent **{covered_podium_places} places "
            f"sur {total_field_participations} participations**, soit "
            f"**{fr_decimal(overall_coverage)} %**."
        ),
        "",
        "## 4. Tableau détaillé par catégorie, sexe et épreuve — 2026",
        "",
        (
            "Chaque cellule indique : **nombre de participants / part "
            "théorique du champ couverte par le podium**."
        ),
        "",
        "| Catégorie | Sexe | Slalom | Figures | Saut | Combiné |",
        "|---|---|---:|---:|---:|---:|",
    ]
)


for category in CATEGORIES:
    for sex in SEXES:
        cells = []

        for event in EVENTS:
            row = detailed_lookup[
                (
                    category,
                    sex,
                    event,
                )
            ]

            count = int(
                row["participants"]
            )

            percentage = row[
                "part_theorique_podium_pct"
            ]

            if count == 0:
                cells.append(
                    "0 / —"
                )
            else:
                cells.append(
                    f"{count} / {fr_percentage(percentage)}"
                )

        lines.append(
            "| "
            + " | ".join(
                [
                    (
                        "Open"
                        if category == "OPEN"
                        else category
                    ),
                    sex,
                    *cells,
                ]
            )
            + " |"
        )


lines.extend(
    [
        "",
        "## 5. Tableau regroupé par population — 2026",
        "",
        (
            "Les populations sont regroupées comme suit : "
            "**Relève** = U8 à U17 ; **U21 / Open** = U21 et Open ; "
            "**Seniors** = 35+ à 75+."
        ),
        "",
        (
            "La ligne **H/F** additionne les champs féminins et "
            "masculins. Elle ne correspond pas à une compétition "
            "mixte."
        ),
        "",
        "| Population | Sexe | Épreuve | Participations | Champs possibles | Champs effectifs | Champs de 1 à 3 | Moyenne par champ effectif | Places couvertes | Part couverte |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
)


for population in POPULATIONS:
    for sex_scope in SEX_SCOPES:
        for event in EVENTS:
            row = grouped_lookup[
                (
                    population,
                    sex_scope,
                    event,
                )
            ]

            average = (
                row[
                    "participants_moyens_par_champ_effectif"
                ]
                or "—"
            )

            if average != "—":
                average = average.replace(
                    ".",
                    ",",
                )

            coverage = fr_percentage(
                row[
                    "part_du_champ_couverte_pct"
                ]
            )

            lines.append(
                "| "
                + " | ".join(
                    [
                        population,
                        sex_scope,
                        event,
                        row["participations"],
                        row["champs_possibles"],
                        row["champs_effectifs"],
                        row[
                            "champs_de_1_a_3_participants"
                        ],
                        average,
                        row[
                            "places_de_podium_couvertes"
                        ],
                        coverage,
                    ]
                )
                + " |"
            )


lines.extend(
    [
        "",
        (
            "![Couverture des podiums par population et épreuve]"
            "(figures/couverture_podiums_groupes_2026.png)"
        ),
        "",
        "## 6. Principaux constats",
        "",
        "### Relève",
        "",
        (
            "Pour l’ensemble femmes-hommes, la part des participations "
            "couverte par les podiums atteint **71,0 % en slalom**, "
            "**82,6 % en figures**, **92,9 % en saut** et "
            "**92,3 % en combiné**."
        ),
        "",
        "### U21 / Open",
        "",
        (
            "Pour l’ensemble femmes-hommes, la part couverte atteint "
            "**52,9 % en slalom**, **66,7 % en figures** et "
            "**87,5 % en saut comme en combiné**."
        ),
        "",
        "### Seniors",
        "",
        (
            "En 2026, les champs Seniors effectivement disputés "
            "comptent tous au maximum trois participants. La part "
            "couverte par les podiums atteint donc **100 %** dans "
            "les champs de slalom et de figures observés."
        ),
        "",
        "## 7. Interprétation institutionnelle",
        "",
        (
            "La valeur individuelle d’une médaille ne doit pas être "
            "confondue avec la profondeur collective du champ dans "
            "lequel elle est obtenue."
        ),
        "",
        (
            "Les résultats de 2026 montrent qu’une part importante "
            "des épreuves nationales fonctionne avec un nombre de "
            "participants inférieur ou égal au nombre de places "
            "disponibles sur le podium."
        ),
        "",
        (
            "Cette situation est particulièrement marquée en saut, "
            "en combiné et dans les catégories Seniors, mais elle "
            "concerne également une part importante des champs de "
            "la Relève et de l’ensemble U21/Open."
        ),
        "",
        (
            "L’évaluation de la politique sportive fédérale devrait "
            "donc intégrer, en complément du nombre de médailles, "
            "les effectifs exacts, la profondeur des champs, leur "
            "évolution, la fidélisation des compétiteurs et la "
            "continuité entre la Relève, l’U21 et l’Open."
        ),
        "",
        "## 8. Limites",
        "",
        (
            "L’absence d’un sportif dans les Championnats de France "
            "étudiés ne permet pas de conclure à un abandon de la "
            "pratique du ski nautique."
        ),
        "",
        (
            "La part couverte par les podiums est un indicateur de "
            "densité numérique. Elle ne tient pas compte du niveau "
            "relatif des concurrents, de leurs performances ni de "
            "la probabilité réelle de classement."
        ),
        "",
        (
            "Les résultats doivent être lus avec les effectifs bruts "
            "et leurs dénominateurs, particulièrement lorsque les "
            "champs comptent moins de dix participants."
        ),
        "",
        "## 9. Conclusion",
        "",
        (
            "Le système compétitif national étudié apparaît très peu "
            "profond et fortement fragmenté entre catégories, sexes "
            "et épreuves."
        ),
        "",
        (
            "En 2026, la majorité des champs effectivement disputés "
            "compte au maximum trois participants. Dans plusieurs "
            "populations et épreuves, les places de podium couvrent "
            "la totalité ou la quasi-totalité des participants."
        ),
        "",
        (
            "Le nombre de médailles ne peut donc constituer, à lui "
            "seul, un indicateur suffisant de la solidité de la "
            "filière. Il doit être rapporté au nombre de concurrents, "
            "à la profondeur des champs et à la capacité du système "
            "à fidéliser et renouveler durablement ses compétiteurs."
        ),
        "",
        "## Sources de données",
        "",
        f"- `{ANNUAL_FILE.as_posix()}`",
        f"- `{DETAILED_FILE.as_posix()}`",
        f"- `{GROUPED_FILE.as_posix()}`",
        "",
    ]
)


REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)


print("=" * 90)
print("RAPPORT V1 GENERE")
print("=" * 90)
print("Participants 2017          :", annual[2017])
print("Participants 2026          :", annual[2026])
print("Champs théoriques 2026     :", theoretical_fields)
print("Champs effectifs 2026      :", effective_fields)
print("Champs vides 2026          :", empty_fields)
print("Champs de 1 à 3            :", fields_one_to_three)
print("Champs au maximum 4        :", fields_four_or_less)
print("Champs au maximum 5        :", fields_five_or_less)
print("Maximum d'un champ         :", maximum_field)
print(
    "Couverture globale podiums :",
    fr_decimal(overall_coverage),
    "%",
)
print("Rapport                     :", REPORT_FILE)
print("Figure                      :", FIGURE_FILE)
