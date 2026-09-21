"""
04_preparation_donnees.py
Préparation des données — Système ILS/DME (LOC, GP, DME).

Rôle :
- Charger les données brutes depuis la base SQLite (table `mesures`)
- Nettoyer (doublons, valeurs manquantes, cohérence des timestamps)
- Mettre en forme en matrices par équipement (une colonne par paramètre)
- Exporter les données préparées pour les étapes suivantes (analyse de tendance, détection)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from ia_engine import charger_donnees, mettre_en_forme_matrice, EQUIPEMENTS

DOSSIER_SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees_preparees")
os.makedirs(DOSSIER_SORTIE, exist_ok=True)


def nettoyer_donnees(df):
    """Nettoyage standard : doublons, valeurs manquantes, types."""
    n_avant = len(df)

    # Doublons exacts (même équipement/paramètre/timestamp)
    df = df.drop_duplicates(subset=["equipement", "parametre", "timestamp"])

    # Valeurs manquantes sur la mesure elle-même -> on ne peut pas les garder
    df = df.dropna(subset=["valeur"])

    # Cohérence de type
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["valeur"] = df["valeur"].astype(float)

    n_apres = len(df)
    n_retires = n_avant - n_apres

    return df, n_retires


def preparer_equipement(equipement):
    df_brut = charger_donnees(equipement)
    df_propre, n_retires = nettoyer_donnees(df_brut)

    matrice = mettre_en_forme_matrice(df_propre, equipement)

    # Valeurs manquantes dans la matrice (paramètre non mesuré à un instant donné)
    # -> interpolation linéaire temporelle (méthode standard pour séries de capteurs),
    # puis remplissage résiduel par la dernière valeur connue si besoin en début de série.
    n_manquants_avant = matrice.isna().sum().sum()
    matrice = matrice.interpolate(method="linear").bfill()
    n_manquants_apres = matrice.isna().sum().sum()

    chemin_csv = os.path.join(DOSSIER_SORTIE, f"donnees_preparees_{equipement}.csv")
    matrice.to_csv(chemin_csv)

    return {
        "equipement": equipement,
        "lignes_brutes_retirees": n_retires,
        "observations": len(matrice),
        "parametres": matrice.shape[1],
        "valeurs_interpolees": int(n_manquants_avant - n_manquants_apres) if n_manquants_apres == 0 else int(n_manquants_avant),
        "fichier": chemin_csv,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("PRÉPARATION DES DONNÉES — Système ILS/DME (LOC, GP, DME)")
    print("=" * 70)

    resumes = []
    for eq in EQUIPEMENTS:
        resume = preparer_equipement(eq)
        resumes.append(resume)
        print(f"\nÉquipement : {resume['equipement']}")
        print(f"  Lignes brutes retirées (doublons/valeurs manquantes) : {resume['lignes_brutes_retirees']}")
        print(f"  Observations après préparation : {resume['observations']}")
        print(f"  Paramètres : {resume['parametres']}")
        print(f"  Valeurs interpolées : {resume['valeurs_interpolees']}")
        print(f"  Export : {resume['fichier']}")

    print("\nPréparation terminée pour les 3 équipements.")