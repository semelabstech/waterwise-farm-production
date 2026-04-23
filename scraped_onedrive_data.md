# Résumé du Scraping OneDrive (DS-2025-G1)

Les données suivantes ont été extraites du bloc-notes OneNote via le lien partagé :

## Section 00 : Informations générales
- **Syllabus**
  - **Thèmes abordés :** 
    - Introduction aux systèmes distribués 
    - Architectures
    - Principes de Développement
    - Auto-stabilisation
    - Cloud Computing
    - L'Intelligence Artificielle (IA) dans les systèmes distributifs.

## Section 01 : Cours (Tableau blanc)
- **Séance 0**
  - **Définition (Systèmes distribués) :** Un "ensemble de machines autonomes interconnectées... qui donne à l'utilisateur final l'illusion d'utiliser une seule machine."

## Section 02 : TD (Travaux Dirigés)
- **Série 1 : Synchronisation**
  - **Exercice 1 :** Calcul du Delay et de l'Offset NTP. Paramètres observés : Client (1000ms), Serveur (1020/1025), Client Retour (1055).
  - **Exercice 2 :** Hiérarchie NTP Stratum. Structure : Récepteur GPS -> Serveur Local -> 50 postes de travail (desktops).
  - **Exercice 3 :** Horloges de Lamport. Implique 3 processus et des événements : a, b (envoi), c (réception), d (envoi), e (réception), f.
  - **Exercice 4 :** Horloges scalaires et vectorielles pour 4 sites qui s'échangent des messages.

## Section 03 : TP (Travaux Pratiques) & Projets
- **Projet : Chat distribué**
  - **Objectif :** Développer une application de chat distribué robuste.
  - **Fonctionnalités attendues :** Inscription/Connexion, Messagerie en temps réel, Canaux de discussion, Liste d'utilisateurs en temps réel.
- **TP 1 - Modèle Client/Serveur**
  - **Tâche 1 :** Créer un serveur calculant et retournant la somme de nombres.
  - **Tâche 2 :** Écrire un client pour récupérer la somme des deux nombres calculée par le serveur.
  - **Tâche 3 :** Écrire une version du serveur capable de gérer de multiples clients.

## Section 04 : Ressources
- **Livres recommandés :** 
  - "Distributed Systems" par Andrew S. Tanenbaum.
  - "Distributed Systems: Concepts and Design" par George Coulouris.

## Section 05 : Annonces et Thèmes de Projet
- **Dates clés :**
  - **12/04/2026 :** Date limite pour le choix des sujets de projet et la formation des équipes.
  - **15/05/2026 :** Date prévue de l'examen final (indiqué potentiellement comme 2025, mais probablement 2026 vu la date des projets).
- **Sujets des projets (Thèmes) :**
  - **Thème 1 : Agriculture & Stress Hydrique** (Correspondant au répertoire actuel de votre projet !)
  - **Thème 2 :** Mobilité Urbaine et Transport Intelligent.
  - **Thème 3 :** Santé et Télémédecine.
  - **Thème 4 :** Énergie et Réseaux Intelligents (Smart Grids).
