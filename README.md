# ✈️ Supervision intelligente des équipements CNS

##  Présentation du projet

Ce projet a été réalisé dans le cadre d'un stage à **l'Aéroport Fès-Saïss – ONDA**.

Il porte sur la mise en place d'une solution de **supervision intelligente des équipements CNS (Communication, Navigation et Surveillance)**, avec une application interactive permettant de suivre l'état des équipements, d'analyser leurs paramètres et de détecter automatiquement d'éventuelles anomalies.

La solution développée combine :

* la génération et la gestion des données de supervision ;
* le stockage dans une base de données SQLite ;
* la préparation et l'analyse des données ;
* la détection automatique des anomalies par Machine Learning ;
* le calcul d'un niveau de risque ;
* la visualisation interactive à travers un dashboard Streamlit.

---

##  Objectifs

Les principaux objectifs du projet sont :

* Superviser les équipements CNS de manière centralisée ;
* Suivre l'évolution des paramètres techniques dans le temps ;
* Identifier automatiquement les comportements anormaux ;
* Exploiter des techniques de Machine Learning pour assister la supervision ;
* Fournir une visualisation claire et interactive des résultats ;
* Faciliter l'interprétation des anomalies et des niveaux de risque.

---

##  Équipements supervisés

Le dashboard permet actuellement de superviser trois équipements liés au système ILS/DME de l'aéroport :

###  LOC — Localizer

* **Identifiant :** LFA
* **Catégorie :** CAT II
* **Fréquence :** 109.7 MHz
* **Piste :** RWY 27
* **Nomenclature :** 7014B4

###  GP — Glide Path

* **Identifiant :** LFA
* **Catégorie :** CAT II
* **Fréquence :** 333.2 MHz
* **Piste :** RWY 27
* **Nomenclature :** 7033B4

###  DME — Distance Measuring Equipment

* **Identifiant :** LFA
* **Catégorie :** CAT II
* **Canal :** 34 X
* **Piste :** RWY 27
* **Nomenclature :** LDB-103

---

##  Pipeline de traitement

Le projet suit une chaîne de traitement permettant de passer des données de supervision à leur analyse et à leur visualisation.

### Pipeline global

![Pipeline de traitement](/assets/Pipline.png)

*Figure 1 — Pipeline global de traitement des données*

Le pipeline comprend principalement les étapes suivantes :

1. **Simulation des données** — Génération des données nécessaires au fonctionnement du prototype de supervision.

2. **Stockage des données** — Enregistrement des données dans une base de données SQLite.

3. **Préparation des données** — Nettoyage, transformation et organisation des données afin de les rendre exploitables par les méthodes d'analyse.

4. **Analyse des données** — Étude de l'évolution des paramètres techniques et identification des tendances.

5. **Détection des anomalies** — Utilisation d'une méthode de Machine Learning basée sur l'**Isolation Forest** afin d'identifier les comportements inhabituels.

6. **Évaluation du risque** — Attribution d'un niveau de risque selon les résultats de l'analyse et les seuils définis.

7. **Visualisation** — Présentation des informations et des résultats dans une interface interactive développée avec **Streamlit**.
---

##  Architecture du projet

L'organisation générale du projet est la suivante :

```text
Projet_cns/
│
├── assets/
│   ├── background.jpg
│   ├── logo_onda.png
│   ├── pipline.png
│   └── screenshots/
│       ├── dashboard_overview.png
│       ├── dashboard_loc.png
│       ├── dashboard_gp.png
│       └── dashboard_dme.png
│
├── donnees_test/
│
├── scripts/
│   ├── 01_simulation_donnees.py
│   ├── 02_creation_base_donnees.py
│   ├── 03_dashboard.py
│   └── ia_engine.py
│
├── supervision_ils_dme.db
├── verifier_db.py
├── requirements.txt
├── .gitignore
└── README.md
```

> Les noms des captures d'écran dans `assets/screenshots/` peuvent être adaptés aux noms réellement présents dans le projet.

---

##  Organisation des principaux fichiers

### `scripts/01_simulation_donnees.py`

Ce script permet de générer les données utilisées par le prototype de supervision.

Les données générées permettent notamment de représenter l'évolution temporelle des paramètres des équipements.

### `scripts/02_creation_base_donnees.py`

Ce script permet de créer et d'alimenter la base de données SQLite utilisée par l'application.

La base principale utilisée dans la version actuelle est :

```text
supervision_ils_dme.db
```

### `scripts/ia_engine.py`

Ce module regroupe les fonctions utilisées pour le traitement et l'analyse intelligente des données.

Il permet notamment :

* de charger les données ;
* de préparer les données pour le modèle ;
* d'appliquer l'algorithme de détection d'anomalies ;
* de calculer les scores associés ;
* de mettre les résultats sous une forme exploitable par le dashboard.

### `scripts/03_dashboard.py`

Ce script constitue l'application principale de supervision.

Le dashboard est développé avec **Streamlit** et permet de :

* sélectionner un équipement ;
* choisir une période d'analyse ;
* consulter les indicateurs de supervision ;
* visualiser l'évolution des paramètres ;
* consulter les anomalies détectées ;
* interpréter les niveaux de risque.

---

##  Intelligence Artificielle

### Isolation Forest

La détection des anomalies repose sur l'algorithme **Isolation Forest**.

Cette méthode de Machine Learning non supervisée permet d'identifier des observations qui présentent un comportement différent de celui de la majorité des données.

Le principe consiste à isoler progressivement les observations dans des arbres aléatoires. Les observations qui peuvent être isolées plus rapidement sont considérées comme potentiellement anormales.

