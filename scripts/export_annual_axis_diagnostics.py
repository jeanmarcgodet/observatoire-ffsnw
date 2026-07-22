"""Diagnostics annuels des champs par population, sexe et epreuve."""

import csv
from pathlib import Path
from statistics import median


FIELD_FILE = Path(
    "data/exports/podiums_par_categorie_sexe_epreuve_2017_2026.csv"
)

OVERALL_FILE = Path(
    "data/exports/diagnostic_annuel_champs_2017_2026.csv"
)

OUTPUT_FILE = Path(
    "data/exports/diagnostic_annuel_par_axes_2017_2026.csv"
)


YEARS = list(range(2017, 2027))

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
    "Combine",
]


POPULATIONS = {
    "RELEVE": [
        "U8",
        "U10",
        "U12",
        "U14",
        "U17",
    ],
    "U21_OPEN": [
        "U21",
        "OPEN",
    ],
    "SENIORS": [
        "35+",
        "45+",
        "55+",
        "65+",
        "70+",
        "75+",
    ],
}


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


def normalize_event(value):
    value = value.strip()

    if value in (
        "Combin\u00e9",
        "Combine",
    ):
        return "Combine"

    return value


def decimal(value):
    if value is None:
        return ""

    return f"{value:.1f}"


def metrics(counts):
    effective = [
        count
        for count in counts
        if count > 0
    ]

    possible_fields = len(counts)
    effective_fields = len(effective)
    empty_fields = possible_fields - effective_fields

    fields_1_to_3 = sum(
        1 <= count <= 3
        for count in counts
    )

    participations = sum(counts)

    podium_places = sum(
        min(3, count)
        for count in counts
    )

    return {
        "champs_possibles": possible_fields,
        "champs_effectifs": effective_fields,
        "champs_vides": empty_fields,
        "taux_occupation_pct": decimal(
            100 * effective_fields / possible_fields
            if possible_fields
            else None
        ),
        "champs_amps_effectifs": effective_fields,
        "champs_vides": empty_fields,
        "taux_occupation_pct": decimal(
            100 * effective_fields / possible_fields
            if possible_fields
            else None
        ),
        "champs_1_a_3_participants": fields_1_to_3,
        "part_champs_1_a_3_parmi_effectifs_pct": decimal(
            100 * fields_1_to_3 / effective_fields
            if effective_fields
            else None
        ),
        "participations_dans_les_champs": participations,
        "moyenne_par_champ_effectif": decimal(
            participations / effective_fields
            if effective_fields
            else None
        ),
        "mediane_par_champ_effectif": decimal(
            median(effective)
            if effective
            else None
        ),
        "effectif_maximal_d_un_champ": (
            max(effective)
            if effective
            else 0
        ),
        "places_de_podium_couvertes": podium_places,
        "part_des_participations_couverte_pct": decimal(
            100 * podium_places / participations
            if participations
            else None
        ),
    }


field_rows = read_csv(FIELD_FILE)
overall_rows = read_csv(OVERALL_FILE)


field_lookup = {}

for row in field_rows:
    key = (
        int(row["annee"]),
        row["categorie"].strip().upper(),
        row["sexe"].strip(),
        normalize_event(row["epreuve"]),
    )

    if key in field_lookup:
        raise RuntimeError(
            f"Champ duplique : {key}"
        )

    field_lookup[key] = int(
        row["participants"]
    )


overall_lookup = {
    int(row["annee"]): row
    for row in overall_rows
}


def get_counts(
    year,
    categories,
    sexes,
    events,
):
    return [
        field_lookup[
            (
                year,
                category,
                sex,
                event,
            )
        ]
        for category in categories
        for sex in sexes
        for event in events
    ]


output_rows = []


