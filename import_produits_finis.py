"""
import_produits_finis.py — Importation des produits finis dans la BDD HACCP Monitor

Usage :
    1. Collez votre tableau JSON dans la variable PRODUITS_JSON ci-dessous.
    2. Exécutez : python import_produits_finis.py

Format attendu pour chaque objet JSON :
    {
        "nom": "Chair à saucisse",
        "categorie": "produit_fini",        # catégorie libre
        "dlc_jours": 3,
        "temperature_conservation": "0°C à +4°C"
    }

Le champ type_produit sera forcé à 'fini' pour tous les produits importés.
Si un produit avec le même nom existe déjà, ses champs seront mis à jour.
"""

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# COLLEZ ICI VOTRE TABLEAU JSON
# ---------------------------------------------------------------------------
PRODUITS_JSON = [
  {"nom": "Aiguillette baronne de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Araignée de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Basse cote avec os", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Basse cote sans os", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Bavette d'aloyau", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Bavette de Flanchet", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Carpaccio de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Club de viande à l'ananas", "categorie": "Préparation bœuf", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Coeur de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Collier de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de boeuf", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Entrecôte", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Faux-filet de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de boeuf", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de boeuf façon tournedos", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Foie de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Hampe", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Jarret de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Joue de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Langue de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Marteau de Thor", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Médaillon de boeuf aux fines herbes", "categorie": "Préparation bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Merlan de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Nerveux de gîte de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Onglet de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Os à moelle", "categorie": "Bœuf", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paleron de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de rumsteak de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Picanha", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Piece à fondue de boeuf", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Plat de cote de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poire de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Queue de boeuf", "categorie": "Bœuf", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Rognon de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Roti de boeuf", "categorie": "Bœuf", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti rumsteck de boeuf", "categorie": "Bœuf", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roulé de boeuf farci", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Scalopine de boeuf", "categorie": "Bœuf", "destination": "A griller, A rotir", "dlc_jours": 1, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Steak de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Steak Haché de boeuf", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 1, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Tomahawk", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Viande haché de boeuf 5%", "categorie": "Bœuf", "destination": "A griller", "dlc_jours": 1, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Araignée de porc", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Barde", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Carré de porc", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cervelle de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Cochon de lait", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de porc echine", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de porc farcie réunionnaise", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de porc filet", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de porc première", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Crépinettes de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Échine de porc à l'ancienne", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Escalope de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Farci de porc au bleu et aux poires", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de porc farci à la mode de Bayonne", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet mignon de porc", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet mignon de porc lambada aux ananas", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 1, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Fricadelle de porc", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Gorge de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Grillade de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Haché de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 1, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Jambon entier de porc", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Jarret de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Joue de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Langue de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Langue de porc demi-sel", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Médaillon de porc montmorency", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Museau de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Oreille de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Palette de porc demi sel", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pied de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine entière de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine tranchée de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Queue de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Ribs", "categorie": "Porc", "destination": "A griller, A rotir, A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rognon de porc", "categorie": "Porc", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Roti de porc à la moderne", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de porc echine", "categorie": "Porc", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de porc filet", "categorie": "Porc", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de porc florida fumé etarni de fruits secs", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de porc roulé à la florentine", "categorie": "Préparation porc", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rouelle de jambon", "categorie": "Porc", "destination": "A rotir, a mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Sauté de porc", "categorie": "Porc", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Travers de porc", "categorie": "Porc", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cordon bleu", "categorie": "Veau", "destination": "A griller", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de veau découverte", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de veau filet", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de veau première", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Epaule de veau", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Escalope de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Escalope de veau farcie amandine", "categorie": "Préparation veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de veau", "categorie": "Veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Flanchet de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Foie de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Grenadin de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Hamburger de veau forestière", "categorie": "Préparation veau", "destination": "A griller, A rotir", "dlc_jours": 1, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Noix de veau farcie à l'anglaise", "categorie": "Préparation veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Osso buco", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de veau", "categorie": "Veau", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pied de veau", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine de veau", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Quasi de veau", "categorie": "Veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Ris de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Rognon de veau", "categorie": "Veau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Roti de veau", "categorie": "Veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rôti de veau fruitina", "categorie": "Préparation veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de veau orloff", "categorie": "Préparation veau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roulade de veau farcie au fromage frais et pistaches", "categorie": "Préparation veau", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Sauté de veau", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Tendron de veau", "categorie": "Veau", "destination": "A mijoter, A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Tete de veau roulé", "categorie": "Veau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Aiguillette de canard", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Aiguillette de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de caille", "categorie": "Volaille", "destination": "Brochette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de canard", "categorie": "Volaille", "destination": "Brochette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de dinde", "categorie": "Volaille", "destination": "Brochette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette de poulet", "categorie": "Volaille", "destination": "Brochette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Caille", "categorie": "Volaille", "destination": "Caille", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Canette", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Coq", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Coquelet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuisse de canard", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuisse de dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuisse de lapin", "categorie": "Volaille", "destination": "Lapin", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuisse de pintade", "categorie": "Volaille", "destination": "Pintade", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuisse de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Escalope de Dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Farce de volaille", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de poulet à la pistache", "categorie": "préparation volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de poulet au jambon de parme et pistache", "categorie": "préparation volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Foie de lapin", "categorie": "Volaille", "destination": "Lapin", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Foie de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Gésier de canard confit", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Gésier de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Gigolette(épaule) de lapin", "categorie": "Volaille", "destination": "Lapin", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Haut de cuisse de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Lapin entier", "categorie": "Volaille", "destination": "Lapin", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Magret de canard", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Magret de canard fumé tranché", "categorie": "Volaille", "destination": "Canard", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Oie", "categorie": "Volaille", "destination": "Oie", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Osso bucco de dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de canard farci", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de dinde", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de lapin", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de pintade", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de poularde", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Paupiette de poulet", "categorie": "préparation volaille", "destination": "Paupiette", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pigeon", "categorie": "Volaille", "destination": "Pigeon", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pillon de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pintade", "categorie": "Volaille", "destination": "Pintade", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pintade Chaponée", "categorie": "Volaille", "destination": "Pintade", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine de dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine de dinde marron framboise", "categorie": "préparation volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poularde de Bresse", "categorie": "Volaille", "destination": "Poularde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poularde Fermière", "categorie": "Volaille", "destination": "Poularde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poulet fermier", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poulet fermier PAC", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rable de lapin", "categorie": "Volaille", "destination": "Lapin", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de dinde Orloff", "categorie": "préparation volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de poulet", "categorie": "Volaille", "destination": "Poulet", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Sot l'y laisse de dinde", "categorie": "Volaille", "destination": "Dinde", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Brochette d'agneau", "categorie": "Agneau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cervelle d'agneau", "categorie": "Agneau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 3°C"},
  {"nom": "Collier d'agneau", "categorie": "Agneau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote d'agneau découverte", "categorie": "Agneau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote d'agneau filet", "categorie": "Agneau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote d'agneau première", "categorie": "Agneau", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Couronne d'agneau", "categorie": "Agneau", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Crépine", "categorie": "Agneau", "destination": "A griller, A rotir, A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Epaule d'agneau", "categorie": "Agneau", "destination": "A rotir, A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Epaule d'agneau roulée", "categorie": "Agneau", "destination": "A rotir, A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Gigot d'agneau", "categorie": "Agneau", "destination": "A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poitrine d'agneau", "categorie": "Agneau", "destination": "A mijoter, A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Sauté d'agneau", "categorie": "Agneau", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Steakette d'agneau au fromage", "categorie": "Préparation agneau", "destination": "A griller, A rotir", "dlc_jours": 2, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Tranche deigot d'agneau", "categorie": "Agneau", "destination": "A mijoter, A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Tranche d'épaule d'agneau", "categorie": "Agneau", "destination": "A mijoter, A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Souris d'agneau", "categorie": "Agneau", "destination": "A rotir, a mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Araignée de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Basse cote de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Bavette d'aloyau de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Bavette de flanchet de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Collier de cheval", "categorie": "Cheval", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cote de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Entrecote de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Faux filet de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de cheval façon tournedos", "categorie": "Cheval", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Haché de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Jarret de cheval", "categorie": "Cheval", "destination": "A mijoter", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Piece a fondue", "categorie": "Cheval", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Poire de cheval", "categorie": "Cheval", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rond de tranche de cheval", "categorie": "Cheval", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Rumsteak de cheval", "categorie": "Cheval", "destination": "A griller, A rotir", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Steak de cheval", "categorie": "Cheval", "destination": "A griller", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Canard sauvage", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Civet de cerf", "categorie": "Gibier", "destination": "Cerf", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Civet de sanglier", "categorie": "Gibier", "destination": "Sanglier", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Cuissot de chevreuil", "categorie": "Gibier", "destination": "Cerf", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Faisan", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Grouse", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Oie sauvage", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de cerf", "categorie": "Gibier", "destination": "Cerf", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de sanglier", "categorie": "Gibier", "destination": "Sanglier", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Perdreau", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Perdrix", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pigeon sauvage", "categorie": "Gibier", "destination": "A plumes", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de cerf", "categorie": "Gibier", "destination": "Cerf", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti de sanglier", "categorie": "Gibier", "destination": "Sanglier", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Entrecôte de kangourou", "categorie": "Viande exotique", "destination": "Kangourou", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Entrecôte de zèbre", "categorie": "Viande exotique", "destination": "Zèbre", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de crocodile", "categorie": "Viande exotique", "destination": "Crocodile", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de kangourou", "categorie": "Viande exotique", "destination": "Kangourou", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Filet de zèbre", "categorie": "Viande exotique", "destination": "Zèbre", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé d'autruche", "categorie": "Viande exotique", "destination": "Autruche", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavé de kangourou", "categorie": "Viande exotique", "destination": "Kangourou", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavés de bison", "categorie": "Viande exotique", "destination": "Bison", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavés de lama", "categorie": "Viande exotique", "destination": "Lama", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Pavés de zèbre", "categorie": "Viande exotique", "destination": "Zèbre", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Roti d'autruche", "categorie": "Viande exotique", "destination": "Autruche", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"},
  {"nom": "Merguez forte", "categorie": "Préparation agneau/bœuf", "destination": "Agneau / Bœuf", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Merguez douce", "categorie": "Préparation agneau/bœuf", "destination": "Agneau / Bœuf", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Saucisse de toulouse", "categorie": "Préparation porc veau", "destination": "Porc / veau", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Chipolata", "categorie": "Préparation porc veau", "destination": "Porc / veau", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Mini chorizo", "categorie": "Préparation agneau/bœuf", "destination": "Agneau / Bœuf", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Tomate farci", "categorie": "Préparation porc veau", "destination": "Porc / veau", "dlc_jours": 2, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Farce aux légumes", "categorie": "Préparation porc veau", "destination": "Porc / veau", "dlc_jours": 2, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Chair à saucisse", "categorie": "Préparation porc", "destination": "Porc", "dlc_jours": 3, "temperature_conservation": "+ 0 à 2°C"},
  {"nom": "Roti de porc orloff", "categorie": "Préparation porc", "destination": "Porc", "dlc_jours": 4, "temperature_conservation": "+ 0 à 4°C"}
]
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent / "haccp.db"
BOUTIQUE_ID = 1


def run():
    if not PRODUITS_JSON:
        print("⚠  PRODUITS_JSON est vide. Collez votre tableau JSON avant de lancer le script.")
        return

    if not DB_PATH.exists():
        print(f"❌  Base de données introuvable : {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    inserts = 0
    updates = 0

    for p in PRODUITS_JSON:
        nom = p.get("nom", "").strip()
        if not nom:
            print("  ⚠  Produit sans nom ignoré.")
            continue

        categorie              = p.get("categorie", "produit_fini")
        dlc_jours              = int(p.get("dlc_jours", 0))
        temperature_conservation = p.get("temperature_conservation", "0°C à +4°C")

        # Chercher un doublon par nom (toutes boutiques confondues pour être sûr)
        cur.execute(
            "SELECT id FROM produits WHERE nom = ? AND boutique_id = ?",
            (nom, BOUTIQUE_ID),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE produits
                SET categorie = ?,
                    dlc_jours = ?,
                    temperature_conservation = ?,
                    type_produit = 'fini',
                    actif = 1
                WHERE id = ?
                """,
                (categorie, dlc_jours, temperature_conservation, row["id"]),
            )
            updates += 1
            print(f"  ↻  Mis à jour : {nom}")
        else:
            cur.execute(
                """
                INSERT INTO produits
                    (boutique_id, nom, categorie, dlc_jours, temperature_conservation, type_produit)
                VALUES (?, ?, ?, ?, ?, 'fini')
                """,
                (BOUTIQUE_ID, nom, categorie, dlc_jours, temperature_conservation),
            )
            inserts += 1
            print(f"  ✔  Inséré : {nom}")

    conn.commit()
    conn.close()

    print(f"\nTerminé — {inserts} insertion(s), {updates} mise(s) à jour.")


if __name__ == "__main__":
    run()
