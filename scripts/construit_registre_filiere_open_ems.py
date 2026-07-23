"""Construit le registre U17 -> U21 -> Open à partir des inscriptions EMS 2023-2025.

Les Seniors sont conservés uniquement comme population d'aval/contexte.
Aucun fichier existant n'est modifié.
"""
from __future__ import annotations

import csv
import re
import statistics
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

YEARS = (2023, 2024, 2025)
TARGET = {"U17", "U21", "OPEN"}


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    return re.sub(r"\s+", " ", text).strip()


def truthy(value: str | None) -> bool:
    return norm(value) in {"1", "TRUE", "YES", "Y", "OUI", "X"}


def delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        return ";"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as fh:
        return [
            {str(k): (v or "").strip() for k, v in row.items()}
            for row in csv.DictReader(fh, delimiter=delimiter(path))
        ]


def write_rows(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def classify(category_raw: str) -> str:
    c = norm(category_raw)
    if not c:
        return "OTHER"
    if "OPEN" in c or re.search(r"(^| )PRO( |$)", c):
        return "OPEN"
    if re.search(r"(^| )(35|45|55|65|70|75|80|85)\+", c):
        return "SENIOR"
    if re.match(r"^-?21(?:\s|$)", c) or "U21" in c or "UNDER 21" in c:
        return "U21"
    if re.match(r"^-?17(?:\s|$)", c) or "U17" in c or "JUNIOR" in c:
        return "U17"
    if re.match(r"^-?(8|10|12|14)(?:\s|$)", c) or re.search(r"U(8|10|12|14)", c):
        return "RELEVES"
    return "OTHER"


def infer_sex(category_raw: str) -> str:
    match = re.search(r"(?:^|\s)(F|M)(?:\s|\(|$)", norm(category_raw))
    return match.group(1) if match else ""


def as_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def joined(values) -> str:
    return " | ".join(sorted({str(v) for v in values if str(v)}))


@dataclass
class AthleteYear:
    year: int
    key: str
    name: str = ""
    yob: int | None = None
    sexes: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    populations: set[str] = field(default_factory=set)
    comps_all: set[str] = field(default_factory=set)
    comps_pop: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    disciplines_all: set[str] = field(default_factory=set)
    disciplines_open: set[str] = field(default_factory=set)
    open_champ: set[str] = field(default_factory=set)

    def add(self, row: dict[str, str], pop: str) -> None:
        code = row.get("CompetitionCode", "")
        category = row.get("Category", "")
        self.name = row.get("Name", "") or self.name
        self.yob = self.yob if self.yob is not None else as_int(row.get("YOB"))
        sex = infer_sex(category)
        if sex:
            self.sexes.add(sex)
        self.categories.add(category)
        self.populations.add(pop)
        if code:
            self.comps_all.add(code)
            self.comps_pop[pop].add(code)
        for column, disc in (("Slalom", "SLALOM"), ("Tricks", "FIGURES"), ("Jump", "SAUT")):
            if truthy(row.get(column)):
                self.disciplines_all.add(disc)
                if pop == "OPEN":
                    self.disciplines_open.add(disc)
        if pop == "OPEN" and code:
            ctype = norm(row.get("CompetitionType"))
            cname = norm(row.get("CompetitionName"))
            if ctype == "NATCH" or "CHAMPIONNAT DE FRANCE" in cname:
                self.open_champ.add(code)

    def has(self, pop: str) -> int:
        return int(pop in self.populations)

    def count(self, pop: str) -> int:
        return len(self.comps_pop.get(pop, set()))

    def row(self) -> dict[str, object]:
        target_comps: set[str] = set()
        for pop in TARGET:
            target_comps |= self.comps_pop.get(pop, set())
        return {
            "Year": self.year,
            "AthleteKey": self.key,
            "Name": self.name,
            "YOB": self.yob or "",
            "Age": self.year - self.yob if self.yob else "",
            "Sex": joined(self.sexes),
            "RegisteredCategories": joined(self.categories),
            "RegisteredPopulations": joined(self.populations),
            "HasReleves": self.has("RELEVES"),
            "HasU17": self.has("U17"),
            "HasU21": self.has("U21"),
            "HasOpen": self.has("OPEN"),
            "HasSenior": self.has("SENIOR"),
            "HasOther": self.has("OTHER"),
            "CompetitionsAll": len(self.comps_all),
            "CompetitionsTarget": len(target_comps),
            "CompetitionsReleves": self.count("RELEVES"),
            "CompetitionsU17": self.count("U17"),
            "CompetitionsU21": self.count("U21"),
            "CompetitionsOpen": self.count("OPEN"),
            "CompetitionsSenior": self.count("SENIOR"),
            "CompetitionsOther": self.count("OTHER"),
            "PhysicalDisciplinesAll": joined(self.disciplines_all),
            "PhysicalDisciplineCountAll": len(self.disciplines_all),
            "PhysicalDisciplinesOpen": joined(self.disciplines_open),
            "PhysicalDisciplineCountOpen": len(self.disciplines_open),
            "OpenChampionshipParticipation": int(bool(self.open_champ)),
            "OpenChampionshipCodes": joined(self.open_champ),
        }


@dataclass
class Competition:
    year: int
    code: str
    date: str = ""
    name: str = ""
    ctype: str = ""
    homol: str = ""
    site: str = ""
    all_athletes: set[str] = field(default_factory=set)
    by_pop: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def add(self, row: dict[str, str], athlete: str, pop: str) -> None:
        self.date = self.date or row.get("CompetitionDate", "")
        self.name = self.name or row.get("CompetitionName", "")
        self.ctype = self.ctype or row.get("CompetitionType", "")
        self.homol = self.homol or row.get("Homologation", "")
        self.site = self.site or row.get("Site", "")
        self.all_athletes.add(athlete)
        self.by_pop[pop].add(athlete)

    def n(self, pop: str) -> int:
        return len(self.by_pop.get(pop, set()))

    def target(self) -> set[str]:
        out: set[str] = set()
        for pop in TARGET:
            out |= self.by_pop.get(pop, set())
        return out

    def profile(self) -> str:
        total, target, senior, open_n, u21 = len(self.all_athletes), len(self.target()), self.n("SENIOR"), self.n("OPEN"), self.n("U21")
        if total == 0:
            return "AUCUN_FRANCAIS"
        if target == 0 and senior > 0:
            return "SENIOR_SANS_FILIERE_CIBLE"
        if senior / total >= 0.5 and senior > target:
            return "DOMINANTE_SENIOR"
        if open_n >= 5 and open_n >= senior:
            return "CENTREE_OPEN"
        if open_n + u21 >= 5:
            return "U21_OPEN_SIGNIFICATIF"
        if target > 0:
            return "FILIERE_CIBLE_FAIBLE"
        return "AUTRE"

    def row(self) -> dict[str, object]:
        total, target, senior, open_n, u21 = len(self.all_athletes), len(self.target()), self.n("SENIOR"), self.n("OPEN"), self.n("U21")
        return {
            "Year": self.year,
            "CompetitionCode": self.code,
            "CompetitionDate": self.date,
            "CompetitionName": self.name,
            "CompetitionType": self.ctype,
            "Homologation": self.homol,
            "Site": self.site,
            "FrenchAthletesAll": total,
            "FrenchTargetAthletes": target,
            "FrenchReleves": self.n("RELEVES"),
            "FrenchU17": self.n("U17"),
            "FrenchU21": u21,
            "FrenchOpen": open_n,
            "FrenchSenior": senior,
            "FrenchOther": self.n("OTHER"),
            "TargetSharePercent": round(100 * target / total, 1) if total else "",
            "OpenSharePercent": round(100 * open_n / total, 1) if total else "",
            "SeniorSharePercent": round(100 * senior / total, 1) if total else "",
            "HasU21": int(u21 > 0),
            "HasOpen": int(open_n > 0),
            "HasFiveOpen": int(open_n >= 5),
            "HasFiveU21Open": int(u21 + open_n >= 5),
            "AnalyticalProfile": self.profile(),
        }


def build(root: Path):
    athletes: dict[tuple[int, str], AthleteYear] = {}
    competitions: dict[tuple[int, str], Competition] = {}
    for year in YEARS:
        path = root / "data" / "processed" / f"ems_participations_france_waterski_{year}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        for row in read_rows(path):
            if not (truthy(row.get("IsFrench")) or norm(row.get("Country")) == "FRA"):
                continue
            code = row.get("CompetitionCode", "")
            if not code:
                continue
            key = row.get("AthleteKey", "") or f"FRA|{row.get('YOB','')}|{norm(row.get('NormalizedName') or row.get('Name'))}"
            pop = classify(row.get("Category", ""))
            athletes.setdefault((year, key), AthleteYear(year, key)).add(row, pop)
            competitions.setdefault((year, code), Competition(year, code)).add(row, key, pop)
    return athletes, competitions


def u21_transitions(athletes):
    by_athlete = defaultdict(dict)
    for (year, key), record in athletes.items():
        by_athlete[key][year] = record
    rows = []
    for key, years in sorted(by_athlete.items()):
        u21_years = sorted(y for y, r in years.items() if r.has("U21"))
        if not u21_years:
            continue
        first_u21 = u21_years[0]
        open_years = sorted(y for y, r in years.items() if y >= first_u21 and r.has("OPEN"))
        first_open = open_years[0] if open_years else None
        if first_open is not None:
            delay = first_open - first_u21
            outcome = "OPEN_MEME_ANNEE" if delay == 0 else "OPEN_ANNEE_SUIVANTE" if delay == 1 else "OPEN_PLUS_TARD"
            censored = 0
        elif first_u21 == 2025:
            delay, outcome, censored = "", "SANS_OPEN_OBSERVE_DROITE_CENSUREE", 1
        else:
            delay, outcome, censored = "", "SANS_OPEN_OBSERVE_JUSQU_EN_2025", 0
        origin = years[first_u21]
        rows.append({
            "AthleteKey": key,
            "Name": origin.name,
            "Sex": joined(origin.sexes),
            "YOB": origin.yob or "",
            "FirstU21YearInWindow": first_u21,
            "U21Years": joined(u21_years),
            "FirstOpenYearInWindow": first_open or "",
            "DelayU21ToOpenYears": delay,
            "Outcome": outcome,
            "RightCensored": censored,
            "U21CompetitionsFirstYear": origin.count("U21"),
        })
    return rows


def open_retention(athletes):
    rows = []
    for start, end in ((2023, 2024), (2024, 2025)):
        keys = sorted(k for (y, k), r in athletes.items() if y == start and r.has("OPEN"))
        for key in keys:
            origin = athletes[(start, key)]
            dest = athletes.get((end, key))
            if dest is None:
                status = "SORTIE_DU_CIRCUIT_FRANCAIS_EMS"
            elif dest.has("OPEN"):
                status = "MAINTIEN_OPEN_AVEC_SENIOR" if dest.has("SENIOR") else "MAINTIEN_OPEN"
            elif dest.has("SENIOR"):
                status = "SENIOR_SANS_OPEN"
            else:
                status = "ACTIF_HORS_OPEN_ET_SENIOR"
            rows.append({
                "FromYear": start,
                "ToYear": end,
                "AthleteKey": key,
                "Name": origin.name,
                "Sex": joined(origin.sexes),
                "YOB": origin.yob or "",
                "OpenCompetitionsFromYear": origin.count("OPEN"),
                "OpenPhysicalDisciplineCountFromYear": len(origin.disciplines_open),
                "OpenChampionshipFromYear": int(bool(origin.open_champ)),
                "DestinationStatus": status,
                "OpenCompetitionsToYear": dest.count("OPEN") if dest else 0,
                "SeniorCompetitionsToYear": dest.count("SENIOR") if dest else 0,
            })
    return rows


def pct(a: int, b: int) -> str:
    return "n.d." if not b else f"{100*a/b:.1f} %".replace(".", ",")


def diagnostic(athletes, competitions, u21_rows, open_rows) -> str:
    lines = [
        "DIAGNOSTIC DE LA FILIÈRE U21 → OPEN — EMS 2023-2025",
        "=" * 78,
        "",
        "PÉRIMÈTRE",
        "Catégories réellement inscrites dans EMS. U17, U21 et Open forment la filière cible.",
        "Les Seniors sont isolés comme population d'aval. Les données décrivent des inscriptions approuvées.",
        "",
        "1. COMPOSITION ANNUELLE",
        "-" * 78,
    ]
    for year in YEARS:
        recs = [r for (y, _), r in athletes.items() if y == year]
        target = sum(bool(r.populations & TARGET) for r in recs)
        lines.append(
            f"{year} : total={len(recs)} ; filière cible={target} ; U17={sum(r.has('U17') for r in recs)} ; "
            f"U21={sum(r.has('U21') for r in recs)} ; Open={sum(r.has('OPEN') for r in recs)} ; "
            f"Seniors={sum(r.has('SENIOR') for r in recs)}."
        )
    lines += ["", "2. CALENDRIER ET UTILITÉ POUR LA FILIÈRE", "-" * 78]
    for year in YEARS:
        comps = [c for (y, _), c in competitions.items() if y == year]
        target_sizes = [len(c.target()) for c in comps if c.target()]
        open_sizes = [c.n("OPEN") for c in comps if c.n("OPEN")]
        lines.append(
            f"{year} : {len(comps)} compétitions ; {sum(bool(c.target()) for c in comps)} avec U17/U21/Open ; "
            f"{sum(c.n('U21')>0 for c in comps)} avec U21 ; {sum(c.n('OPEN')>0 for c in comps)} avec Open ; "
            f"{sum(c.n('OPEN')>=5 for c in comps)} avec au moins 5 Open ; "
            f"{sum(c.profile() in {'DOMINANTE_SENIOR','SENIOR_SANS_FILIERE_CIBLE'} for c in comps)} à dominante Senior ou sans filière cible."
        )
        lines.append(
            f"       Médiane U17/U21/Open lorsqu'ils sont présents={statistics.median(target_sizes) if target_sizes else 0:.1f} ; "
            f"médiane Open={statistics.median(open_sizes) if open_sizes else 0:.1f}."
        )
    lines += ["", "3. PASSAGE U21 → OPEN", "-" * 78]
    for cohort in YEARS:
        cohort_rows = [r for r in u21_rows if r["FirstU21YearInWindow"] == cohort]
        converted = sum(str(r["Outcome"]).startswith("OPEN_") for r in cohort_rows)
        same = sum(r["Outcome"] == "OPEN_MEME_ANNEE" for r in cohort_rows)
        next_y = sum(r["Outcome"] == "OPEN_ANNEE_SUIVANTE" for r in cohort_rows)
        if cohort == 2025:
            lines.append(f"Cohorte U21 2025 : {len(cohort_rows)} sportifs ; {same} également Open la même année ; suivi futur censuré.")
        else:
            lines.append(f"Cohorte U21 {cohort} : {len(cohort_rows)} sportifs ; {converted} observés en Open ({pct(converted,len(cohort_rows))}) ; même année={same} ; année suivante={next_y}.")
    lines += ["", "4. PÉRENNITÉ EN OPEN", "-" * 78]
    for start, end in ((2023, 2024), (2024, 2025)):
        trs = [r for r in open_rows if r["FromYear"] == start]
        kept = sum(r["DestinationStatus"] in {"MAINTIEN_OPEN","MAINTIEN_OPEN_AVEC_SENIOR"} for r in trs)
        senior_only = sum(r["DestinationStatus"] == "SENIOR_SANS_OPEN" for r in trs)
        exits = sum(r["DestinationStatus"] == "SORTIE_DU_CIRCUIT_FRANCAIS_EMS" for r in trs)
        lines.append(f"{start}→{end} : {len(trs)} Open initiaux ; {kept} maintenus en Open ({pct(kept,len(trs))}) ; {senior_only} seulement Seniors ; {exits} absents du circuit français EMS.")
    lines += [
        "",
        "5. RÈGLES D'INTERPRÉTATION",
        "-" * 78,
        "- Le total toutes catégories ne doit pas servir seul à évaluer la filière de performance.",
        "- Les Seniors documentent uniquement l'aval et la continuité après Open.",
        "- La catégorie réellement inscrite prévaut sur une catégorie reconstruite par l'âge.",
        "- Une compétition avec un ou deux Open n'a pas la même fonction qu'un champ Open significatif.",
        "- L'absence l'année suivante ne prouve pas un abandon définitif.",
        "",
        "FIN DU DIAGNOSTIC",
    ]
    return "\n".join(lines)


def main() -> None:
    root = root_dir()
    athletes, competitions = build(root)
    register_rows = [r.row() for _, r in sorted(athletes.items())]
    competition_rows = [c.row() for _, c in sorted(competitions.items())]
    u21_rows = u21_transitions(athletes)
    open_rows = open_retention(athletes)

    out = root / "data" / "processed"
    write_rows(out / "registre_filiere_open_ems_2023_2025.csv", register_rows, [
        "Year","AthleteKey","Name","YOB","Age","Sex","RegisteredCategories","RegisteredPopulations",
        "HasReleves","HasU17","HasU21","HasOpen","HasSenior","HasOther","CompetitionsAll","CompetitionsTarget",
        "CompetitionsReleves","CompetitionsU17","CompetitionsU21","CompetitionsOpen","CompetitionsSenior","CompetitionsOther",
        "PhysicalDisciplinesAll","PhysicalDisciplineCountAll","PhysicalDisciplinesOpen","PhysicalDisciplineCountOpen",
        "OpenChampionshipParticipation","OpenChampionshipCodes"
    ])
    write_rows(out / "synthese_competitions_filiere_open_2023_2025.csv", competition_rows, [
        "Year","CompetitionCode","CompetitionDate","CompetitionName","CompetitionType","Homologation","Site",
        "FrenchAthletesAll","FrenchTargetAthletes","FrenchReleves","FrenchU17","FrenchU21","FrenchOpen","FrenchSenior","FrenchOther",
        "TargetSharePercent","OpenSharePercent","SeniorSharePercent","HasU21","HasOpen","HasFiveOpen","HasFiveU21Open","AnalyticalProfile"
    ])
    write_rows(out / "transitions_u21_open_2023_2025.csv", u21_rows, [
        "AthleteKey","Name","Sex","YOB","FirstU21YearInWindow","U21Years","FirstOpenYearInWindow",
        "DelayU21ToOpenYears","Outcome","RightCensored","U21CompetitionsFirstYear"
    ])
    write_rows(out / "retention_open_2023_2025.csv", open_rows, [
        "FromYear","ToYear","AthleteKey","Name","Sex","YOB","OpenCompetitionsFromYear",
        "OpenPhysicalDisciplineCountFromYear","OpenChampionshipFromYear","DestinationStatus","OpenCompetitionsToYear","SeniorCompetitionsToYear"
    ])
    diag_path = root / "data" / "exports" / "diagnostic_filiere_open_2023_2025.txt"
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    diag_path.write_text(diagnostic(athletes, competitions, u21_rows, open_rows), encoding="utf-8")

    print("=" * 88)
    print("REGISTRE FILIERE OPEN CONSTRUIT")
    print("=" * 88)
    print(f"Sportifs-années : {len(register_rows)}")
    print(f"Compétitions    : {len(competition_rows)}")
    print(f"Trajectoires U21: {len(u21_rows)}")
    print(f"Transitions Open: {len(open_rows)}")
    print(f"Diagnostic      : {diag_path}")
    print("Aucun fichier existant n'a été modifié.")


if __name__ == "__main__":
    main()
