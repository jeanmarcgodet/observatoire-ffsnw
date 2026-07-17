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