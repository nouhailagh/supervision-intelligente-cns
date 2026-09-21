"""
07_evaluation_modele.py
Évalue chaque modèle Isolation Forest (LOC, GP, DME) contre les anomalies injectées
lors de la simulation (colonne anomalie_injectee de la base).

Corrections apportées :
1. On NE REDÉFINIT PLUS `est_anomalie` à partir de `niveau_risque` (Critique/Élevé).
   Cette colonne existe déjà correctement dans `resultat` (issue de `scorer_donnees()`
   dans ia_engine.py) : c'est la vraie prédiction binaire d'Isolation Forest, calibrée
   par `contamination` (~3%). La redéfinir via niveau_risque classait TOUJOURS 30% des
   données comme "anomalie" (percentile P10+P30), quelle que soit la réalité — d'où une
   precision artificiellement écrasée (~0.02) et des comptes d'anomalies gonflés.
2. Le bloc de diagnostic/affichage était désindenté en dehors de la boucle
   `for equipement in EQUIPEMENTS`, donc il ne s'exécutait qu'une seule fois après la
   boucle, avec les variables de la DERNIÈRE itération (DME) — LOC et GP n'étaient
   jamais affichés. Corrigé : tout le bloc est maintenant à l'intérieur de la boucle.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ia_engine import charger_donnees, mettre_en_forme_matrice, scorer_donnees, EQUIPEMENTS
import pandas as pd

print("=" * 70)
print("ÉVALUATION DES MODÈLES — Système ILS/DME (LOC, GP, DME)")
print("=" * 70)

for equipement in EQUIPEMENTS:
    df = charger_donnees(equipement)

    # Une ligne (timestamp) est considérée comme anomalie réelle si AU MOINS UN paramètre
    # a une anomalie_injectee=1 à ce timestamp
    verite_terrain = df.groupby("timestamp")["anomalie_injectee"].max().astype(bool)

    resultat = scorer_donnees(equipement)
    resultat = resultat.join(verite_terrain.rename("verite_terrain"))

    # est_anomalie est DÉJÀ dans resultat (prédiction Isolation Forest réelle,
    # calibrée par contamination) — on ne la redéfinit pas ici.

    vp = ((resultat["est_anomalie"]) & (resultat["verite_terrain"])).sum()
    fn = ((~resultat["est_anomalie"]) & (resultat["verite_terrain"])).sum()
    fp = ((resultat["est_anomalie"]) & (~resultat["verite_terrain"])).sum()
    vn = ((~resultat["est_anomalie"]) & (~resultat["verite_terrain"])).sum()

    recall = vp / (vp + fn) if (vp + fn) > 0 else float("nan")
    precision = vp / (vp + fp) if (vp + fp) > 0 else float("nan")

    print(f"\nÉquipement : {equipement}")
    print(f"  Anomalies réelles (injectées)   : {resultat['verite_terrain'].sum()}")
    print(f"  Anomalies détectées (modèle)    : {resultat['est_anomalie'].sum()}")
    print(f"  Vrais positifs / Faux négatifs  : {vp} / {fn}")
    print(f"  Faux positifs / Vrais négatifs  : {fp} / {vn}")
    print(f"  Recall (sensibilité)            : {recall:.2f}")
    print(f"  Precision                       : {precision:.2f}")
    print(f"  Répartition niveaux de risque   :")
    print("    " + resultat["niveau_risque"].value_counts().to_string().replace("\n", "\n    "))

    # ==========================================================
    # Diagnostic des anomalies manquées (à l'intérieur de la boucle)
    # ==========================================================

    if resultat["verite_terrain"].sum() > 0:

        print("\n  Diagnostic :")

        detectees = resultat[resultat["est_anomalie"] & resultat["verite_terrain"]]
        manquees = resultat[(~resultat["est_anomalie"]) & resultat["verite_terrain"]]

        print(f"  VP : {len(detectees)}")
        print(f"  FN : {len(manquees)}")

        if len(detectees) > 0:
            print(f"  Score moyen des VP : {detectees['score_anomalie'].mean():.4f}")

        if len(manquees) > 0:
            print(f"  Score moyen des FN : {manquees['score_anomalie'].mean():.4f}")
    else:
        print("\n  Diagnostic : aucune anomalie réelle injectée pour cet équipement sur la période.")