Dans ce projet, l'Isolation Forest est utilisée pour compléter la supervision classique basée sur les seuils techniques.

### Fonctionnement général

```text
Données de supervision
        ↓
Préparation des données
        ↓
Construction de la matrice
        ↓
Isolation Forest
        ↓
Score d'anomalie
        ↓
Niveau de risque
        ↓
Visualisation dans Streamlit
```

---

##  Niveaux d'état et de risque

Le dashboard permet de présenter l'état des équipements selon différents niveaux.

### État de supervision

| État      | Signification                                       |
| --------- | --------------------------------------------------- |
| 🟢 Normal | Paramètres dans une zone normale                    |
| 🟠 Alerte | Écart nécessitant une surveillance                  |
| 🔴 Défaut | Situation présentant un niveau d'anomalie important |

### Niveau de risque IA

Le moteur d'analyse peut également associer un niveau de risque aux observations détectées :

* **Normal / Faible**
* **Élevé**
* **Critique**

Ces informations permettent de compléter les indicateurs classiques par une analyse basée sur les données.

---

##  Dashboard de supervision

L'application fournit une interface interactive permettant de consulter les informations relatives aux équipements CNS, d'analyser leur comportement et d'interpréter les résultats de la détection des anomalies.

### Vue générale du dashboard

![Dashboard de supervision](/assets/Screenchots/Dashboard.png)

*Figure 2 — Vue générale du dashboard de supervision*

### Analyse des tendances

![Analyse de tendance](/assets/Screenchots/Analyse%20de%20tendance.png)

*Figure 3 — Analyse de l'évolution des paramètres techniques*

### Recommandations issues de l'IA

![Recommandations IA](/assets/Screenchots/Recommandations%20IA.png)

*Figure 4 — Recommandations générées à partir des résultats de l'analyse*
---

##  Fonctionnalités du dashboard

Le dashboard permet notamment :

* de sélectionner l'équipement à superviser ;
* de choisir une période d'analyse ;
* d'afficher les principaux indicateurs ;
* de visualiser les séries temporelles ;
* d'identifier les anomalies ;
* d'afficher les niveaux d'état ;
* d'exploiter les résultats du moteur IA ;
* de consulter les données sous forme de graphiques interactifs.

Les périodes disponibles permettent notamment d'analyser :

* les dernières **24 heures** ;
* les **7 derniers jours** ;
* les **30 derniers jours** ;
* l'ensemble des données disponibles.

---

##  Stockage des données

Les données utilisées par l'application sont stockées dans une base **SQLite** :

```text
supervision_ils_dme.db
```

Cette base permet de centraliser les données nécessaires à la supervision et à l'analyse.

Le projet utilise également des fichiers de données intermédiaires lorsque cela est nécessaire pour les différentes étapes de traitement.

---

##  Technologies utilisées

| Technologie      | Utilisation                             |
| ---------------- | --------------------------------------- |
| **Python**       | Développement général                   |
| **Pandas**       | Manipulation et préparation des données |
| **NumPy**        | Calcul numérique                        |
| **Scikit-learn** | Machine Learning et Isolation Forest    |
| **Plotly**       | Visualisations interactives             |
| **Streamlit**    | Développement du dashboard              |
| **SQLite**       | Stockage des données                    |
| **Matplotlib**   | Visualisation complémentaire            |

---

##  Installation

### 1. Cloner ou récupérer le projet

Placer le projet dans un répertoire local.

### 2. Créer un environnement virtuel

Sous Windows PowerShell :

```powershell
python -m venv venv
```

### 3. Activer l'environnement virtuel

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Installer les dépendances

```powershell
pip install -r requirements.txt
```

---

##  Lancement de l'application

Une fois les dépendances installées, lancer le dashboard avec :

```powershell
streamlit run scripts/03_dashboard.py
```

L'application Streamlit s'ouvre ensuite dans le navigateur.

---

## Fonctionnement global

Le fonctionnement général de la solution peut être résumé comme suit :

```text
          DONNÉES DE SUPERVISION
                    │
                    ▼
          Préparation des données
                    │
                    ▼
             Base SQLite
                    │
                    ▼
            Analyse des données
                    │
                    ▼
          Détection des anomalies
                    │
                    ▼
            Isolation Forest
                    │
                    ▼
            Score de risque
                    │
                    ▼
          Dashboard Streamlit
                    │
                    ▼
       Supervision et interprétation
```

---

##  Résultat attendu

La solution proposée permet de disposer d'un prototype de supervision capable de combiner :

* la surveillance des équipements ;
* l'analyse temporelle des paramètres ;
* la détection automatique des anomalies ;
* l'évaluation du niveau de risque ;
* la visualisation interactive des résultats.

L'objectif est ainsi de fournir une approche permettant d'assister la supervision technique des équipements CNS à travers l'exploitation des données et des techniques d'intelligence artificielle.

---

##  Contexte du stage

**Organisme d'accueil :** Office National des Aéroports — ONDA
**Site :** Aéroport Fès-Saïss
**Projet :** Supervision intelligente des équipements CNS
**Domaine :** Big Data & Intelligence Artificielle

---

##  Réalisation

Projet réalisé dans le cadre d'un stage en **Big Data & Intelligence Artificielle**.

**Établissement :** École Nationale des Sciences Appliquées de Tétouan — ENSA Tétouan

---

##  Remarque

Ce projet constitue un **prototype académique de supervision intelligente**. Les données utilisées dans cette version servent à reproduire le fonctionnement d'une chaîne de supervision et à démontrer l'intégration entre traitement des données, Machine Learning et visualisation interactive.
