from pathlib import Path


path = Path("scripts/analyse_ems_champs_championnats.py")

source = path.read_text(encoding="utf-8")

replacements = [
    (
'''            population = parsed["PopulationGroup"]

            if population not in ALLOWED_POPULATIONS[
                championship_block
            ]:
''',
'''            population = parsed["PopulationGroup"]

            title_eligible = (
                population
                in ALLOWED_POPULATIONS[championship_block]
            )

            if not title_eligible:
''',
    ),
    (
'''                "ChampionshipBlock": championship_block,
                "AthleteKey": row.get("AthleteKey", ""),
''',
'''                "ChampionshipBlock": championship_block,
                "TitleEligible": int(title_eligible),
                "AthleteKey": row.get("AthleteKey", ""),
''',
    ),
    (
'''                        "ChampionshipBlock": championship_block,
                        "PopulationGroup": population,
''',
'''                        "ChampionshipBlock": championship_block,
                        "TitleEligible": int(title_eligible),
                        "PopulationGroup": population,
''',
    ),
    (
'''    field_entries = list(deduplicated_entries.values())

    # ------------------------------------------------------------
    # Synthèse par champ observé
''',
'''    field_entries = list(deduplicated_entries.values())

    title_field_entries = [
        entry
        for entry in field_entries
        if int(entry["TitleEligible"]) == 1
    ]

    parallel_field_entries = [
        entry
        for entry in field_entries
        if int(entry["TitleEligible"]) == 0
    ]

    # ------------------------------------------------------------
    # Synthèse par champ observé
''',
    ),
    (
'''    for entry in field_entries:
        key = (
            entry["Year"],
            entry["CompetitionCode"],
            entry["ChampionshipBlock"],
''',
'''    for entry in title_field_entries:
        key = (
            entry["Year"],
            entry["CompetitionCode"],
            entry["ChampionshipBlock"],
''',
    ),
    (
'''        block_participants = [
            row
            for row in participants
            if row["CompetitionCode"] == code
        ]

        block_entries = [
            row
            for row in field_entries
            if row["CompetitionCode"] == code
        ]
''',
'''        block_participants = [
            row
            for row in participants
            if (
                row["CompetitionCode"] == code
                and int(row["TitleEligible"]) == 1
            )
        ]

        block_entries = [
            row
            for row in title_field_entries
            if row["CompetitionCode"] == code
        ]
''',
    ),
    (
'''    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "champs_2023_2026.csv"
        ),
        field_summary,
    )
''',
'''    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "champs_2023_2026.csv"
        ),
        field_summary,
    )

    write_csv(
        ROOT
        / "data/processed/"
        / (
            "ems_championnats_france_"
            "entrees_paralleles_2023_2026.csv"
        ),
        parallel_field_entries,
    )
''',
    ),
    (
'''    print(f"Participants normalisés : {len(participants)}")
    print(f"Entrées dans les champs : {len(field_entries)}")
    print(f"Champs observés         : {len(field_summary)}")
    print(f"Anomalies               : {len(anomalies)}")
''',
'''    title_participants = [
        row
        for row in participants
        if int(row["TitleEligible"]) == 1
    ]

    print(f"Participants normalisés : {len(participants)}")
    print(f"Participants éligibles  : {len(title_participants)}")
    print(f"Entrées totales         : {len(field_entries)}")
    print(f"Entrées de titre        : {len(title_field_entries)}")
    print(f"Entrées parallèles      : {len(parallel_field_entries)}")
    print(f"Champs de titre observés: {len(field_summary)}")
    print(f"Anomalies               : {len(anomalies)}")
''',
    ),
]

for old, new in replacements:
    if old not in source:
        raise RuntimeError(
            "Bloc introuvable pour le remplacement :\n"
            + old[:250]
        )

    source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8")

print("Script corrigé :", path)