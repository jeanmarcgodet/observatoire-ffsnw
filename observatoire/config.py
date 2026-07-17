from pathlib import Path

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dossiers principaux
DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"
DOCS_DIR = PROJECT_ROOT / "docs"

# Base de données SQLite
DATABASE_FILE = DATA_DIR / "observatoire.db"