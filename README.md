[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/zP0O23M7)

# GROUPE 5

## Nom des auteurs

Cousin Bastien (TD1-TPB)
Deldalle Pierre (TD1-TPB)
Groué Sébastien (TD2-TPD)

## Méthodes choisies

- Interface Utilisateur : Développez une interface permettant de charger un fichier FITS et
d’ajuster en temps réel la force de la réduction (taille du noyau et seuil du masque).

- Comparateur Avant/Après : Créez un outil de visualisation qui permet de superposer
rapidement l’image originale et l’image traitée (fonction "clignotement" + ajout de slider avec la bibliothéque QT) pour
détecter les pertes de détails dans la nébuleuse.

- Réduction Multitaille : Les grosses étoiles nécessitent une érosion plus forte que les petites.
Proposez un algorithme qui adapte la taille du noyau d’érosion en fonction de la magnitude
de l’étoile.

## Difficultés rencontrées

- Problème avec le dossier venv, qu’on essayait de push sur le github. 

- Problème lors de l’érosion, ajouter la Réduction Multi-taille donnait des masques complétement noirs qui n'affichaient aucune étoiles. 

- Problèmes de lenteur sur l’application utilisateur,  impossible de manipuler les curseurs à cause des calculs.

## Résultat

Une application fonctionnelle où l'utilisateur peut choisir l'image FITS qu'il souhaite modifier. Il y a donc une interface d'accueil où l'utilisateur peut récupérer son image FITS dans ses dossiers personnels. Il peut ensuite la modifier avec deux curseurs : la taille du noyau d'érosion et le seuil de détection des étoiles, il peut aussi décider d'afficher une réduction Multitaille si il le souhaite avec un bouton ON/OFF. Une fois ses modifications réalisées, il enregistre et peut comparer grâce à un bouton de clignotement et un curseur qui permet de voir précisément ce qui change.


# Project Documentation

## Installation


### Virtual Environment

It is recommended to create a virtual environment before installing dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```


### Dependencies
```bash
pip install -r requirements.txt
```

Or install dependencies manually:
```bash
pip install [package-name]
```

## Usage


### Command Line
```bash
python main.py [arguments]
```

## Requirements

- Python 3.8+
- See `requirements.txt` for full dependency list

## Examples files
Example files are located in the `examples/` directory. You can run the scripts with these files to see how they work.
- Example 1 : `examples/HorseHead.fits` (Black and whiteFITS image file for testing)
- Example 2 : `examples/test_M31_linear.fits` (Color FITS image file for testing)
- Example 3 : `examples/test_M31_raw.fits` (Color FITS image file for testing)



