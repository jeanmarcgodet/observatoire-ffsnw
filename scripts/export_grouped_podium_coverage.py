"""Agrège la couverture des podiums par population, sexe et épreuve."""

import csv
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path(
    "data/exports/podiums_par_categorie_sexe_epreuve_2017_2026.csv"
)

OUTPUT_FILE = Path(
    "data/exports/podiums_groupes_releve_u21_open_seniors_2017_2026.csv"
)


GROUPS = {
    "Relève": [
        "U8",
        "U10",
        "U12",
        "U14",
        "U17",
    ],
    "U21 / Open": [
        "U21",
        "OPEN",
    ],
    "Seniors": [
        "35+",
        "45+",
        "55+",
        "65+",
        "70+",
        "75+",
    ],
}

EVENTS = [
    "Slalom",
    "Figures",
    "Saut",
    "Combiné",
]

SEX_SCOPES = {
    "F": ["Femmes"],
    "H": ["Hommes"],
    "H/F": ["Femmes", "Hommes"],
}


with INPUT_FILE.open(
    newline="",
    encoding="utf-8-sig",
) as handle:
    rows = list(
        csv.DictReader(
            handle,
            delimiter=";",
        )
    )


lookup = defaultdict(int)

for row in rows:
    lookup[
        (
            int(row["annee"]),
            row["categorie"],
            row["sexe"],
            row["epreuve"],
        )
    ] = int(row["participants"])


output_rows = []


for year in range(2017, 2027):
    for group, categories in GROUPS.items():
        for sex_scope, sexes in SEX_SCOPES.items():
            for event in EVENTS:
                field_counts = [
                    lookup.get(
                        (
                            year,
                            category,
                            sex,
                            event,
                        ),
                        0,
                    )
                    for category in categories
                    for sex in sexes
                ]

                participations = sum(field_counts)

                possible_fields = (
                    len(categories) * len(sexes)
                )

                effective_fields = sum(
                    count > 0
                    for count in field_counts
                )

                fields_with_three_or_less = sum(
                    1 <= count <= 3
                    for count in field_counts
                )

                podium_places_covered = sum(
                    min(3, count)
                    for count in field_counts
                )

                average_effective = (
                    participations / effective_fields
                    if effective_fields
                    else None
                )

                coverage_pct = (
                    100
                    * podium_places_covered
                    / participations
                    if participations
                    else None
                )

                output_rows.append(
                    {
                        "annee": year,
                        "population": group,
                        "sexe": sex_scope,
                        "epreuve": event,
                        "participations": participations,
                        "champs_possibles": possible_fields,
                        "champs_effectifs": effective_fields,
                        "champs_de_1_a_3_participants": (
                            fields_with_three_or_less
                        ),
                        "participants_moyens_par_champ_effectif": (
                            f"{average_effective:.1f}"
                            if average_effective is not None
                            else ""
                        ),
                        "places_de_podium_couvertes": (
                            podium_places_covered
                        ),
                        "part_du_champ_couverte_pct": (
                            f"{coverage_pct:.1f}"
                            if coverage_pct is not None
                            else ""
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
        fieldnames=list(output_rows[0]),
        delimiter=";",
    )

    writer.writeheader()
    writer.writerows(output_rows)


print("=" * 154)
print("COUVERTURE DES PODIUMS PAR POPULATION, SEXE ET EPREUVE — 2026")
print("=" * 154)

print(
    f"{'Population':<13}"
    f"{'Sexe':<6}"
    f"{'Epreuve':<11}"
    f"{'Part.':>8}"
    f"{'Poss.':>8}"
    f"{'Effect.':>9}"
    f"{'Champs 1-3':>12}"
    f"{'Moy./champ':>12}"
    f"{'Places':>9}"
    f"{'Couverture':>13}"
)


for row in output_rows:
    if row["annee"] != 2026:
        continue

    coverage = (
        f"{row['part_du_champ_couverte_pct']} %"
        if row["part_du_champ_couverte_pct"]
        else "—"
    )

    average = (
        row["participants_moyens_par_champ_effectif"]
        or "—"
    )

    print(
        f"{row['population']:<13}"
        f"{row['sexe']:<6}"
        f"{row['epreuve']:<11}"
        f"{row['participations']:>8}"
        f"{row['champs_possibles']:>8}"
        f"{row['champs_effectifs']:>9}"
        f"{row['champs_de_1_a_3_participants']:>12}"
        f"{average:>12}"
        f"{row['places_de_podium_couvertes']:>9}"
        f"{coverage:>13}"
    )


print()
print("=" * 154)
print("CONTROLE DES CHAMPS POSSIBLES")
print("=" * 154)
print("Relève F ou H     : 5 champs par épreuve")
print("Relève H/F        : 10 champs par épreuve")
print("U21 / Open F ou H : 2 champs par épreuve")
print("U21 / Open H/F    : 4 champs par épreuve")
print("Seniors F ou H    : 6 champs par épreuve")
print("Seniors H/F       : 12 champs par épreuve")

print()
print("=" * 154)
print("PRECISION METHODOLOGIQUE")
print("=" * 154)
print(
    "La ligne H/F additionne les champs féminins et masculins. "
    "Elle ne correspond pas à une compétition mixte."
)
print(
    "Les places de podium couvertes sont calculées séparément "
    "dans chaque champ catégorie × sexe × épreuve."
)
print(
    "La part couverte vaut somme(min(3, effectif)) divisée par "
    "la somme des participations."
)
print(
    "Elle ne mesure pas la probabilité sportive individuelle "
    "d'obtenir une médaille."
)

print()
print("Fichier généré :", OUTPUT_FILE)
