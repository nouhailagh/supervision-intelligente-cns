"""
ia_engine.py
==========================================================
Module IA centralisé — Supervision ILS/DME
Équipements : LOC, GP, DME

Fonctions principales :
- Chargement des données depuis SQLite
- Transformation des mesures en matrice
- Entraînement Isolation Forest
- Chargement des modèles
- Vérification des tolérances
- Scoring des données du projet
- Scoring des données réelles importées
"""

import os
import sqlite3

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ==========================================================
# CONFIGURATION
# ==========================================================

# Chemin racine du projet
DOSSIER_IA = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PROJET = os.path.dirname(DOSSIER_IA)

# Base SQLite utilisée par le projet
DB_PATH = os.path.join(
    DOSSIER_PROJET,
    "data",
    "supervision_ils_dme.db"
)

# Dossier des modèles
MODELS_DIR = os.path.join(
    DOSSIER_IA,
    "modeles"
)

os.makedirs(MODELS_DIR, exist_ok=True)


# ==========================================================
# PARAMÈTRES IA
# ==========================================================

EQUIPEMENTS = [
    "LOC",
    "GP",
    "DME",
]

CONTAMINATION = 0.02


# ==========================================================
# VÉRIFICATION DE LA BASE
# ==========================================================

def verifier_base():
    """
    Vérifie que la base SQLite existe et contient
    les tables nécessaires.
    """

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Base SQLite introuvable :\n{DB_PATH}\n\n"
            "Exécutez d'abord 02_creation_base_donnees.py."
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """,
            conn
        )

        noms_tables = set(tables["name"].tolist())

        if "mesures" not in noms_tables:
            raise RuntimeError(
                "La base SQLite existe mais la table 'mesures' "
                "n'existe pas.\n\n"
                f"Base utilisée : {DB_PATH}\n\n"
                "Recréez la base avec 02_creation_base_donnees.py."
            )

        if "equipements" not in noms_tables:
            raise RuntimeError(
                "La table 'equipements' est absente de la base SQLite."
            )

    finally:
        conn.close()


# ==========================================================
# CHARGEMENT DES DONNÉES PROJET
# ==========================================================

def charger_donnees(equipement=None):
    """
    Charge les données depuis la base SQLite.

    Paramètres
    ----------
    equipement : str ou None
        LOC, GP, DME ou None pour tous les équipements.

    Retour
    ------
    pandas.DataFrame
    """

    verifier_base()

    conn = sqlite3.connect(DB_PATH)

    try:

        if equipement is not None:

            equipement = str(equipement).upper()

            if equipement not in EQUIPEMENTS:
                raise ValueError(
                    f"Équipement inconnu : {equipement}. "
                    f"Valeurs autorisées : {EQUIPEMENTS}"
                )

            query = """
                SELECT *
                FROM mesures
                WHERE equipement = ?
                ORDER BY timestamp
            """

            df = pd.read_sql_query(
                query,
                conn,
                params=(equipement,)
            )

        else:

            query = """
                SELECT *
                FROM mesures
                ORDER BY equipement, timestamp
            """

            df = pd.read_sql_query(
                query,
                conn
            )

    finally:
        conn.close()

    if df.empty:
        return df

    # Conversion timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Conversion valeur
    if "valeur" in df.columns:
        df["valeur"] = pd.to_numeric(
            df["valeur"],
            errors="coerce"
        )

    return df


# ==========================================================
# MISE EN FORME DES DONNÉES
# ==========================================================

def mettre_en_forme_matrice(df, equipement):
    """
    Transforme les données longues :

        timestamp | equipement | parametre | valeur

    en matrice large :

        timestamp | param1 | param2 | param3 | ...

    Une ligne correspond à un instant de mesure.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    equipement = str(equipement).upper()

    df_eq = df[
        df["equipement"]
        .astype(str)
        .str.upper()
        == equipement
    ].copy()

    if df_eq.empty:
        return pd.DataFrame()

    # Nettoyage minimal
    df_eq["timestamp"] = pd.to_datetime(
        df_eq["timestamp"],
        errors="coerce"
    )

    df_eq["valeur"] = pd.to_numeric(
        df_eq["valeur"],
        errors="coerce"
    )

    df_eq = df_eq.dropna(
        subset=[
            "timestamp",
            "parametre",
            "valeur",
        ]
    )

    if df_eq.empty:
        return pd.DataFrame()

    # Transformation longue -> large
    matrice = df_eq.pivot_table(
        index="timestamp",
        columns="parametre",
        values="valeur",
        aggfunc="mean"
    )

    matrice = matrice.sort_index()

    return matrice


