PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iwwf_id TEXT UNIQUE,
    nom TEXT NOT NULL,
    date_debut TEXT,
    date_fin TEXT,
    pays TEXT,
    ville TEXT,
    discipline TEXT
);

CREATE TABLE IF NOT EXISTS riders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iwwf_id TEXT UNIQUE,
    nom TEXT NOT NULL,
    prenom TEXT,
    sexe TEXT,
    nation TEXT
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    categorie TEXT,
    rang INTEGER,
    score TEXT,

    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (rider_id) REFERENCES riders(id)
);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    categorie TEXT,
    club TEXT,
    equipe TEXT,

    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (rider_id) REFERENCES riders(id),

    UNIQUE (competition_id, rider_id, categorie)
);

CREATE INDEX IF NOT EXISTS idx_entries_competition
ON entries (competition_id);

CREATE INDEX IF NOT EXISTS idx_entries_rider
ON entries (rider_id);

CREATE INDEX IF NOT EXISTS idx_results_competition
ON results (competition_id);

CREATE INDEX IF NOT EXISTS idx_results_rider
ON results (rider_id);
CREATE TABLE IF NOT EXISTS riders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iwwf_id TEXT UNIQUE,
    nom TEXT NOT NULL,
    prenom TEXT,
    sexe TEXT,
    nation TEXT,
    annee_naissance INTEGER
);