for year in YEARS:

    # Population
    for group, categories in POPULATIONS.items():
        row = {
            "annee": year,
            "axe": "POPULATION",
            "groupe": group,
        }

        row.update(
            metrics(
                get_counts(
                    year,
                    categories,
                    SEXES,
                    EVENTS,
                )
            )
        )

        output_rows.append(row)

    # Sexe
    for sex in SEXES:
        row = {
            "annee": year,
            "axe": "SEXE",
            "groupe": (
                "FEMMES"
                if sex == "Femmes"
                else "HOMMES"
            ),
        }

        row.update(
            metrics(
                get_counts(
                    year,
                    CATEGORIES,
                    [sex],
                    EVENTS,
                )
            )
        )

        output_rows.append(row)

    # Epreuve
    for event in EVENTS:
        row = {
            "annee": year,
            "axe": "EPREUVE",
            "groupe": event.upper(),
        }

        row.update(
            metrics(
                get_counts(
                    year,
                    CATEGORIES,
                    SEXES,
                    [event],
                )
            )
        )

        output_rows.append(row)


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


with OUTPUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=list(
            output_rows[0].keys()
        ),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(output_rows)


# Controles de coherence avec le diagnostic global.
for year in YEARS:
    expected = overall_lookup[year]

    for axis in (
        "POPULATION",
        "SEXE",
        "EPREUVE",
    ):
        rows = [
            row
            for row in output_rows
            if (
                row["annee"] == year
                and row["axe"] == axis
            )
        ]

        possible = sum(
            row["champs_possibles"]
            for row in rows
        )

        effective = sum(
            row["champs_effectifs"]
            for row in rows
        )

        participations = sum(
            row["participations_dans_les_champs"]
            for row in rows
        )

        if possible != 104:
            raise RuntimeError(
                f"{year} {axis} : "
                f"{possible} champs possibles."
            )

        if effective != int(
            expected["champs_effectifs"]
        ):
            raise RuntimeError(
                f"{year} {axis} : "
                f"{effective} champs effectifs au lieu de "
                f"{expected['champs_effectifs']}."
            )

        if participations != int(
            expected["participations_dans_les_champs"]
        ):
            raise RuntimeError(
                f"{year} {axis} : "
                f"{participations} participations au lieu de "
                f"{expected['participations_dans_les_champs']}."
            )


def print_table(axis, groups, title):
    print()
    print("=" * 132)
    print(title)
    print("=" * 132)

    print(
        f"{'Annee':<7}"
        f"{'Groupe':<12}"
        f"{'Champs':>10}"
        f"{'Occup.':>10}"
        f"{'Part.':>9}"
        f"{'Ch. 1-3':>10}"
        f"{'% 1-3':>9}"
        f"{'Mediane':>10}"
        f"{'Maximum':>10}"
        f"{'Podiums':>11}"
    )

    for year in YEARS:
        for group in groups:
            row = next(
                item
                for item in output_rows
                if (
                    item["annee"] == year
                    and item["axe"] == axis
                    and item["groupe"] == group
                )
            )

            print(
                f"{year:<7}"
                f"{group:<12}"
                f"{str(row['champs_effectifs']) + '/' + str(row['champs_possibles']):>10}"
                f"{row['taux_occupation_pct'] + ' %':>10}"
                f"{row['participations_dans_les_champs']:>9}"
                f"{row['champs_1_a_3_participants']:>10}"
                f"{row['part_champs_1_a_3_parmi_effectifs_pct'] + ' %':>9}"
                f"{row['mediane_par_champ_effectif']:>10}"
                f"{row['effectif_maximal_d_un_champ']:>10}"
                f"{row['part_des_participations_couverte_pct'] + ' %':>11}"
            )


print_table(
    "POPULATION",
    [
        "RELEVE",
        "U21_OPEN",
        "SENIORS",
    ],
    "DIAGNOSTIC ANNUEL PAR POPULATION",
)

print_table(
    "SEXE",
    [
        "FEMMES",
        "HOMMES",
    ],
    "DIAGNOSTIC ANNUEL PAR SEXE",
)

print_table(
    "EPREUVE",
    [
        "SLALOM",
        "FIGURES",
        "SAUT",
        "COMBINE",
    ],
    "DIAGNOSTIC ANNUEL PAR EPREUVE",
)


print()
print("=" * 132)
print("CONTROLES")
print("=" * 132)
print(
    "Pour chaque annee, les sommes par population, sexe et epreuve "
    "retrouvent exactement le diagnostic global."
)
print("Fichier genere :", OUTPUT_FILE)
