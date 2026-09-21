"""
01_simulation_donnees.py
Simulation des données de supervision ILS/DME (LOC, GP, DME) — piste 13/31, Aéroport Fès-Saïs.

Source des paramètres et tolérances : Relevé Semestriel ILS/DME
Référence: FEZ.PS08.E.422/01 (document fourni par le jury).

Toutes les bornes min/max ci-dessous sont reprises EXACTEMENT du PDF, sans modification.
Aucun paramètre inventé.

Période simulée : 60 jours, échantillonnage horaire (1 440 points par paramètre/équipement).

Comportement normal : valeur = point médian de la tolérance + bruit gaussien réaliste.

Anomalie injectée (corrigée) : deux phases distinctes, pour un scénario réaliste où les
anomalies restent des événements RARES sur l'historique complet (conforme aux observations
opérationnelles réelles rapportées par le jury) :

  1. Phase de TENDANCE (J-15 à J-2) : dérive lente et progressive vers une des bornes de
     tolérance, mais qui RESTE DANS LA TOLÉRANCE (clip strict). Elle sert à démontrer la
     détection de tendance (Mann-Kendall) — un signal précurseur, pas encore une anomalie.

  2. Phase d'ANOMALIE RÉELLE (J-2 à J-0, dernières 48h) : la dérive continue et sort
     effectivement de la tolérance — scénario réaliste d'une panne naissante, tout juste
     détectable au moment de la consultation du dashboard.

Sur les 60 jours simulés, seules les ~48 dernières heures sortent réellement de tolérance :
le taux d'anomalies réelles reste donc faible sur l'historique complet (~1-2 %), avec une
alarme concentrée et clairement identifiable en fin de période — cohérent avec le comportement
observé en exploitation réelle.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ---------------------------------------------------------------------------
# 1. Paramètres et tolérances EXACTS du PDF (Relevé Semestriel ILS/DME)
# ---------------------------------------------------------------------------

PARAMETRES = {
    "LOC": {
        "CSB_DIR_Course_W":     {"min": 15,      "max": 26,      "unite": "W"},
        "SBO_DIR_Course_W":     {"min": 0.1,     "max": 2,       "unite": "W"},
        "CSB_DIR_Clearance_W":  {"min": 15,      "max": 26,      "unite": "W"},
        "SBO_DIR_Clearance_W":  {"min": 0.04,    "max": 1,       "unite": "W"},
        "CL_DDM_uA":            {"min": -10,     "max": 10,      "unite": "µA"},
        "CL_SDM_pct":           {"min": 36,      "max": 44,      "unite": "%"},
        "CL_RF_dB":             {"min": -1,      "max": 1,       "unite": "dB"},
        "DS_DDM_uA":            {"min": -25,     "max": 25,      "unite": "µA"},
        "DS_SDM_pct":           {"min": 20,      "max": 60,      "unite": "%"},
        "DS_RF_dB":             {"min": -4,      "max": 4,       "unite": "dB"},
        "NF_DDM_uA":            {"min": -10,     "max": 10,      "unite": "µA"},
        "CLR_DDM_uA":           {"min": -38,     "max": 38,      "unite": "µA"},
        "CLR_SDM_pct":          {"min": 36,      "max": 44,      "unite": "%"},
        "Diff_Freq_kHz":        {"min": 6,       "max": 14,      "unite": "kHz"},
        "Freq_Porteuse_MHz":    {"min": 108.07323, "max": 108.12671, "unite": "MHz"},
        "Tension_Batterie_V":   {"min": 23,      "max": 28,      "unite": "V"},
    },
    "GP": {
        "CSB_DIR_Course_W":     {"min": 4,       "max": 9,       "unite": "W"},
        "SBO_DIR_Course_W":     {"min": 0.04,    "max": 1,       "unite": "W"},
        "CSB_DIR_Clearance_W":  {"min": 0.04,    "max": 1,       "unite": "W"},
        "CL_DDM_uA":            {"min": -35,     "max": 35,      "unite": "µA"},
        "CL_SDM_pct":           {"min": 75,      "max": 85,      "unite": "%"},
        "CL_RF_dB":             {"min": -1,      "max": 1,       "unite": "dB"},
        "DS_DDM_uA":            {"min": -18,     "max": 18,      "unite": "µA"},
        "DS_SDM_pct":           {"min": 60,      "max": 100,     "unite": "%"},
        "DS_RF_dB":             {"min": -4,      "max": 4,       "unite": "dB"},
        "NF_DDM_uA":            {"min": -45,     "max": 45,      "unite": "µA"},
        "CLR_DDM_uA":           {"min": -45,     "max": 45,      "unite": "µA"},
        "CLR_SDM_pct":          {"min": 75,      "max": 85,      "unite": "%"},
        "Diff_Freq_kHz":        {"min": 10.5,    "max": 19.5,    "unite": "kHz"},
        "Freq_Porteuse_MHz":    {"min": 344.62311, "max": 344.77689, "unite": "MHz"},
        "Tension_Batterie_V":   {"min": 23,      "max": 28,      "unite": "V"},
    },
    "DME": {
        "Retard_Systematique_us": {"min": 49.1,  "max": 50.1,    "unite": "µs"},
        "Code_us":                {"min": 11.75, "max": 12.25,   "unite": "µs"},
        # PDF : max = "N/A" (aucune borne max définie). Traité en tolérance UNILATÉRALE :
        # seul le seuil min (50 W) est une exigence réelle du document. Pas de plafond inventé.
        "Puissance_Rayonnee_W":   {"min": 50,    "max": None,   "unite": "W"},
        # PDF : max = "N/A". Ici 100% n'est PAS une valeur du PDF : c'est le plafond physique
        # d'un pourcentage (ne peut mathématiquement pas dépasser 100%). Le seuil réel du
        # document est uniquement le min (70%).
        "Efficacite_Reponse_pct": {"min": 70,    "max": 100,    "unite": "%"},
        "Temps_Montee_us":        {"min": 1.5,   "max": 3,       "unite": "µs"},
        "Temps_Descente_us":      {"min": 1.5,   "max": 3.5,     "unite": "µs"},
        "Largeur_Impulsion_us":   {"min": 3,     "max": 4,       "unite": "µs"},
        "Tension_Batterie_V":     {"min": 23,    "max": 28,      "unite": "V"},
    },
}

# Paramètre choisi pour l'anomalie injectée par équipement (dérive réaliste de dégradation)
PARAM_ANOMALIE = {
    "LOC": "CL_DDM_uA",             # dérive de modulation différentielle -> défaut de calibration typique
    "GP":  "CSB_DIR_Course_W",      # baisse progressive de puissance -> vieillissement émetteur
    "DME": "Retard_Systematique_us" # dérive du retard -> défaut de calibration transpondeur
}

# Paramètres corrélés qui se dégradent légèrement avec la panne principale
PARAM_CORRELES = {
    "LOC": ["CL_SDM_pct", "CL_RF_dB"],
    "GP":  ["CL_SDM_pct", "CL_RF_dB"],
    "DME": ["Temps_Montee_us", "Largeur_Impulsion_us"],
}

# ---------------------------------------------------------------------------
# 2. Génération des séries temporelles
# ---------------------------------------------------------------------------

DUREE_JOURS = 60
FREQ_HEURES = 1
DEBUT = datetime(2026, 1, 1, 0, 0, 0)
N_POINTS = int(DUREE_JOURS * 24 / FREQ_HEURES)
timestamps = [DEBUT + timedelta(hours=i * FREQ_HEURES) for i in range(N_POINTS)]

# --- Fenêtres de dégradation (décalées par équipement, pour un scénario réaliste) ---
# Phase 1 - TENDANCE : dérive lente vers la limite, mais reste dans la tolérance.
# Phase 2 - ANOMALIE RÉELLE : sortie effective de tolérance (panne).
#
# IMPORTANT (réalisme opérationnel) : les 3 équipements ne tombent PAS en panne au
# même moment. En exploitation réelle, avoir 3 équipements de navigation indépendants
# dérivant simultanément serait un scénario catastrophique et improbable. On décale
# donc l'incident de chaque équipement dans le temps :
#   - LOC  : incident survenu et RÉSOLU il y a 25 jours (retour à la normale depuis)
#   - GP   : incident survenu et RÉSOLU il y a 10 jours (retour à la normale depuis)
#   - DME  : incident EN COURS actuellement (panne naissante, tout juste détectée)
# Résultat : à un instant donné (ex: "aujourd'hui"), au plus UN seul équipement est
# anormal — jamais les 3 ensemble — cohérent avec une exploitation réelle où les
# pannes sont des événements rares et indépendants les uns des autres.
JOURS_TENDANCE = 15    # durée totale de la dérive visible (tendance + anomalie)
JOURS_ANOMALIE = 0.5   # dont, sortie réelle de tolérance (12h de panne)

JOURS_AVANT_FIN_INCIDENT = {
    "LOC": 25,   # incident terminé il y a 25 jours
    "GP": 10,    # incident terminé il y a 10 jours
    "DME": 0,    # incident en cours (se termine à la toute fin des données)
}

N_POINTS_TENDANCE = int(JOURS_TENDANCE * 24 / FREQ_HEURES)
N_POINTS_ANOMALIE = int(JOURS_ANOMALIE * 24 / FREQ_HEURES)

lignes = []

for equipement, params in PARAMETRES.items():

    # Position de la fin de l'incident pour CET équipement (décalage temporel propre)
    jours_avant_fin = JOURS_AVANT_FIN_INCIDENT.get(equipement, 0)
    idx_fin_incident = N_POINTS - int(jours_avant_fin * 24 / FREQ_HEURES)
    idx_fin_incident = min(idx_fin_incident, N_POINTS)  # sécurité, ne dépasse pas la fin

    for nom_param, bornes in params.items():
        vmin = bornes["min"]
        vmax = bornes["max"]
        unilateral = vmax is None  # tolérance min seule (PDF: max = "N/A")

        if unilateral:
            # Pas de max réel : on simule une marge d'exploitation réaliste au-dessus du min
            # (ex: puissance rayonnée typiquement 4 à 8% au-dessus du seuil minimal exigé).
            marge_typique = vmin * 0.08
            centre = vmin + marge_typique
            sigma = marge_typique * 0.02
            etendue_reference = marge_typique * 2
        else:
            centre = (vmin + vmax) / 2
            etendue = vmax - vmin
            sigma = etendue * 0.02
            etendue_reference = etendue

        # Bruit gaussien
        bruit = np.random.normal(0, sigma, N_POINTS)

        # Variation journalière très légère
        cycle = 0.01 * etendue_reference * np.sin(np.linspace(0, 8 * np.pi, N_POINTS))

        # Valeur finale
        valeurs = centre + bruit + cycle

        is_anomalie_param = (nom_param == PARAM_ANOMALIE.get(equipement))
        is_param_correle = nom_param in PARAM_CORRELES.get(equipement, [])
        anomalie_flags = np.zeros(N_POINTS, dtype=bool)

        if is_anomalie_param or is_param_correle:
            idx_debut_tendance = idx_fin_incident - N_POINTS_TENDANCE
            idx_debut_anomalie = idx_fin_incident - N_POINTS_ANOMALIE

            # Distance du centre au bord de tolérance le plus proche
            demi_etendue = etendue_reference / 2
            # En fin de fenêtre "anomalie", on dépasse la borne d'une marge réaliste (~15%)
            derive_max = demi_etendue + (etendue_reference * 0.15)
            facteur_intensite = 1.0 if is_anomalie_param else 0.75

            # Le paramètre PRINCIPAL dérive dès la phase de tendance (J-15 par rapport à
            # LA FIN DE SON PROPRE INCIDENT) : signal précurseur visible par Mann-Kendall,
            # mais qui reste dans la tolérance. Les paramètres CORRÉLÉS, eux, restent
            # normaux pendant la tendance et ne dérivent qu'en même temps que la vraie
            # panne (fenêtre courte) : une IA multivariée a besoin de plusieurs paramètres
            # qui bougent ENSEMBLE au même instant pour isoler fiablement l'anomalie.
            idx_debut_derive_pour_ce_param = (
                idx_debut_tendance if is_anomalie_param else idx_debut_anomalie
            )

            for i in range(idx_debut_derive_pour_ce_param, idx_fin_incident):
                progression = (i - idx_debut_tendance) / max(1, (N_POINTS_TENDANCE - 1))
                derive = derive_max * (progression ** 2) * facteur_intensite
                instabilite = np.random.normal(0, sigma * (1 + 3 * progression))
                valeurs[i] += derive + instabilite

                if i < idx_debut_anomalie:
                    # --- Phase TENDANCE : signal précurseur, reste dans la tolérance ---
                    marge_securite = etendue_reference * 0.03  # petite marge pour ne pas raser le bord
                    if unilateral:
                        valeurs[i] = max(valeurs[i], vmin + marge_securite)
                    else:
                        valeurs[i] = min(max(valeurs[i], vmin + marge_securite), vmax - marge_securite)
                    anomalie_flags[i] = False
                else:
                    # --- Phase ANOMALIE RÉELLE : sortie effective de tolérance autorisée ---
                    depasse_max = (not unilateral) and (valeurs[i] > vmax)
                    depasse_min = valeurs[i] < vmin
                    anomalie_flags[i] = bool(depasse_max or depasse_min)

            # Comportement normal AVANT le début de dérive ET APRÈS la fin de l'incident
            # (équipement réparé / revenu en tolérance) : clip strict dans les bornes PDF.
            for i in list(range(0, idx_debut_derive_pour_ce_param)) + list(range(idx_fin_incident, N_POINTS)):
                if unilateral:
                    valeurs[i] = max(valeurs[i], vmin)
                else:
                    valeurs[i] = min(max(valeurs[i], vmin), vmax)
        else:
            # Petite dérive naturelle (calibration), toujours dans les bornes PDF (clip strict)
            valeurs += np.linspace(0, sigma * 0.5, N_POINTS)
            if unilateral:
                valeurs = np.maximum(valeurs, vmin)
            else:
                valeurs = np.clip(valeurs, vmin, vmax)

        for i, t in enumerate(timestamps):
            lignes.append({
                "timestamp": t,
                "equipement": equipement,
                "parametre": nom_param,
                "valeur": round(float(valeurs[i]), 4),
                "unite": bornes["unite"],
                "tol_min": vmin,
                "tol_max": vmax,
                "anomalie_injectee": bool(anomalie_flags[i]),
            })

df = pd.DataFrame(lignes)
df = df.sort_values(["equipement", "parametre", "timestamp"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 3. Export
# ---------------------------------------------------------------------------

sortie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees_simulees_ils_dme.csv")
df.to_csv(sortie, index=False, encoding="utf-8")

print(f"Fichier généré : {sortie}")
print(f"Lignes totales : {len(df)}")
print(f"Période : {timestamps[0]} -> {timestamps[-1]} ({DUREE_JOURS} jours, pas horaire)")
print(f"Équipements : {list(PARAMETRES.keys())}")
print(f"Nb paramètres par équipement : {[ (e, len(p)) for e, p in PARAMETRES.items() ]}")
print(f"Paramètres avec anomalie injectée : {PARAM_ANOMALIE}")
print(f"Nb points hors-tolérance générés (anomalie) : {df['anomalie_injectee'].sum()}")
print()
print(df.groupby(["equipement", "parametre"])["anomalie_injectee"].sum()[lambda s: s > 0])

print("\n========================")
print("RÉSUMÉ DE LA SIMULATION")
print("========================")
print(f"Nombre total de mesures : {len(df)}")
print(f"Nombre total d'anomalies : {df['anomalie_injectee'].sum()}")

for eq in PARAMETRES.keys():
    nb = df[(df["equipement"] == eq) & (df["anomalie_injectee"])].shape[0]
    print(f"{eq} : {nb} anomalies")