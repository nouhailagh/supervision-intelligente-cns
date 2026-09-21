"""
02_creation_base.py
Création de la base SQLite pour la supervision ILS/DME (LOC, GP, DME).

Structure :
- table `mesures` : toutes les lectures de capteurs (timestamp, équipement, paramètre, valeur, tolérances)
- table `equipements` : référentiel des 3 équipements (métadonnées du PDF : indicatif, catégorie, fréquence, QFU, marque/modèle)
"""

import sqlite3
import pandas as pd
import os

DOSSIER_PROJET = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(
    DOSSIER_PROJET,
    "data"
)

os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(
    DATA_DIR,
    "supervision_ils_dme.db"
)
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees_simulees_ils_dme.csv")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("PRAGMA foreign_keys = ON;")

# ---------------------------------------------------------------------------
# Table équipements (référentiel — infos exactes du PDF, en-tête du relevé)
# ---------------------------------------------------------------------------
cur.execute("""
CREATE TABLE equipements (
    equipement      TEXT PRIMARY KEY,
    indicatif       TEXT,
    categorie       TEXT,
    frequence       TEXT,
    qfu             TEXT,
    marque_modele   TEXT,
    domaine_cns     TEXT
)
""")

cur.executemany("""
INSERT INTO equipements (equipement, indicatif, categorie, frequence, qfu, marque_modele, domaine_cns)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    ("LOC", "LFA", "II", "109.7 MHz",  "Rwy 27", "NM 7014B4",  "Navigation"),
    ("GP",  "LFA", "II", "333.2 MHz",  "Rwy 27", "NM 7033B4",  "Navigation"),
    ("DME", "LFA", "II", "34 X",       "Rwy 27", "NM LDB-103", "Navigation"),
])

# ---------------------------------------------------------------------------
# Table mesures (données de supervision simulées)
# ---------------------------------------------------------------------------
cur.execute("""
CREATE TABLE mesures (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL,
    equipement          TEXT NOT NULL,
    parametre           TEXT NOT NULL,
    valeur              REAL NOT NULL,
    unite               TEXT,
    tol_min             REAL,
    tol_max             REAL,
    anomalie_injectee   INTEGER,
    FOREIGN KEY (equipement) REFERENCES equipements(equipement)
)
""")

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"Le fichier {CSV_PATH} est introuvable."
    )

df = pd.read_csv(CSV_PATH)
df["anomalie_injectee"] = df["anomalie_injectee"].astype(int)
df.to_sql("mesures", conn, if_exists="append", index=False)

cur.execute("CREATE INDEX idx_mesures_equip_param ON mesures(equipement, parametre)")
cur.execute("CREATE INDEX idx_mesures_timestamp ON mesures(timestamp)")

conn.commit()

# ---------------------------------------------------------------------------
# Vérification
# ---------------------------------------------------------------------------
print("Base créée :", DB_PATH)
print()
print("Table equipements :")
for row in cur.execute("SELECT * FROM equipements"):
    print(" ", row)

print()
cur.execute("SELECT COUNT(*) FROM mesures")
print("Nb lignes table mesures :", cur.fetchone()[0])

print()
print("Répartition par équipement :")
for row in cur.execute("SELECT equipement, COUNT(*), COUNT(DISTINCT parametre) FROM mesures GROUP BY equipement"):
    print(" ", row)

print()
print("="*60)
print("BASE SQLITE CRÉÉE AVEC SUCCÈS")
print("="*60)

print(f"Equipements : 3")
print(f"Paramètres : {df['parametre'].nunique()}")
print(f"Mesures : {len(df)}")
print(f"Anomalies injectées : {df['anomalie_injectee'].sum()}")

cur.execute("""
CREATE VIEW vue_supervision AS
SELECT
    m.timestamp,
    m.equipement,
    e.domaine_cns,
    e.frequence,
    m.parametre,
    m.valeur,
    m.unite,
    m.tol_min,
    m.tol_max,
    m.anomalie_injectee
FROM mesures m
JOIN equipements e
ON m.equipement = e.equipement;
""")

conn.commit()
conn.close()