# ==========================================================
# ENTRAÎNEMENT D'UN MODÈLE
# ==========================================================

def entrainer_modele(
    equipement,
    contamination=CONTAMINATION
):
    """
    Entraîne un Isolation Forest pour un équipement.

    Le modèle est entraîné uniquement sur les données
    disponibles dans la base du projet.
    """

    equipement = str(equipement).upper()

    if equipement not in EQUIPEMENTS:
        raise ValueError(
            f"Équipement inconnu : {equipement}"
        )

    # Chargement des données projet
    df = charger_donnees(equipement)

    if df.empty:
        raise ValueError(
            f"Aucune donnée disponible pour {equipement}."
        )

    # Matrice multivariée
    matrice = mettre_en_forme_matrice(
        df,
        equipement
    )

    if matrice.empty:
        raise ValueError(
            f"Impossible de construire la matrice pour {equipement}."
        )

    # Suppression des lignes incomplètes
    matrice = matrice.dropna()

    if len(matrice) < 10:
        raise ValueError(
            f"Pas assez d'observations pour entraîner le modèle {equipement}."
        )

    # ------------------------------------------------------
    # Séparation Train / Test
    # ------------------------------------------------------

    n_train = int(len(matrice) * 0.70)

    # Sécurité
    n_train = max(
        n_train,
        2
    )

    matrice_train = matrice.iloc[:n_train].copy()

    # ------------------------------------------------------
    # Standardisation
    # ------------------------------------------------------

    scaler = StandardScaler()

    train_norm = scaler.fit_transform(
        matrice_train
    )

    # ------------------------------------------------------
    # Isolation Forest
    # ------------------------------------------------------

    modele = IsolationForest(
        n_estimators=300,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )

    modele.fit(train_norm)

    # ------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------

    chemin_modele = os.path.join(
        MODELS_DIR,
        f"isolation_forest_{equipement}.joblib"
    )

    joblib.dump(
        {
            "modele": modele,
            "scaler": scaler,
            "colonnes": list(matrice.columns),
        },
        chemin_modele
    )

    return modele, matrice_train


# ==========================================================
# CHARGEMENT D'UN MODÈLE
# ==========================================================

def charger_modele(equipement):
    """
    Charge le modèle Isolation Forest correspondant.

    Si le modèle n'existe pas, il est entraîné automatiquement.
    """

    equipement = str(equipement).upper()

    chemin_modele = os.path.join(
        MODELS_DIR,
        f"isolation_forest_{equipement}.joblib"
    )

    if not os.path.exists(chemin_modele):

        entrainer_modele(
            equipement
        )

    objet = joblib.load(
        chemin_modele
    )

    return (
        objet["modele"],
        objet["scaler"],
        objet["colonnes"],
    )


# ==========================================================
# RÉCUPÉRATION DES TOLÉRANCES
# ==========================================================

