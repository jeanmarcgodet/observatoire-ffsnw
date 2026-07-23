"""Exporte la version 4 du rapport Ã  partir du moteur d'export V3.

Ce script rÃ©utilise le moteur dÃ©jÃ  validÃ© dans
scripts/export_longitudinal_report_pdf_v3.py, en substituant uniquement
les chemins et libellÃ©s de version. Il doit Ãªtre exÃ©cutÃ© depuis le dÃ©pÃ´t.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V3_EXPORTER = ROOT / "scripts" / "export_longitudinal_report_pdf_v3.py"

if not V3_EXPORTER.exists():
    raise FileNotFoundError(
        f"Exporteur V3 introuvable : {V3_EXPORTER}"
    )

source = V3_EXPORTER.read_text(encoding="utf-8")
source = source.replace("PDF V3 GENERE", "PDF V4 GENERE")

replacements = (
    (
        "rapport_longitudinal_participation_2017_2026_v3.md",
        "rapport_longitudinal_participation_2017_2026_v4.md",
    ),
    (
        "rapport_longitudinal_participation_2017_2026_v3.pdf",
        "rapport_longitudinal_participation_2017_2026_v4.pdf",
    ),
    (
        "version 3",
        "version 4",
    ),
    (
        "Version 3",
        "Version 4",
    ),
)

for old, new in replacements:
    source = source.replace(old, new)

namespace = {
    "__name__": "__main__",
    "__file__": str(Path(__file__).resolve()),
}

exec(
    compile(
        source,
        str(V3_EXPORTER),
        "exec",
    ),
    namespace,
)
