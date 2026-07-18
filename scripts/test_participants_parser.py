from pathlib import Path

from observatoire.importers.iwwf_participants import parse_participants


html_file = Path(
    "data/raw/iwwf/26FRA021/all_skiers_list.html"
)

participants = parse_participants(html_file)

print(f"{len(participants)} participant(s) détecté(s)\n")

for participant in participants:
    print(participant)