"""
05_analyse_tendance.py
Analyse de tendance — Système ILS/DME (LOC, GP, DME).

Pour chaque paramètre de chaque équipement :
- calcule la tendance (régression linéaire dans le temps)
- teste la significativité statistique de cette évolution (test de Mann-Kendall,
  robuste aux données non-normales et aux séries temporelles — cohérent avec la
  démarche "test de significativité basé sur les statistiques" utilisée précédemment)
- signale les paramètres dont l'évolution est statistiquement significative
  (candidats à une dérive matérielle réelle, à surveiller en priorité)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from ia_engine import EQUIPEMENTS

DOSSIER_DONNEES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees_preparees")
SEUIL_SIGNIFICATIVITE = 0.05  # seuil classique (p-value < 0.05)


def mann_kendall(serie):
    """
    Test de Mann-Kendall (non-paramétrique) : détecte une tendance monotone
    (croissante ou décroissante) dans une série temporelle, sans supposer
    une distribution particulière des données — adapté aux mesures de capteurs.
    Retourne (statistique_S, p_value_approx, tendance).
    """
    x = serie.values
    n = len(x)
    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1:] - x[k]))

    # Variance de S (approximation standard, sans correction d'ex-aequo pour simplicité)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0

    from scipy.stats import norm
    p_value = 2 * (1 - norm.cdf(abs(z)))

    if p_value < SEUIL_SIGNIFICATIVITE:
        tendance = "Croissante" if s > 0 else "Décroissante"
    else:
        tendance = "Aucune tendance significative"

    return s, p_value, tendance


def analyser_equipement(equipement):
    chemin = os.path.join(DOSSIER_DONNEES, f"donnees_preparees_{equipement}.csv")
    matrice = pd.read_csv(chemin, index_col=0, parse_dates=True)

    resultats = []
    for parametre in matrice.columns:
        serie = matrice[parametre]
        pente = np.polyfit(range(len(serie)), serie.values, 1)[0]
        s, p_value, tendance = mann_kendall(serie)

        resultats.append({
            "equipement": equipement,
            "parametre": parametre,
            "pente_par_observation": round(pente, 6),
            "p_value": round(p_value, 5),
            "tendance": tendance,
            "significatif": p_value < SEUIL_SIGNIFICATIVITE,
        })

    return pd.DataFrame(resultats)


if __name__ == "__main__":
    print("=" * 70)
    print("ANALYSE DE TENDANCE — Système ILS/DME (LOC, GP, DME)")
    print(f"Test de Mann-Kendall, seuil de significativité p < {SEUIL_SIGNIFICATIVITE}")
    print("=" * 70)

    tous_resultats = []
    for eq in EQUIPEMENTS:
        res = analyser_equipement(eq)
        tous_resultats.append(res)

    df_final = pd.concat(tous_resultats, ignore_index=True)

    chemin_sortie = os.path.join(DOSSIER_DONNEES, "analyse_tendance.csv")
    df_final.to_csv(chemin_sortie, index=False)

    print("\nParamètres avec évolution statistiquement significative :\n")
    significatifs = df_final[df_final["significatif"]].sort_values("p_value")
    print(significatifs.to_string(index=False))

    print(f"\nTotal paramètres analysés : {len(df_final)}")
    print(f"Paramètres avec tendance significative : {df_final['significatif'].sum()}")
    print(f"Export complet : {chemin_sortie}")