def _tolerances_depuis_source(
    df_source,
    equipement
):
    """
    Récupère les tolérances depuis la source utilisée.

    Priorité :
    1. tolérances présentes dans df_source
    2. tolérances de la base SQLite du projet

    Retour :
        DataFrame indexé par paramètre
    """

    equipement = str(equipement).upper()

    # ------------------------------------------------------
    # 1. Tolérances de la source
    # ------------------------------------------------------

    if (
        df_source is not None
        and not df_source.empty
        and "parametre" in df_source.columns
    ):

        colonnes = [
            "parametre",
            "tol_min",
            "tol_max",
        ]

        colonnes_disponibles = [
            c
            for c in colonnes
            if c in df_source.columns
        ]

        if (
            "parametre" in colonnes_disponibles
            and "tol_min" in colonnes_disponibles
            and "tol_max" in colonnes_disponibles
        ):

            tol = (
                df_source[colonnes]
                .copy()
            )

            tol["tol_min"] = pd.to_numeric(
                tol["tol_min"],
                errors="coerce"
            )

            tol["tol_max"] = pd.to_numeric(
                tol["tol_max"],
                errors="coerce"
            )

            tol = (
                tol
                .drop_duplicates("parametre")
                .set_index("parametre")
            )

            # Vérifier si au moins une vraie tolérance existe
            if (
                tol["tol_min"].notna().any()
                or tol["tol_max"].notna().any()
            ):
                return tol

    # ------------------------------------------------------
    # 2. Tolérances de la base du projet
    # ------------------------------------------------------

    df_projet = charger_donnees(
        equipement
    )

    if (
        df_projet.empty
        or "parametre" not in df_projet.columns
    ):
        return pd.DataFrame(
            columns=[
                "tol_min",
                "tol_max",
            ]
        )

    tol = (
        df_projet[
            [
                "parametre",
                "tol_min",
                "tol_max",
            ]
        ]
        .drop_duplicates("parametre")
        .set_index("parametre")
    )

    tol["tol_min"] = pd.to_numeric(
        tol["tol_min"],
        errors="coerce"
    )

    tol["tol_max"] = pd.to_numeric(
        tol["tol_max"],
        errors="coerce"
    )

    return tol


# ==========================================================
# VÉRIFICATION DES TOLÉRANCES
# ==========================================================

def verifier_tolerances(
    matrice,
    equipement,
    df_source=None
):
    """
    Détermine si chaque observation est hors tolérance.

    Retour :
        Series booléenne indexée par timestamp.

    True  = au moins un paramètre hors tolérance
    False = aucun paramètre hors tolérance
    """

    if matrice is None or matrice.empty:
        return pd.Series(
            False,
            index=matrice.index if matrice is not None else None,
            dtype=bool
        )

    tolerances = _tolerances_depuis_source(
        df_source,
        equipement
    )

    hors_tolerance = pd.DataFrame(
        False,
        index=matrice.index,
        columns=matrice.columns,
    )

    if tolerances.empty:
        return pd.Series(
            False,
            index=matrice.index,
            dtype=bool
        )

    for parametre in matrice.columns:

        if parametre not in tolerances.index:
            continue

        vmin = tolerances.loc[
            parametre,
            "tol_min"
        ]

        vmax = tolerances.loc[
            parametre,
            "tol_max"
        ]

        valeurs = matrice[parametre]

        if pd.notna(vmin):

            hors_tolerance[parametre] |= (
                valeurs < vmin
            )

        if pd.notna(vmax):

            hors_tolerance[parametre] |= (
                valeurs > vmax
            )

    return hors_tolerance.any(
        axis=1
    )


# ==========================================================
# SCORING DES DONNÉES
# ==========================================================

