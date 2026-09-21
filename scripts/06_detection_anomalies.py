"""
06_detection_anomalies.py
Détection d'anomalies — Système ILS/DME (LOC, GP, DME).

Applique les modèles Isolation Forest (via ia_engine) sur les 3 équipements,
identifie le(s) paramètre(s) responsable(s) de chaque anomalie détectée
(le paramètre le plus éloigné de sa moyenne, en écart-type, au moment de l'anomalie),
et enregistre les résultats dans la base SQLite (table `anomalies_detectees`)
pour consultation par le dashboard et le rapport.

Correction : une "anomalie détectée" est définie par la prédiction binaire réelle
d'Isolation Forest (colonne `est_anomalie`, calibrée par `contamination` ≈ 3%),
et non par `niveau_risque ∈ {Critique, Élevé}`. Ce dernier est un percentile
(P10/P30) calculé sur TOUTES les observations : il classe TOUJOURS 30% des
données comme "Critique + Élevé", qu'il y ait ou non une vraie anomalie. Utiliser
`niveau_risque` comme critère de détection gonfle artificiellement le nombre
d'anomalies (ex: 432/1440 = 30% pile) et fausse toute mesure de performance.
`niveau_risque` reste utile *après coup*, pour prioriser les anomalies déjà
détectées (Critique = les plus sévères parmi elles), pas pour les détecter.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
import numpy as np
from ia_engine import charger_donnees, mettre_en_forme_matrice, scorer_donnees, EQUIPEMENTS, DB_PATH


def identifier_parametre_responsable(matrice, timestamp):
    """
    Pour un timestamp donné, identifie le paramètre le plus anormal
    (le plus grand écart en valeur absolue par rapport à sa moyenne, en unités d'écart-type).
    """
    ligne = matrice.loc[timestamp]
    z_scores = (ligne - matrice.mean()) / matrice.std()
    parametre_responsable = z_scores.abs().idxmax()
    z_max = z_scores[parametre_responsable]
    return parametre_responsable, round(float(z_max), 2)


def detecter_equipement(equipement):
    df = charger_donnees(equipement)
    matrice = mettre_en_forme_matrice(df, equipement)
    resultat = scorer_donnees(equipement, matrice)

    # Critère de détection = prédiction réelle d'Isolation Forest (est_anomalie),
    # PAS niveau_risque (qui est un percentile toujours égal à 30% des données).
    anomalies = resultat[resultat["est_anomalie"] == True].copy()

    lignes = []
    for timestamp in anomalies.index:
        parametre_resp, z_max = identifier_parametre_responsable(matrice, timestamp)
        lignes.append({
            "timestamp": timestamp,
            "equipement": equipement,
            "niveau_risque": anomalies.loc[timestamp, "niveau_risque"],
            "score_anomalie": round(float(anomalies.loc[timestamp, "score_anomalie"]), 4),
            "parametre_responsable": parametre_resp,
            "ecart_type_z": z_max,
        })

    return pd.DataFrame(lignes)


if __name__ == "__main__":
    print("=" * 70)
    print("DÉTECTION D'ANOMALIES — Système ILS/DME (LOC, GP, DME)")
    print("=" * 70)

    toutes_anomalies = []
    for eq in EQUIPEMENTS:
        df_anom = detecter_equipement(eq)
        toutes_anomalies.append(df_anom)
        print(f"\nÉquipement : {eq}")
        print(f"  Anomalies détectées (Isolation Forest) : {len(df_anom)}")
        if len(df_anom) > 0:
            print(f"  Paramètre(s) responsable(s) le plus souvent :")
            print("   ", df_anom["parametre_responsable"].value_counts().head(3).to_dict())
        else:
            print("  Aucune anomalie détectée sur cet équipement.")

    df_final = pd.concat(toutes_anomalies, ignore_index=True)
    df_final["timestamp"] = df_final["timestamp"].astype(str)

    # Sauvegarde dans la base SQLite
    conn = sqlite3.connect(DB_PATH)
    df_final.to_sql("anomalies_detectees", conn, if_exists="replace", index=False)
    conn.close()

    print(f"\nTotal anomalies enregistrées : {len(df_final)}")
    print(f"Table 'anomalies_detectees' créée dans {DB_PATH}")