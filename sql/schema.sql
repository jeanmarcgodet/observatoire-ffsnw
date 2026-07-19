PRAGMA foreign_keys = ON;

-- =========================================================
-- COMPÉTITIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iwwf_id TEXT NOT NULL UNIQUE,
    nom TEXT NOT NULL,
    date_debut TEXT,
    date_fin TEXT,
    pays TEXT,
    ville TEXT,
    discipline TEXT
);

-- =========================================================
-- RIDERS
-- =========================================================

CREATE TABLE IF NOT EXISTS riders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iwwf_id TEXT NOT NULL UNIQUE,
    nom TEXT NOT NULL,
    prenom TEXT,
    sexe TEXT CHECK (
        sexe IS NULL
        OR sexe IN ('M', 'F')
    ),
    nation TEXT,
    annee_naissance INTEGER CHECK (
        annee_naissance IS NULL
        OR annee_naissance BETWEEN 1900 AND 2100
    )
);

-- =========================================================
-- INSCRIPTIONS
-- Une ligne représente l'inscription d'un rider
-- dans une catégorie donnée.
-- =========================================================

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    categorie TEXT,
    club TEXT,
    equipe TEXT,

    FOREIGN KEY (competition_id)
        REFERENCES competitions(id)
        ON DELETE CASCADE,

    FOREIGN KEY (rider_id)
        REFERENCES riders(id)
        ON DELETE CASCADE,

    UNIQUE (
        competition_id,
        rider_id,
        categorie
    )
);

-- =========================================================
-- RÉSULTATS / PERFORMANCES
-- Une ligne représente une performance sportive unique.
-- =========================================================

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    discipline TEXT NOT NULL,
    tour TEXT NOT NULL,
    score TEXT NOT NULL,
    document_url TEXT,

    FOREIGN KEY (competition_id)
        REFERENCES competitions(id)
        ON DELETE CASCADE,

    FOREIGN KEY (rider_id)
        REFERENCES riders(id)
        ON DELETE CASCADE,

    UNIQUE (
    competition_id,
    rider_id,
    discipline,
    tour,
    score
    )
);

-- =========================================================
-- CLASSIFICATIONS
-- Une même performance peut apparaître dans plusieurs
-- classements : Open, U21, classement général, etc.
-- =========================================================

CREATE TABLE IF NOT EXISTS result_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL,
    classement TEXT NOT NULL,
    categorie TEXT,
    sexe TEXT CHECK (
        sexe IS NULL
        OR sexe IN ('M', 'F')
    ),
    rang INTEGER,
    ligue TEXT,
    fichier_source TEXT NOT NULL,

    FOREIGN KEY (result_id)
        REFERENCES results(id)
        ON DELETE CASCADE,

    UNIQUE (
        result_id,
        classement,
        fichier_source
    )
);

-- =========================================================
-- INDEX
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_competitions_iwwf_id
ON competitions (iwwf_id);

CREATE INDEX IF NOT EXISTS idx_riders_iwwf_id
ON riders (iwwf_id);

CREATE INDEX IF NOT EXISTS idx_entries_competition
ON entries (competition_id);

CREATE INDEX IF NOT EXISTS idx_entries_rider
ON entries (rider_id);

CREATE INDEX IF NOT EXISTS idx_results_competition
ON results (competition_id);

CREATE INDEX IF NOT EXISTS idx_results_rider
ON results (rider_id);

CREATE INDEX IF NOT EXISTS idx_results_discipline
ON results (discipline);

CREATE INDEX IF NOT EXISTS idx_result_classifications_result
ON result_classifications (result_id);

CREATE INDEX IF NOT EXISTS idx_result_classifications_category
ON result_classifications (categorie);

CREATE INDEX IF NOT EXISTS idx_result_classifications_source
ON result_classifications (fichier_source);


