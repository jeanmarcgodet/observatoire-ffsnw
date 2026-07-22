"""Diagnostic annuel comparable des champs de competition."""

import csv
from pathlib import Path
from statistics import median


ANNUAL_FILE = Path(
    "data/exports/participation_annuelle_2017_2026.csv"
)

FIELD_FILE = Path(
    "data/exports/podiums_par_categorie_sexe_epreuve_2017_2026.csv"
)

OUTPUT_FILE = Path(
    "data/exports/diagnostic_annuel_champs_2017_2026.csv"
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

POSSIBLE_FIELDS = (
    len(CATEGORIES)
    * len(SEXES)
    * len(EVENTS)
)


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

    mapping = {
        "Combin\u00e9": "Combine",
        "Combine": "Combine",
    }

    return mapping.get(
        value,
        value,
    )


def read_integer(row, names, required=False):
    for name in names:
        value = row.get(name)

        if value not in ("", None):
            return int(
                float(
                    str(value).replace(
                        ",",
                        ".",
                    )
                )
            )

    if required:
        raise RuntimeError(
            "Colonne introuvable parmi : "
            + ", ".join(names)
        )

    return None


def decimal(value):
    if value is None:
        return ""

    return f"{value:.1f}"


annual_rows = read_csv(
    ANNUAL_FILE
)

field_rows = read_csv(
    FIELD_FILE
)


annual_lookup = {}

for row in annual_rows:
    year = int(row["annee"])

    annual_lookup[year] = {
        "participants_distincts": read_integer(
            row,
            [
                "participants",
                "participants_distincts",
                "total",
                "effectif_total",
            ],
            required=True,
        ),
        "femmes_distinctes": read_integer(
            row,
            [
                "femmes",
                "participants_femmes",
                "femmes_distinctes",
                "F",
            ],
        ),
        "hommes_distincts": read_integer(
            row,
            [
                "hommes",
                "participants_hommes",
                "hommes_distincts",
                "H",
            ],
        ),
    }


field_lookup = {}

for row in field_rows:
    key = (
        int(row["annee"]),
        row["categorie"].strip().upper(),
        row["sexe"].strip(),
        normalize_event(
            row["epreuve"]
        ),
    )

    if key in field_lookup:
        raise RuntimeError(
            f"Champ duplique : {key}"
        )

    field_lookup[key] = int(
        row["participants"]
    )


expected_keys = [
    (
        year,
        category,
        sex,
        event,
    )
    for year in YEARS
    for category in CATEGORIES
    for sex in SEXES
    for event in EVENTS
]


missing_keys = [
    key
    for key in expected_keys
    if key not in field_lookup
]

if missing_keys:
    print(
        "Premiers champs manquants :",
        missing_keys[:10],
    )

    raise RuntimeError(
        f"{len(missing_keys)} champs manquants."
    )


output_rows = []


for year in YEARS:
    counts = [
        field_lookup[
            (
                year,
                category,
                sex,
                event,
            )
        ]
        for category in CATEGORIES
        for sex in SEXES
        for event in EVENTS
    ]

    effective_counts = [
        count
        for count in counts
        if count > 0
    ]

    effective_fields = len(
        effective_counts
    )

    empty_fields = (
        POSSIBLE_FIELDS
        - effective_fields
    )

    fields_1 = sum(
        count == 1
        for count in counts
    )

    fields_2 = sum(
        count == 2
        for count in counts
    )

    fields_3 = sum(
        count == 3
        for count in counts
    )

    fields_1_to_3 = sum(
        1 <= count <= 3
        for count in counts
    )

    fields_4_to_5 = sum(
        4 <= count <= 5
        for count in counts
    )

    fields_6_to_9 = sum(
        6 <= count <= 9
        for count in counts
    )

    fields_10_plus = sum(
        count >= 10
        for count in counts
    )

    field_participations = sum(
        counts
    )

    podium_places = sum(
        min(3, count)
        for count in counts
    )

    occupation_rate = (
        100
        * effective_fields
        / POSSIBLE_FIELDS
    )

    fields_1_to_3_rate = (
        100
        * fields_1_to_3
        / effective_fields
        if effective_fields
        else None
    )

    mean_all_fields = (
        field_participations
        / POSSIBLE_FIELDS
    )

    mean_effective_fields = (
        field_participations
        / effective_fields
        if effective_fields
        else None
    )

    median_effective_fields = (
        median(effective_counts)
        if effective_counts
        else None
    )

    maximum_field = (
        max(effective_counts)
        if effective_counts
        else 0
    )

    podium_coverage = (
        100
        * podium_places
        / field_participations
        if field_participations
        else None
    )

    annual_data = annual_lookup[
        year
    ]

    output_rows.append(
        {
            "annee": year,
            "participants_distincts": annual_data[
                "participants_distincts"
            ],
            "femmes_distinctes": (
                annual_data[
                    "femmes_distinctes"
                ]
                if annual_data[
                    "femmes_distinctes"
                ] is not None
                else ""
            ),
            "hommes_distincts": (
                annual_data[
                    "hommes_distincts"
                ]
                if annual_data[
                    "hommes_distincts"
                ] is not None
                else ""
            ),
            "champs_possibles": POSSIBLE_FIELDS,
            "champs_effectifs": effective_fields,
            "champs_vides": empty_fields,
            "taux_occupation_pct": decimal(
                occupation_rate
            ),
            "champs_1_participant": fields_1,
            "champs_2_participants": fields_2,
            "champs_3_participants": fields_3,
            "champs_1_a_3_participants": fields_1_to_3,
            "part_champs_1_a_3_parmi_effectifs_pct": decimal(
                fields_1_to_3_rate
            ),
            "champs_4_a_5_participants": fields_4_to_5,
            "champs_6_a_9_participants": fields_6_to_9,
            "champs_10_participants_ou_plus": fields_10_plus,
            "participations_dans_les_champs": field_participations,
            "moyenne_par_champ_possible": decimal(
                mean_all_fields
            ),
            "moyenne_par_champ_effectif": decimal(
                mean_effective_fields
            ),
            "mediane_par_champ_effectif": decimal(
                median_effective_fields
            ),
            "effectif_maximal_d_un_champ": maximum_field,
            "places_de_podium_couvertes": podium_places,
            "part_des_participations_couverte_pct": decimal(
                podium_coverage
            ),
        }
    )


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
    writer.writerows(
        output_rows
    )


print("=" * 150)
print("DIAGNOSTIC ANNUEL COMPARABLE DES CHAMPS - 2017-2026")
print("=" * 150)

print(
    f"{'Annee':<7}"
    f"{'Distincts':>11}"
    f"{'F':>6}"
    f"{'H':>6}"
    f"{'Champs':>11}"
    f"{'Vides':>8}"
    f"{'Occup.':>10}"
    f"{'Ch. 1-3':>10}"
    f"{'% 1-3':>9}"
    f"{'Mediane':>10}"
    f"{'Maximum':>10}"
    f"{'Part. champs':>14}"
    f"{'Podiums':>11}"
)


for row in output_rows:
    women = (
        str(row["femmes_distinctes"])
        if row["femmes_distinctes"] != ""
        else "-"
    )

    men = (
        str(row["hommes_distincts"])
        if row["hommes_distincts"] != ""
        else "-"
    )

    print(
        f"{row['annee']:<7}"
        f"{row['participants_distincts']:>11}"
        f"{women:>6}"
        f"{men:>6}"
        f"{str(row['champs_effectifs']) + '/104':>11}"
        f"{row['champs_vides']:>8}"
        f"{row['taux_occupation_pct'] + ' %':>10}"
        f"{row['champs_1_a_3_participants']:>10}"
        f"{row['part_champs_1_a_3_parmi_effectifs_pct'] + ' %':>9}"
        f"{row['mediane_par_champ_effectif']:>10}"
        f"{row['effectif_maximal_d_un_champ']:>10}"
        f"{row['participations_dans_les_champs']:>14}"
        f"{row['part_des_participations_couverte_pct'] + ' %':>11}"
    )


row_2026 = next(
    row
    for row in output_rows
    if row["annee"] == 2026
)


checks = {
    "participants_distincts": 69,
    "champs_effectifs": 52,
    "champs_vides": 52,
    "champs_1_a_3_participants": 36,
    "effectif_maximal_d_un_champ": 7,
    "part_des_participations_couverte_pct": "79.4",
}


for field, expected in checks.items():
    actual = row_2026[field]

    if actual != expected:
        raise RuntimeError(
            f"Controle 2026 incorrect : "
            f"{field}={actual!r}, attendu={expected!r}"
        )


print()
print("Controle 2026 : OK")
print("Fichier genere :", OUTPUT_FILE)
