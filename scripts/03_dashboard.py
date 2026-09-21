# ==========================================================
# DASHBOARD ILS / DME
# Aéroport Fès-Saïss - ONDA
# Version corrigée : source des données dans la sidebar
# ==========================================================

import os
import sys
import io
import base64

import pandas as pd
import streamlit as st

import plotly.graph_objects as go
from datetime import datetime

# ----------------------------------------------------------
# permettre l'import des fichiers du projet
# ----------------------------------------------------------

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ia_engine import (
    charger_donnees,
    scorer_donnees,
    EQUIPEMENTS,
)

# ==========================================================
# CONFIGURATION STREAMLIT
# ==========================================================

st.set_page_config(
    page_title="Supervision Intelligente ILS/DME",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================
# CHEMINS DES IMAGES
# ==========================================================

DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
DOSSIER_PROJET = os.path.dirname(DOSSIER_SCRIPT)

BACKGROUND_PATH = os.path.join(
    DOSSIER_PROJET,
    "assets",
    "background.jpg"
)

LOGO_PATH = os.path.join(
    DOSSIER_PROJET,
    "assets",
    "logo_onda.png"
)


def image_to_base64(path):

    if not os.path.exists(path):
        return ""

    with open(path, "rb") as image:
        return base64.b64encode(
            image.read()
        ).decode()


background = image_to_base64(BACKGROUND_PATH)
logo = image_to_base64(LOGO_PATH)



# ==========================================================
# STYLE CSS GLOBAL
# ==========================================================

st.markdown(
    f"""
<style>

.stApp {{
    background-image:
        linear-gradient(
            rgba(255,255,255,0.10),
            rgba(255,255,255,0.10)
        ),
        url("data:image/jpg;base64,{background}");

    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

section[data-testid="stSidebar"] {{
    background-color: white;
    border-right: 1px solid #D9E2EC;
}}

.block-container {{
    padding-top: 3rem;
    padding-bottom: 1rem;
}}

.section-title {{
    margin-top: 32px;
    margin-bottom: 18px;
    font-size: 21px;
    font-weight: 800;
    color: #173F67;
}}

</style>
""",
    unsafe_allow_html=True,
)


# ==========================================================
# STYLE HEADER
# ==========================================================

st.markdown(
    f"""
<style>

.header-principal {{
    width: 100%;
    min-height: 125px;
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 20px 28px;
    margin-bottom: 22px;

    background: rgba(255,255,255,0.80);

    border: 1px solid rgba(255,255,255,0.90);
    border-radius: 16px;

    box-shadow:
        0 5px 20px rgba(15,43,74,0.08);

    backdrop-filter: blur(4px);
    box-sizing: border-box;
}}

.header-logo {{
    width: 120px;
    min-width: 120px;

    display: flex;
    align-items: center;
    justify-content: center;
}}

.header-logo img {{
    width: 105px;
    height: auto;
    object-fit: contain;
}}

.header-contenu {{
    flex: 1;
}}

.header-organisation {{
    font-size: 15px;
    font-weight: 700;
    color: #173F67;
    margin-bottom: 4px;
}}

.header-titre {{
    font-size: 30px;
    font-weight: 800;
    color: #0B2545;
    line-height: 1.15;
}}

.header-sous-titre {{
    font-size: 13px;
    color: #64748B;
    margin-top: 7px;
}}

.header-date {{
    min-width: 190px;
    text-align: right;
}}

.header-date-label {{
    font-size: 11px;
    color: #64748B;
    text-transform: uppercase;
    font-weight: 700;
}}

.header-date-value {{
    font-size: 14px;
    font-weight: 700;
    color: #173F67;
    margin-top: 4px;
}}

.header-heure {{
    font-size: 11px;
    color: #64748B;
    margin-top: 6px;
}}

</style>
""",
    unsafe_allow_html=True,
)


# ==========================================================
# STYLE GLOBAL — SOUS-TITRES
# ==========================================================

st.markdown(
    """
<style>

.sous-titre-dashboard {
    color: #173F67 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.85);
    margin-top: 2px !important;
    margin-bottom: 8px !important;
}

.texte-secondaire-dashboard {
    color: #28577F !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.9);
}

.description-dashboard {
    color: #365F82 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.95);
}

</style>
""",
    unsafe_allow_html=True,
)


# ==========================================================
# BLOC 1 : ÉTAT PARTAGÉ
# ==========================================================

if "equipement_actif" not in st.session_state:

    st.session_state["equipement_actif"] = EQUIPEMENTS[0]


if "periode_actif" not in st.session_state:

    st.session_state["periode_actif"] = "7j"


PERIODES = {

    "24h": pd.Timedelta(hours=24),

    "7j": pd.Timedelta(days=7),

    "30j": pd.Timedelta(days=30),

    "Tout": None,
}


# ==========================================================
# TERMINOLOGIE DES ÉTATS
# ==========================================================

SEUIL_ALERTE = 5
SEUIL_DEFAUT = 10


def classifier_etat(taux_anomalies):

    if taux_anomalies < SEUIL_ALERTE:

        return "Normal", "normal"

    elif taux_anomalies < SEUIL_DEFAUT:

        return "Alerte", "alerte"

    else:

        return "Défaut", "defaut"


# ==========================================================
# FONCTION FILTRAGE PÉRIODE
# ==========================================================

def filtrer_periode_df(
    df,
    colonne_timestamp,
    date_reference,
    periode
):

    delta = PERIODES.get(periode)

    if delta is None:

        return df

    cutoff = date_reference - delta

    return df[
        df[colonne_timestamp] >= cutoff
    ]


def filtrer_periode_index(
    df,
    date_reference,
    periode
):

    delta = PERIODES.get(periode)

    if delta is None:

        return df

    cutoff = date_reference - delta

    return df[
        df.index >= cutoff
    ]


# ==========================================================
# SOURCE DES DONNÉES — SIDEBAR
# ==========================================================
#
# IMPORTANT :
# Ici on affiche seulement le LOGO + la SOURCE.
#
# Le traitement des données reste dans le BLOC 2.
#
# ==========================================================

with st.sidebar:

    # ------------------------------------------------------
   


    # ------------------------------------------------------
    # IDENTITÉ
    # ------------------------------------------------------

    st.markdown(
        """
        <h3 style="
            color:#0B2545;
            text-align:center;
            margin-bottom:5px;
        ">
            Supervision CNS
        </h3>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        """
        <p style="
            text-align:center;
            color:#64748B;
            font-size:13px;
        ">
            Aéroport Fès-Saïss<br>
            Service CNS — Navigation
        </p>
        """,
        unsafe_allow_html=True,
    )


    st.divider()


    # ------------------------------------------------------
    # SOURCE DES DONNÉES
    # ------------------------------------------------------

    st.markdown(
        """
        <h4 style="color:#0B2545;">
            Source des données
        </h4>
        """,
        unsafe_allow_html=True,
    )


    mode_donnees = st.radio(

        "Source des données",

        [
            "Données du projet",
            "Données réelles"
        ],

        key="mode_donnees",

        label_visibility="collapsed",
    )


    fichier_importe = None


    if mode_donnees == "Données réelles":

        fichier_importe = st.file_uploader(

            "Importer les données réelles",

            type=["csv"],

            key="fichier_donnees_reelles",

            help="Format accepté : CSV",
        )


# ==========================================================
# BLOC 2 : SOURCE DES DONNÉES + SCORING IA
# ==========================================================


# ----------------------------------------------------------
# SOURCE DES DONNÉES
# ----------------------------------------------------------

if mode_donnees == "Données du projet":

    donnees_sources = {

        equipement: charger_donnees(equipement)

        for equipement in EQUIPEMENTS
    }


elif mode_donnees == "Données réelles":

    if fichier_importe is None:

        st.warning(
            "Veuillez importer un fichier CSV contenant les données réelles."
        )

        st.stop()


    try:

        df_import = pd.read_csv(
            fichier_importe
        )


        # --------------------------------------------------
        # Vérification des colonnes
        # --------------------------------------------------

        colonnes_requises = {

            "timestamp",
            "equipement",
            "parametre",
            "valeur",
        }


        colonnes_manquantes = (

            colonnes_requises
            - set(df_import.columns)
        )


        if colonnes_manquantes:

            st.error(

                "Le fichier CSV ne contient pas "
                "les colonnes nécessaires : "
                + ", ".join(
                    sorted(colonnes_manquantes)
                )
            )

            st.stop()


        # --------------------------------------------------
        # Conversion des données
        # --------------------------------------------------

        df_import["timestamp"] = pd.to_datetime(

            df_import["timestamp"],

            errors="coerce"
        )


        df_import["valeur"] = pd.to_numeric(

            df_import["valeur"],

            errors="coerce"
        )


        # --------------------------------------------------
        # Suppression des lignes invalides
        # --------------------------------------------------

        df_import = df_import.dropna(

            subset=[

                "timestamp",
                "equipement",
                "parametre",
                "valeur",
            ]
        )


        if len(df_import) == 0:

            st.error(

                "Aucune donnée exploitable "
                "n'a été trouvée dans le fichier CSV."
            )

            st.stop()


        # --------------------------------------------------
        # Colonnes facultatives
        # --------------------------------------------------

        if "tol_min" not in df_import.columns:

            df_import["tol_min"] = None


        if "tol_max" not in df_import.columns:

            df_import["tol_max"] = None


        if "unite" not in df_import.columns:

            df_import["unite"] = ""


        # --------------------------------------------------
        # Séparation par équipement
        # --------------------------------------------------

        donnees_sources = {}


        for equipement in EQUIPEMENTS:

            df_eq = df_import[

                df_import["equipement"]
                .astype(str)
                .str.upper()
                == equipement

            ].copy()


            donnees_sources[equipement] = df_eq


    except Exception as e:

        st.error(

            f"Erreur lors du traitement "
            f"du fichier CSV : {e}"
        )

        st.stop()


else:

    st.error(
        "Source de données inconnue."
    )

    st.stop()


# ==========================================================
# SCORING IA
# ==========================================================

resultats_complets = {}


for equipement in EQUIPEMENTS:

    df_source = donnees_sources.get(

        equipement,

        pd.DataFrame()
    )


    if len(df_source) == 0:

        resultats_complets[equipement] = (
            pd.DataFrame()
        )


    else:

        resultats_complets[equipement] = (
            scorer_donnees(

                equipement,

                df_source=df_source
            )
        )


# ==========================================================
# DATE DE RÉFÉRENCE
# ==========================================================

toutes_les_donnees = [

    df

    for df in donnees_sources.values()

    if len(df) > 0
]


if len(toutes_les_donnees) == 0:

    st.error(
        "Aucune donnée disponible "
        "pour construire le dashboard."
    )

    st.stop()


df_total = pd.concat(

    toutes_les_donnees,

    ignore_index=True
)


date_maj = pd.to_datetime(

    df_total["timestamp"],

    errors="coerce"
).max()


if pd.isna(date_maj):

    st.error(
        "Impossible de déterminer "
        "la date de dernière mesure."
    )

    st.stop()


if not isinstance(
    date_maj,
    pd.Timestamp
):

    date_maj = pd.to_datetime(
        date_maj
    )


# ==========================================================
# BLOC 3 : SIDEBAR — ÉQUIPEMENT + PÉRIODE
# ==========================================================

INFOS_EQUIPEMENT = {

    "LOC": [

        "Indicatif : LFA",
        "Catégorie : II",
        "Fréquence : 109.7 MHz",
        "Piste : RWY 27",
        "Modèle : NM 7014B4",
    ],

    "GP": [

        "Indicatif : LFA",
        "Catégorie : II",
        "Fréquence : 333.2 MHz",
        "Piste : RWY 27",
        "Modèle : NM 7033B4",
    ],

    "DME": [

        "Indicatif : LFA",
        "Catégorie : II",
        "Fréquence : 34 X",
        "Piste : RWY 27",
        "Modèle : NM LDB-103",
    ],
}


with st.sidebar:

    # ------------------------------------------------------
    # ÉQUIPEMENT
    # ------------------------------------------------------

    st.markdown(
        """
        <h4 style="color:#0B2545;">
            Équipement
        </h4>
        """,
        unsafe_allow_html=True,
    )


    equipement_actif = st.selectbox(

        "Équipement à superviser",

        EQUIPEMENTS,

        index=EQUIPEMENTS.index(
            st.session_state[
                "equipement_actif"
            ]
        ),

        key="selecteur_equipement_maitre",

        label_visibility="collapsed",
    )


    st.session_state[
        "equipement_actif"
    ] = equipement_actif


    st.divider()


    # ------------------------------------------------------
    # PÉRIODE D'ANALYSE
    # ------------------------------------------------------

    st.markdown(
        """
        <h4 style="color:#0B2545;">
            Période d'analyse
        </h4>
        """,
        unsafe_allow_html=True,
    )


    periode_actif = st.radio(

        "Période d'analyse",

        list(PERIODES.keys()),

        index=list(
            PERIODES.keys()
        ).index(
            st.session_state[
                "periode_actif"
            ]
        ),

        key="selecteur_periode_maitre",

        horizontal=True,

        label_visibility="collapsed",
    )


    st.session_state[
        "periode_actif"
    ] = periode_actif


    st.divider()


    # ------------------------------------------------------
    # INFORMATIONS ÉQUIPEMENT
    # ------------------------------------------------------

    st.markdown(
        """
        <h4 style="color:#0B2545;">
            Informations équipement
        </h4>
        """,
        unsafe_allow_html=True,
    )


    for ligne in INFOS_EQUIPEMENT[
        equipement_actif
    ]:

        st.markdown(

            f"""
            <p style="
                color:#334155;
                font-size:14px;
                margin:3px;
            ">
                {ligne}
            </p>
            """,

            unsafe_allow_html=True,
        )


    st.divider()


    # ------------------------------------------------------
    # DERNIÈRE MISE À JOUR
    # ------------------------------------------------------

    st.markdown(

        f"""
        <p style="
            color:#64748B;
            font-size:13px;
        ">
            Dernière mise à jour :<br>
            <b>
                {date_maj.strftime("%d/%m/%Y %H:%M")}
            </b>
        </p>
        """,

        unsafe_allow_html=True,
    )


# ==========================================================
# BLOC 3bis : APPLICATION DE LA PÉRIODE
# ==========================================================

resultats = {

    equipement: filtrer_periode_index(

        resultats_complets[equipement],

        date_maj,

        periode_actif
    )

    for equipement in EQUIPEMENTS
}


nb_anomalies_total = int(

    sum(

        r["est_anomalie"].sum()

        for r in resultats.values()
    )
)


nb_observations_total = int(

    sum(

        len(r)

        for r in resultats.values()
    )
)


taux_anomalies_total = (

    (nb_anomalies_total / nb_observations_total)
    * 100

    if nb_observations_total > 0

    else 0
)
# ==========================================================
# BLOC 4 — HEADER PRINCIPAL
# ==========================================================

heure = datetime.now().strftime("%H:%M")
date_jour = datetime.now().strftime("%d/%m/%Y")

LABELS_PERIODE = {
    "24h": "dernières 24 h",
    "7j": "7 derniers jours",
    "30j": "30 derniers jours",
    "Tout": "historique complet",
}

st.markdown(
f"""
<div class="header-principal">

<div class="header-logo">
        <img src="data:image/png;base64,{logo}">
</div>

<div class="header-contenu">

<div class="header-organisation">
        Office National des Aéroports
</div>

<div class="header-titre">
        Supervision Intelligente des Équipements de Navigation
</div>

<div class="header-sous-titre">
        Systèmes ILS / DME — Aéroport Fès-Saïss
          Surveillance des paramètres · Détection des anomalies · Analyse par IA
</div>

</div>

<div class="header-date">
<div class="header-date-label">
        Période d'analyse
</div>

<div class="header-date-value">
        {LABELS_PERIODE[periode_actif]}
</div>

<div class="header-heure">
        Mise à jour : {date_jour} à {heure}
</div>
</div>

</div>
""",
unsafe_allow_html=True,
)

# ==========================================================
# BLOC 5 — CARTES DES 3 ÉQUIPEMENTS (vue d'ensemble)
# ==========================================================

st.markdown(
    """
    <style>
    .equipements-container { display:flex; gap:18px; width:100%; margin-top:18px; margin-bottom:25px; }
    .equipement-card {
        flex:1; background:rgba(255,255,255,0.96); border-radius:10px;
        border:1px solid #D8E2EC; border-top:4px solid #173F67;
        padding:8px 16px 7px 16px; box-shadow:0 3px 10px rgba(15,52,86,0.08);
        min-height:155px; box-sizing:border-box;
    }
    .equipement-card.actif { border-top:4px solid #D4A017; box-shadow:0 6px 18px rgba(212,160,23,0.25); }
    .equipement-title { font-size:18px; font-weight:800; color:#123B63; margin-bottom:2px; }
    .equipement-type { font-size:12px; color:#6B7C93; margin-bottom:20px; }
    .info-label { font-size:12px; color:#6B7C93; margin-top:12px; margin-bottom:3px; }
    .info-value { font-size:21px; font-weight:700; color:#173F67; margin-bottom:8px; }
    .anomaly-value { font-size:21px; font-weight:800; color:#E74C3C; margin-bottom:8px; }
    .rate-value { font-size:13px; color:#536579; margin-top:4px; }
    .status-normal, .status-alerte, .status-defaut {
        margin-top:18px; padding:9px 12px; border-radius:8px; font-size:13px; font-weight:700;
    }
    .status-normal { background:#E8F7F0; color:#138A55; border:1px solid #BCE8D2; }
    .status-alerte { background:#FFF7D6; color:#A87500; border:1px solid #F2DE91; }
    .status-defaut { background:#FDE8E8; color:#C0392B; border:1px solid #F2B8B5; }
    </style>
    """,
    unsafe_allow_html=True,
)

TYPES_EQUIPEMENTS = {
    "LOC": "Localizer — Système ILS",
    "GP": "Glide Path — Système ILS",
    "DME": "Distance Measuring Equipment",
}

donnees_globales = []
cartes_html = ""

for equipement in EQUIPEMENTS:

    resultat_eq = resultats[equipement]
    nb_observations = len(resultat_eq)
    nb_anomalies = int(resultat_eq["est_anomalie"].sum())

    disponibilite = (
        ((nb_observations - nb_anomalies) / nb_observations) * 100
        if nb_observations > 0
        else 0
    )
    taux_anomalies = (
        (nb_anomalies / nb_observations) * 100 if nb_observations > 0 else 0
    )

    donnees_globales.append(
        {
            "equipement": equipement,
            "total": nb_observations,
            "anomalies": nb_anomalies,
            "disponibilite": disponibilite,
            "taux": taux_anomalies,
        }
    )

    statut, classe_statut = classifier_etat(taux_anomalies)

    classe_carte = "equipement-card actif" if equipement == equipement_actif else "equipement-card"

    cartes_html += f"""
<div class="{classe_carte}">
<div class="equipement-title">{equipement}</div>
<div class="equipement-type">{TYPES_EQUIPEMENTS.get(equipement, "Équipement CNS")}</div>
<div class="info-label">Disponibilité estimée</div>
<div class="info-value">{disponibilite:.1f} %</div>
<div class="info-label">Anomalies détectées</div>
<div class="anomaly-value">{nb_anomalies}</div>
<div class="rate-value">Taux d'anomalies : {taux_anomalies:.1f} %</div>
<div class="status-{classe_statut}">● {statut}</div>
</div>
"""

st.markdown(f'<div class="equipements-container">{cartes_html}</div>', unsafe_allow_html=True)

# ==========================================================
# BLOC 6 — SYNTHÈSE GLOBALE DU SYSTÈME ILS / DME
# ==========================================================

total_observations_systeme = sum(l["total"] for l in donnees_globales)
total_anomalies_systeme = sum(l["anomalies"] for l in donnees_globales)

disponibilite_systeme = (
    ((total_observations_systeme - total_anomalies_systeme) / total_observations_systeme) * 100
    if total_observations_systeme > 0
    else 0
)
taux_anomalies_systeme = (
    (total_anomalies_systeme / total_observations_systeme) * 100
    if total_observations_systeme > 0
    else 0
)

equipement_plus_risque = max(donnees_globales, key=lambda x: x["taux"])
nom_plus_risque = equipement_plus_risque["equipement"]
taux_plus_risque = equipement_plus_risque["taux"]

etat_global, classe_globale = classifier_etat(taux_anomalies_systeme)

st.markdown(
    """
<style>
.global-section { margin-top:25px; margin-bottom:15px; }
.global-card {
    background:rgba(255,255,255,0.97); border:1px solid #D8E2EC; border-radius:12px;
    padding:18px; min-height:125px; box-shadow:0 4px 14px rgba(15,43,74,0.09);
}
.global-label { font-size:12px; font-weight:600; color:#6B7C93; margin-bottom:7px; }
.global-value { font-size:25px; font-weight:800; color:#173F67; }
.global-small { font-size:12px; color:#64748B; margin-top:5px; }
.global-normal { border-left:5px solid #2E8B57; }
.global-alerte { border-left:5px solid #F39C12; }
.global-defaut { border-left:5px solid #C0392B; }
.global-status-normal { color:#138A55; }
.global-status-alerte { color:#A87500; }
.global-status-defaut { color:#C0392B; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">Synthèse globale du système ILS / DME</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""<div class="global-card global-{classe_globale}">
        <div class="global-label">État global du système</div>
        <div class="global-value global-status-{classe_globale}">● {etat_global}</div>
        <div class="global-small">LOC · GP · DME</div></div>""",
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""<div class="global-card">
        <div class="global-label">Disponibilité globale estimée</div>
        <div class="global-value">{disponibilite_systeme:.1f} %</div>
        <div class="global-small">Basée sur les anomalies détectées par l'IA</div></div>""",
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""<div class="global-card">
        <div class="global-label">Anomalies détectées</div>
        <div class="global-value">{total_anomalies_systeme}</div>
        <div class="global-small">Taux global : {taux_anomalies_systeme:.1f} %</div></div>""",
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""<div class="global-card">
        <div class="global-label">Équipement le plus à risque</div>
        <div class="global-value">{nom_plus_risque}</div>
        <div class="global-small">Taux d'anomalies : {taux_plus_risque:.1f} %</div></div>""",
        unsafe_allow_html=True,
    )

# ==========================================================
# BLOC 7 — ÉVOLUTION DES PARAMÈTRES (équipement = sélecteur maître)
## ==========================================================
# BLOC 7 — ÉVOLUTION DES PARAMÈTRES
# ==========================================================

st.markdown(
    """
<div class="titre-section">
        Évolution des paramètres
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="sous-titre-dashboard">
        Équipement sélectionné :
<strong>{equipement_actif}</strong>
<span style="color:#718096;">
            · modifiable dans la barre latérale
</span>
</div>
""",
    unsafe_allow_html=True,
)
# ----------------------------------------------------------
# CHARGEMENT DES DONNÉES
# ----------------------------------------------------------

df_brut_graph = donnees_sources[equipement_actif].copy()

df_brut_graph = filtrer_periode_df(
    df_brut_graph,
    "timestamp",
    date_maj,
    periode_actif,
)

# Résultats IA déjà calculés
resultat_graph = resultats[equipement_actif]

# ----------------------------------------------------------
# LISTE DES PARAMÈTRES
# ----------------------------------------------------------

parametres_disponibles = sorted(
    df_brut_graph["parametre"]
    .dropna()
    .unique()
    .tolist()
)

if len(parametres_disponibles) == 0:

    st.warning(
        f"Aucun paramètre disponible pour {equipement_actif}."
    )

else:

    # ------------------------------------------------------
    # SÉLECTEUR DU PARAMÈTRE
    # ------------------------------------------------------

    parametre_graph = st.selectbox(
        "Paramètre",
        parametres_disponibles,
        key="bloc7_parametre",
    )

    # ------------------------------------------------------
    # DONNÉES DU PARAMÈTRE
    # ------------------------------------------------------

    df_parametre = df_brut_graph[
        df_brut_graph["parametre"] == parametre_graph
    ].copy()

    df_parametre["timestamp"] = pd.to_datetime(
        df_parametre["timestamp"]
    )

    df_parametre = df_parametre.sort_values(
        "timestamp"
    )

    if len(df_parametre) == 0:

        st.warning(
            "Aucune donnée disponible pour ce paramètre."
        )

    else:

        unite = (
            df_parametre["unite"].iloc[0]
            if "unite" in df_parametre.columns
            else ""
        )

        tol_min = (
            df_parametre["tol_min"].iloc[0]
            if "tol_min" in df_parametre.columns
            else None
        )

        tol_max = (
            df_parametre["tol_max"].iloc[0]
            if "tol_max" in df_parametre.columns
            else None
        )

        # ==================================================
        # LES DEUX GRAPHES SUR LA MÊME LIGNE
        # ==================================================

        col_graph, col_score = st.columns([1.6, 1], gap="medium")

        # ==================================================
        # GRAPHE GAUCHE
        # ==================================================

        with col_graph:

            st.markdown(
f"""
<div class="carte-graphe carte-graphe-principale">

<div class="titre-graphe">
            {parametre_graph}
</div>

<div class="description-graphe">
        Évolution temporelle — {equipement_actif}
</div>

</div>
""",
    unsafe_allow_html=True,
)

            # ------------------------------------------------
            # CRÉATION DU GRAPHE PARAMÈTRE
            # ------------------------------------------------

            fig_param = go.Figure()

            fig_param.add_trace(
                go.Scatter(
                    x=df_parametre["timestamp"],
                    y=df_parametre["valeur"],
                    mode="lines",
                    name="Valeur",
                    line=dict(
                        color="#173F67",
                        width=2,
                    ),
                    hovertemplate=(
                        "<b>%{y}</b> "
                        + unite
                        + "<br>%{x}<extra></extra>"
                    ),
                )
            )

            # ------------------------------------------------
            # TOLÉRANCE MINIMUM
            # ------------------------------------------------

            if pd.notna(tol_min):

                fig_param.add_hline(
                    y=float(tol_min),
                    line_dash="dash",
                    line_color="#D64545",
                    line_width=1.5,
                    annotation_text=(
                        f"Min : {tol_min} {unite}"
                    ),
                    annotation_position="bottom left",
                )

            # ------------------------------------------------
            # TOLÉRANCE MAXIMUM
            # ------------------------------------------------

            if pd.notna(tol_max):

                fig_param.add_hline(
                    y=float(tol_max),
                    line_dash="dash",
                    line_color="#D64545",
                    line_width=1.5,
                    annotation_text=(
                        f"Max : {tol_max} {unite}"
                    ),
                    annotation_position="top left",
                )

            # ------------------------------------------------
            # ANOMALIES INJECTÉES
            # ------------------------------------------------

            if "anomalie_injectee" in df_parametre.columns:

                anomalies_param = df_parametre[
                    df_parametre["anomalie_injectee"] == 1
                ]

                if len(anomalies_param) > 0:

                    fig_param.add_trace(
                        go.Scatter(
                            x=anomalies_param["timestamp"],
                            y=anomalies_param["valeur"],
                            mode="markers",
                            name="Anomalies IA",
                            marker=dict(
                                color="#D64545",
                                size=8,
                                symbol="x",
                                line=dict(
                                    width=1.5
                                ),
                            ),
                            hovertemplate=(
                                "<b>Anomalie</b><br>"
                                "%{y} "
                                + unite
                                + "<br>%{x}<extra></extra>"
                            ),
                        )
                    )

            # ------------------------------------------------
            # STYLE DU GRAPHE
            # ------------------------------------------------

            fig_param.update_layout(
                height=320,
                template="plotly_white",
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(
                    l=45,
                    r=20,
                    t=25,
                    b=45,
                ),
                xaxis=dict(
                    title="Date / heure",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                ),
                yaxis=dict(
                    title=unite,
                    showgrid=True,
                    gridcolor="#E5E7EB",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                ),
            )

            st.plotly_chart(
                fig_param,
                width="stretch",
                key=f"graph_param_{equipement_actif}_{parametre_graph}"
            )

        # ==================================================
        # GRAPHE DROIT — SCORE IA
        # ==================================================

        with col_score:

            st.markdown(
"""
<div class="carte-graphe carte-graphe-ia">

<div class="titre-graphe">
        Score d'anomalie IA
</div>

<div class="description-graphe">
        Isolation Forest
</div>

</div>
""",
    unsafe_allow_html=True,
)

            # ------------------------------------------------
            # PRÉPARATION SCORE IA
            # ------------------------------------------------

            resultat_graph = resultat_graph.copy()

            resultat_graph.index = pd.to_datetime(
                resultat_graph.index
            )

            resultat_graph = resultat_graph.sort_index()

            # ------------------------------------------------
            # CRÉATION DU GRAPHE SCORE
            # ------------------------------------------------

            fig_score = go.Figure()

            if (
                "score_anomalie" in resultat_graph.columns
                and "niveau_risque" in resultat_graph.columns
            ):

                for niveau in [
                    "Normal",
                    "Élevé",
                    "Critique",
                ]:

                    sous_df = resultat_graph[
                        resultat_graph["niveau_risque"] == niveau
                    ]

                    if len(sous_df) > 0:

                        couleur = {
                        "Normal": "#219653",
                        "Élevé": "#F2A900",
                        "Critique": "#D64545"    
                        }[niveau]

                        fig_score.add_trace(
                            go.Scatter(
                                x=sous_df.index,
                                y=sous_df["score_anomalie"],
                                mode="markers",
                                name=niveau,
                                marker=dict(
                                    color=couleur,
                                    size=5,
                                ),
                                hovertemplate=(
                                    f"<b>{niveau}</b><br>"
                                    "Score : %{y:.4f}<br>"
                                    "%{x}<extra></extra>"
                                ),
                            )
                        )

            # ------------------------------------------------
            # STYLE DU GRAPHE SCORE
            # ------------------------------------------------

            fig_score.update_layout(
                height=320,
                template="plotly_white",
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(
                    l=45,
                    r=20,
                    t=25,
                    b=45,
                ),
                xaxis=dict(
                    title="Date / heure",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                ),
                yaxis=dict(
                    title="Score IA",
                    showgrid=True,
                    gridcolor="#E5E7EB",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                ),
            )

            st.plotly_chart(
                fig_score,
                width="stretch",
                key=f"graph_score_{equipement_actif}_{parametre_graph}"
            )

        # ==================================================
        # INFORMATIONS SOUS LES DEUX GRAPHES
        # ==================================================

        nb_points = len(df_parametre)

        nb_anomalies_param = (
            int(
                df_parametre["anomalie_injectee"].sum()
            )
            if "anomalie_injectee" in df_parametre.columns
            else 0
        )

        st.markdown(
            f"""
            <div style="
                margin-top:8px;
                padding:10px 15px;
                background:rgba(255,255,255,0.85);
                border-radius:8px;
                color:#5A6472;
                font-size:12px;
                border:1px solid #E2E8F0;
            ">
                <b>{equipement_actif}</b>
                &nbsp;·&nbsp;
                <b>{parametre_graph}</b>
                &nbsp;·&nbsp;
                {nb_points} observations
                &nbsp;·&nbsp;
                {nb_anomalies_param} anomalie(s) injectée(s)
            </div>
            """,

            unsafe_allow_html=True,
        ) 
#BLOC 8 — ANALYSE ET HISTORIQUE DES ANOMALIES (équipement = sélecteur maître)
# ==========================================================

st.markdown(
    """
<div style="
        margin-top:20px;
        margin-bottom:4px;
        font-size:22px;
        font-weight:700;
        color:#173F67;
">
        Analyse et historique
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="sous-titre-dashboard">
        Équipement analysé :
<strong>{equipement_actif}</strong>
</div>
""",
    unsafe_allow_html=True,
)

df_bloc8 = donnees_sources[equipement_actif].copy()
df_bloc8["timestamp"] = pd.to_datetime(df_bloc8["timestamp"], errors="coerce")
df_bloc8 = df_bloc8.dropna(subset=["timestamp"]).sort_values("timestamp")
df_bloc8 = filtrer_periode_df(df_bloc8, "timestamp", date_maj, periode_actif)

# Réutilisation du score IA déjà calculé et filtré en amont (BLOC 3bis)
resultat_bloc8 = resultats[equipement_actif]

# Colonnes de paramètres pour l'affichage du tableau (colonnes hors métadonnées IA)
COLONNES_META_IA = {"prediction", "score_anomalie", "est_anomalie", "niveau_risque"}
colonnes_parametres_bloc8 = [c for c in resultat_bloc8.columns if c not in COLONNES_META_IA]

anomalies_bloc8 = resultat_bloc8[resultat_bloc8["est_anomalie"] == True].copy()
anomalies_bloc8 = anomalies_bloc8.reset_index()
if "timestamp" not in anomalies_bloc8.columns and "index" in anomalies_bloc8.columns:
    anomalies_bloc8 = anomalies_bloc8.rename(columns={"index": "timestamp"})

st.markdown(
    """
<div style="
        background:rgba(255,255,255,0.97);
        border-radius:10px;
        padding:14px 20px;
        border-left:4px solid #173F67;
        border-top:1px solid #E2E8F0;
        border-right:1px solid #E2E8F0;
        border-bottom:1px solid #E2E8F0;
        box-shadow:0 3px 10px rgba(15,43,74,0.07);
">
<div style="
            font-size:17px;
            font-weight:700;
            color:#173F67;
">
            Analyse de tendance
</div>

<div class="description-dashboard" style="margin-top:4px;">
            Évolution du paramètre sélectionné
</div>
</div>
""",
    unsafe_allow_html=True,
)

parametres_bloc8 = sorted(df_bloc8["parametre"].dropna().unique().tolist())

if len(parametres_bloc8) == 0:
    st.warning("Aucun paramètre disponible pour cet équipement.")
else:
    parametre_bloc8 = st.selectbox("Paramètre à analyser", parametres_bloc8, key="bloc8_parametre")

    df_tendance_bloc8 = df_bloc8[df_bloc8["parametre"] == parametre_bloc8].copy()
    df_tendance_bloc8["valeur"] = pd.to_numeric(df_tendance_bloc8["valeur"], errors="coerce")
    df_tendance_bloc8 = df_tendance_bloc8.dropna(subset=["valeur"])

    tendance_bloc8 = "Stable"
    variation_bloc8 = 0.0

    if len(df_tendance_bloc8) >= 4:
        milieu = len(df_tendance_bloc8) // 2
        moyenne_debut = df_tendance_bloc8["valeur"].iloc[:milieu].mean()
        moyenne_fin = df_tendance_bloc8["valeur"].iloc[milieu:].mean()
        variation_bloc8 = moyenne_fin - moyenne_debut
        variation_relative = (variation_bloc8 / abs(moyenne_debut)) * 100 if moyenne_debut != 0 else 0

        if variation_relative > 2:
            tendance_bloc8 = "Hausse"
        elif variation_relative < -2:
            tendance_bloc8 = "Baisse"
        else:
            tendance_bloc8 = "Stable"

    texte_tendance = {"Hausse": "↗ Hausse", "Baisse": "↘ Baisse", "Stable": "→ Stable"}[tendance_bloc8]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Paramètre", parametre_bloc8)
    with c2:
        st.metric("Tendance", texte_tendance)
    with c3:
        st.metric("Variation moyenne", f"{variation_bloc8:.4f}")

    fig_tendance_bloc8 = go.Figure()
    fig_tendance_bloc8.add_trace(
        go.Scatter(
            x=df_tendance_bloc8["timestamp"],
            y=df_tendance_bloc8["valeur"],
            mode="lines",
            name=parametre_bloc8,
            line=dict(color="#173F67", width=2),
        )
    )
    fig_tendance_bloc8.update_layout(
        height=330, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=45, r=20, t=20, b=45),
        xaxis=dict(title="Date / heure", showgrid=True, gridcolor="#E5E7EB"),
        yaxis=dict(title=parametre_bloc8, showgrid=True, gridcolor="#E5E7EB"),
        font=dict(color="#173F67"),
    )
    st.plotly_chart(fig_tendance_bloc8, width="stretch")

st.markdown(
    """<div style="margin-top:30px;margin-bottom:15px;background:white;border-radius:12px;
    padding:16px 20px;border:1px solid #D8E2EC;border-left:5px solid #C0392B;
    box-shadow:0 4px 14px rgba(15,43,74,0.08);">
    <div style="font-size:17px;font-weight:700;color:#173F67;">Historique des anomalies IA</div>
    <div style="font-size:12px;color:#64748B;margin-top:4px;">
    Anomalies détectées directement par Isolation Forest</div></div>""",
    unsafe_allow_html=True,
)

nb_anomalies_bloc8 = len(anomalies_bloc8)
nb_critiques_bloc8 = 0
nb_eleves_bloc8 = 0

if "niveau_risque" in anomalies_bloc8.columns:
    nb_critiques_bloc8 = int((anomalies_bloc8["niveau_risque"] == "Critique").sum())
    nb_eleves_bloc8 = int((anomalies_bloc8["niveau_risque"] == "Élevé").sum())

a1, a2, a3 = st.columns(3)
with a1:
    st.metric("Anomalies détectées", nb_anomalies_bloc8)
with a2:
    st.metric("Critiques", nb_critiques_bloc8)
with a3:
    st.metric("Élevées", nb_eleves_bloc8)

if len(anomalies_bloc8) == 0:
    st.success(f"Aucune anomalie IA détectée pour {equipement_actif}.")
else:
    colonnes_affichage = ["timestamp", "niveau_risque", "score_anomalie"]
    colonnes_parametres = [c for c in colonnes_parametres_bloc8 if c in anomalies_bloc8.columns]
    colonnes_affichage.extend(colonnes_parametres[:3])
    colonnes_affichage = [c for c in colonnes_affichage if c in anomalies_bloc8.columns]

    tableau_bloc8 = anomalies_bloc8[colonnes_affichage].copy()
    tableau_bloc8 = tableau_bloc8.rename(
        columns={
            "timestamp": "Date / Heure",
            "niveau_risque": "Niveau de risque",
            "score_anomalie": "Score IA",
        }
    )

    if "Date / Heure" in tableau_bloc8.columns:
        tableau_bloc8 = tableau_bloc8.sort_values("Date / Heure", ascending=False)

    st.dataframe(tableau_bloc8, width="stretch", hide_index=True)

    st.download_button(
        label="⬇️ Exporter l'historique des anomalies",
        data=tableau_bloc8.to_csv(index=False).encode("utf-8"),
        file_name=f"historique_anomalies_{equipement_actif}.csv",
        mime="text/csv",
        key="bloc8_export",
    )

# ==========================================================
# BLOC 9 — RECOMMANDATIONS IA (une seule section, vue globale)
# ==========================================================

st.markdown('<div class="section-title">Recommandations IA</div>', unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .rec-card {
        background:white; border-radius:14px; padding:20px; margin-bottom:15px;
        border:1px solid #D8E2EC; box-shadow:0 4px 14px rgba(15,43,74,0.08);
    }
    .rec-title { font-size:19px; font-weight:800; color:#173F67; margin-bottom:4px; }
    .rec-subtitle { font-size:12px; color:#64748B; margin-bottom:15px; }
    .rec-kpi { font-size:14px; color:#475569; margin:6px 0; }
    .rec-value { font-size:20px; font-weight:800; color:#173F67; }
    .rec-defaut {
        background:#FDECEC; color:#B42318; padding:7px 12px; border-radius:20px;
        font-weight:800; display:inline-block; margin-bottom:12px;
    }
    .rec-alerte {
        background:#FFF4E5; color:#C56A00; padding:7px 12px; border-radius:20px;
        font-weight:800; display:inline-block; margin-bottom:12px;
    }
    .rec-normal {
        background:#EAF7EF; color:#207A45; padding:7px 12px; border-radius:20px;
        font-weight:800; display:inline-block; margin-bottom:12px;
    }
    .rec-action {
        background:#F8FAFC; border-left:4px solid #173F67; padding:12px; border-radius:8px;
        margin-top:12px; color:#334155; font-size:13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

recommandations = []

for equipement in EQUIPEMENTS:
    resultat_rec = resultats[equipement]
    nb_observations_rec = len(resultat_rec)
    nb_anomalies_rec = int(resultat_rec["est_anomalie"].sum())

    taux_anomalies_rec = (
        nb_anomalies_rec / nb_observations_rec * 100 if nb_observations_rec > 0 else 0
    )
    disponibilite_rec = 100 - taux_anomalies_rec

    etat_rec, classe_rec = classifier_etat(taux_anomalies_rec)

    if classe_rec == "defaut":
        action_rec = "Contrôle immédiat de l'équipement et vérification technique recommandée."
    elif classe_rec == "alerte":
        action_rec = "Surveillance renforcée et contrôle technique à programmer."
    else:
        action_rec = "Fonctionnement globalement stable. Poursuivre la surveillance normale."

    recommandations.append(
        {
            "equipement": equipement,
            "etat": etat_rec,
            "classe": classe_rec,
            "anomalies": nb_anomalies_rec,
            "taux": taux_anomalies_rec,
            "disponibilite": disponibilite_rec,
            "action": action_rec,
        }
    )

colonnes_rec = st.columns(3)

for i, rec in enumerate(recommandations):
    with colonnes_rec[i]:
        st.markdown(
            f"""<div class="rec-card">
            <div class="rec-title">{rec['equipement']}</div>
            <div class="rec-subtitle">Supervision intelligente ILS/DME</div>
            <div class="rec-{rec['classe']}">● État : {rec['etat']}</div>
            <div class="rec-kpi">Anomalies détectées</div>
            <div class="rec-value">{rec['anomalies']}</div>
            <div class="rec-kpi">Taux d'anomalies : <strong>{rec['taux']:.1f} %</strong></div>
            <div class="rec-kpi">Disponibilité estimée : <strong>{rec['disponibilite']:.1f} %</strong></div>
            <div class="rec-action"><strong>Action recommandée</strong><br>{rec['action']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

nb_defaut = sum(1 for r in recommandations if r["classe"] == "defaut")
nb_alerte = sum(1 for r in recommandations if r["classe"] == "alerte")
nb_normal = sum(1 for r in recommandations if r["classe"] == "normal")

st.markdown(
    f"""<div style="margin-top:15px;background:white;border-radius:12px;padding:16px 20px;
    border:1px solid #D8E2EC;box-shadow:0 4px 14px rgba(15,43,74,0.08);color:#334155;font-size:14px;">
    <strong style="color:#173F67;">Synthèse de supervision :</strong>
    {nb_defaut} équipement(s) en état de Défaut,
    {nb_alerte} équipement(s) en état d'Alerte et
    {nb_normal} équipement(s) en état Normal.
    </div>""",
    unsafe_allow_html=True,
)

# ==========================================================
# BLOC 10 — RAPPORT DE SYNTHÈSE (PDF)
# ==========================================================

st.markdown(
    """
<div style="
        margin-top:20px;
        margin-bottom:4px;
        font-size:22px;
        font-weight:700;
        color:#173F67;
">
        Rapport de synthèse
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
"""
<div class="sous-titre-dashboard">
        Génère un rapport PDF récapitulatif de l'état du système
        (période et équipement sélectionnés).
</div>
""",
    unsafe_allow_html=True,
)


def generer_rapport_pdf():
    """Construit un rapport PDF de synthèse à partir des données déjà calculées
    (donnees_globales, recommandations, resultats filtrés par la période active)."""

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT

    BLEU_PDF = colors.HexColor("#0B2545")
    BLEU2_PDF = colors.HexColor("#173F67")
    OR_PDF = colors.HexColor("#D4A017")
    GRIS_PDF = colors.HexColor("#64748B")
    GRIS_CLAIR_PDF = colors.HexColor("#F4F6F8")
    ROUGE_PDF = colors.HexColor("#C0392B")
    ORANGE_PDF = colors.HexColor("#F39C12")
    VERT_PDF = colors.HexColor("#2E8B57")

    tampon = io.BytesIO()
    document = SimpleDocTemplate(
        tampon,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title="Rapport de supervision ILS/DME",
    )

    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        "TitrePrincipal", parent=styles["Heading1"],
        fontSize=18, textColor=BLEU_PDF, spaceAfter=4,
    )
    style_sous_titre = ParagraphStyle(
        "SousTitre", parent=styles["Normal"],
        fontSize=10, textColor=OR_PDF, spaceAfter=14,
    )
    style_section = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontSize=13, textColor=BLEU2_PDF, spaceBefore=16, spaceAfter=8,
    )
    style_normal = ParagraphStyle(
        "NormalPetit", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#334155"), leading=12,
    )
    style_pied = ParagraphStyle(
        "Pied", parent=styles["Normal"],
        fontSize=8, textColor=GRIS_PDF, alignment=TA_LEFT,
    )

    elements = []

    # ---- En-tête ----
    elements.append(Paragraph("Supervision Intelligente — Système ILS/DME", style_titre))
    elements.append(
        Paragraph(
            f"Aéroport Fès-Saïss • Domaine CNS : Navigation • LOC • GP • DME "
            f"&nbsp;·&nbsp; Période : {LABELS_PERIODE.get(periode_actif, periode_actif)}",
            style_sous_titre,
        )
    )
    elements.append(
        Paragraph(
            f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — "
            f"Dernière mesure disponible : {date_maj.strftime('%d/%m/%Y %H:%M')}",
            style_normal,
        )
    )
    elements.append(Spacer(1, 10))

    # ---- Synthèse globale ----
    elements.append(Paragraph("Synthèse globale du système", style_section))

    donnees_synthese = [
        ["État global", "Disponibilité globale", "Anomalies détectées", "Équipement le plus à risque"],
        [
            etat_global,
            f"{disponibilite_systeme:.1f} %",
            f"{total_anomalies_systeme} (taux : {taux_anomalies_systeme:.1f} %)",
            f"{nom_plus_risque} ({taux_plus_risque:.1f} %)",
        ],
    ]
    tableau_synthese = Table(donnees_synthese, colWidths=[3.5 * cm, 4 * cm, 5 * cm, 4.5 * cm])
    tableau_synthese.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLEU2_PDF),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [GRIS_CLAIR_PDF]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(tableau_synthese)

    # ---- État par équipement ----
    elements.append(Paragraph("État détaillé par équipement", style_section))

    entetes_eq = ["Équipement", "Type", "Disponibilité", "Anomalies", "Taux", "État"]
    lignes_eq = [entetes_eq]

    couleurs_etats = {"Normal": VERT_PDF, "Alerte": ORANGE_PDF, "Défaut": ROUGE_PDF}

    for ligne in donnees_globales:
        eq = ligne["equipement"]
        statut_txt, _ = classifier_etat(ligne["taux"])

        lignes_eq.append(
            [
                eq,
                TYPES_EQUIPEMENTS.get(eq, "Équipement CNS"),
                f"{ligne['disponibilite']:.1f} %",
                str(ligne["anomalies"]),
                f"{ligne['taux']:.1f} %",
                statut_txt,
            ]
        )

    tableau_eq = Table(
        lignes_eq,
        colWidths=[2.2 * cm, 4.5 * cm, 2.8 * cm, 2.4 * cm, 2 * cm, 3.1 * cm],
    )

    style_tableau_eq = [
        ("BACKGROUND", (0, 0), (-1, 0), BLEU2_PDF),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLAIR_PDF]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for i, ligne in enumerate(donnees_globales, start=1):
        statut_txt = lignes_eq[i][5]
        style_tableau_eq.append(
            ("TEXTCOLOR", (5, i), (5, i), couleurs_etats.get(statut_txt, colors.black))
        )
        style_tableau_eq.append(("FONTNAME", (5, i), (5, i), "Helvetica-Bold"))

    tableau_eq.setStyle(TableStyle(style_tableau_eq))
    elements.append(tableau_eq)

    # ---- Recommandations IA ----
    elements.append(Paragraph("Recommandations IA", style_section))

    entetes_rec = ["Équipement", "État", "Anomalies", "Taux", "Disponibilité", "Action recommandée"]
    lignes_rec = [entetes_rec]

    for rec in recommandations:
        lignes_rec.append(
            [
                rec["equipement"],
                rec["etat"],
                str(rec["anomalies"]),
                f"{rec['taux']:.1f} %",
                f"{rec['disponibilite']:.1f} %",
                Paragraph(rec["action"], style_normal),
            ]
        )

    tableau_rec = Table(
        lignes_rec,
        colWidths=[2.2 * cm, 2.3 * cm, 2.2 * cm, 1.8 * cm, 2.5 * cm, 5.8 * cm],
    )

    style_tableau_rec = [
        ("BACKGROUND", (0, 0), (-1, 0), BLEU2_PDF),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLAIR_PDF]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for i, rec in enumerate(recommandations, start=1):
        style_tableau_rec.append(
            ("TEXTCOLOR", (1, i), (1, i), couleurs_etats.get(rec["etat"], colors.black))
        )
        style_tableau_rec.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))

    tableau_rec.setStyle(TableStyle(style_tableau_rec))
    elements.append(tableau_rec)

    # ---- Synthèse de supervision ----
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            f"<b>Synthèse de supervision :</b> {nb_defaut} équipement(s) en état de "
            f"Défaut, {nb_alerte} équipement(s) en état d'Alerte et "
            f"{nb_normal} équipement(s) en état Normal.",
            style_normal,
        )
    )

    # ---- Pied de page ----
    elements.append(Spacer(1, 24))
    elements.append(
        Paragraph(
            "Office National Des Aéroports — Aéroport Fès-Saïss — Service CNS Navigation. "
            "Rapport généré automatiquement par le système de supervision intelligente ILS/DME. "
            "Référentiel des tolérances : FEZ.PS08.E.422/01.",
            style_pied,
        )
    )

    document.build(elements)
    tampon.seek(0)
    return tampon.getvalue()


try:
    pdf_bytes = generer_rapport_pdf()

    st.download_button(
        label="📄 Générer et télécharger le rapport de synthèse (PDF)",
        data=pdf_bytes,
        file_name=f"rapport_supervision_ILS_DME_{periode_actif}.pdf",
        mime="application/pdf",
        key="export_rapport_pdf",
    )
except ImportError:
    st.warning(
        "La génération de rapport PDF nécessite le module `reportlab`. "
        "Installe-le avec : `pip install reportlab`"
    )