def scorer_donnees(
    equipement,
    matrice=None,
    df_source=None
):
    """
    Calcule le résultat IA pour un équipement.

    Sortie :

    - prediction_ia
        1  = normal selon Isolation Forest
       -1  = anomalie selon Isolation Forest

    - score_anomalie
        Score Isolation Forest.

    - hors_tolerance
        True si au moins un paramètre dépasse sa tolérance.

    - est_anomalie
        True uniquement si :
            Isolation Forest détecte une anomalie
            ET
            la mesure est hors tolérance.

    - niveau_risque
        Normal
        Élevé
        Critique
    """

    equipement = str(equipement).upper()

    if equipement not in EQUIPEMENTS:
        raise ValueError(
            f"Équipement inconnu : {equipement}"
        )

    # ------------------------------------------------------
    # Source par défaut
    # ------------------------------------------------------

    if df_source is None:

        df_source = charger_donnees(
            equipement
        )

    if df_source is None or df_source.empty:

        return pd.DataFrame()

    # ------------------------------------------------------
    # Chargement du modèle
    # ------------------------------------------------------

    modele, scaler, colonnes = charger_modele(
        equipement
    )

    # ------------------------------------------------------
    # Construction de la matrice
    # ------------------------------------------------------

    if matrice is None:

        matrice = mettre_en_forme_matrice(
            df_source,
            equipement
        )

    if matrice.empty:

        return pd.DataFrame()

    # ------------------------------------------------------
    # Harmonisation avec les colonnes du modèle
    # ------------------------------------------------------

    # Les données réelles peuvent contenir :
    # - moins de paramètres
    # - plus de paramètres
    #
    # On conserve uniquement les paramètres connus
    # du modèle et on respecte exactement leur ordre.

    matrice = matrice.reindex(
        columns=colonnes
    )

    # ------------------------------------------------------
    # Gestion des valeurs manquantes
    # ------------------------------------------------------

    # Utilisation de l'imputation par médiane du modèle
    # lorsqu'une colonne possède des valeurs manquantes.

    matrice = matrice.copy()

    for colonne in colonnes:

        if matrice[colonne].isna().any():

            # Médiane issue du scaler
            mediane = scaler.mean_[
                colonnes.index(colonne)
            ]

            matrice[colonne] = (
                matrice[colonne]
                .fillna(mediane)
            )

    # ------------------------------------------------------
    # Standardisation
    # ------------------------------------------------------

    matrice_norm = scaler.transform(
        matrice
    )

    # ------------------------------------------------------
    # Prédiction IA
    # ------------------------------------------------------

    predictions = modele.predict(
        matrice_norm
    )

    scores = modele.decision_function(
        matrice_norm
    )

    # ------------------------------------------------------
    # Tolérances
    # ------------------------------------------------------

    hors_tolerance = verifier_tolerances(
        matrice,
        equipement,
        df_source=df_source
    )

    # ------------------------------------------------------
    # Anomalie finale
    # ------------------------------------------------------

    est_anomalie = (
        (predictions == -1)
        & hors_tolerance
    )

    # ------------------------------------------------------
    # Construction du résultat
    # ------------------------------------------------------

    resultat = matrice.copy()

    resultat["prediction_ia"] = predictions

    resultat["score_anomalie"] = scores

    resultat["hors_tolerance"] = (
        hors_tolerance
    )

    resultat["est_anomalie"] = (
        est_anomalie
    )

    # ------------------------------------------------------
    # Niveau de risque
    # ------------------------------------------------------

    def niveau_risque(row):

        if row["est_anomalie"]:
            return "Critique"

        if row["prediction_ia"] == -1:
            return "Élevé"

        return "Normal"

    resultat["niveau_risque"] = resultat.apply(
        niveau_risque,
        axis=1
    )

    return resultat


# ==========================================================
# ENTRAÎNEMENT DE TOUS LES MODÈLES
# ==========================================================

def entrainer_tous_les_modeles():
    """
    Entraîne un modèle pour chacun des trois équipements.
    """

    resultats = {}

    for equipement in EQUIPEMENTS:

        modele, matrice = entrainer_modele(
            equipement
        )

        resultats[equipement] = {
            "n_observations": len(matrice),
            "n_parametres": matrice.shape[1],
            "parametres": list(matrice.columns),
        }

        print(
            f"[OK] Modèle {equipement} entraîné : "
            f"{len(matrice)} observations, "
            f"{matrice.shape[1]} paramètres."
        )

    return resultats


# ==========================================================
# TEST DIRECT DU MODULE
# ==========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TEST IA ENGINE")
    print("=" * 60)

    print()
    print("Base utilisée :")
    print(DB_PATH)

    print()
    print("Vérification de la base...")

    verifier_base()

    print("[OK] Base SQLite valide.")

    print()
    print("Entraînement des modèles...")

    entrainer_tous_les_modeles()

    print()
    print("=" * 60)
    print("IA ENGINE TERMINÉ AVEC SUCCÈS")
    print("=" * 60)

