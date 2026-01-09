import sys
import cv2 as cv
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QSlider, QFileDialog
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QTimer

# 3 lignes qui permettent de ne pas afficher les warnings dans la console.
import warnings
from photutils.utils import NoDetectionsWarning
warnings.filterwarnings("ignore", category=NoDetectionsWarning)

# Interface 1 : Mettre l'image fits que l'on veut dans le logiciel
class InterfaceChoix(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Choisir une image FITS")
        self.resize(800, 600)
        self.label_bienvenue = QLabel("Bienvenue,\npour commencer veuillez sélectionner votre image.")
        self.label_bienvenue.setAlignment(Qt.AlignCenter)
        self.label_bienvenue.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        panneau_bienvenue = QWidget()
        panneau_bienvenue.setStyleSheet("background-color: gray; border-radius: 10px; margin-left: 50px; margin-right: 50px;")

        layout_panneau = QVBoxLayout()
        layout_panneau.addWidget(self.label_bienvenue)
        panneau_bienvenue.setLayout(layout_panneau)

        self.bouton_ouvrir = QPushButton("Ouvrir FITS")
        self.bouton_ouvrir.clicked.connect(self.ouvrir_fits)
        self.bouton_ouvrir.setMinimumSize(200, 50)
        self.bouton_ouvrir.setStyleSheet("background-color: gray; color: white; font-size: 18px;")

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(panneau_bienvenue)
        layout.addSpacing(30)
        layout.addWidget(self.bouton_ouvrir, alignment=Qt.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def ouvrir_fits(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un FITS", "", "*.fits")
        if not path:
            return

        # Lecture de l'image choisie
        data = fits.getdata(path)
        if data.ndim > 2:
            data = np.mean(data, axis=0)

        data = np.nan_to_num(data)
        #Pour convertir l'image en formats 8 bits au lieu de le laisser par défaut
        image = ((data - np.min(data)) / (np.max(data) - np.min(data)) * 255).astype(np.uint8)

        # Ouvre l'interface de personnalisation
        self.interface_param = InterfacePersonnalisation(image)
        self.interface_param.showMaximized()
        self.hide()


# Interface 2 : Personnalisation de l'interface
class InterfacePersonnalisation(QWidget):
    def __init__(self, image):
        super().__init__()
        self.setWindowTitle("Personnaliser l'image")
        self.resize(1000, 700)

        self.image_originale = image.copy()
        self.image_float = image.astype(np.float64)
        self.image_traitée = image.copy()

        # PSF taille moyenne des étoiles (comme dans erosion.py)
        self.FWHM_PSF = 2.0

        # Calculer le rayon autour des étoiles (comme dans erosion.py)
        self.ETOILES_RAYON = 6
        
        self.multitaille_active = False

        # Widgets
        self.label_image = QLabel("Image FITS chargée")
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setMinimumSize(800, 500)

        self.kernel_slider = QSlider(Qt.Horizontal)
        self.kernel_slider.setRange(3, 15)
        self.kernel_slider.setValue(5)
        self.kernel_slider.valueChanged.connect(self.mettre_a_jour_image)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(1, 20)
        self.threshold_slider.setValue(7)
        self.threshold_slider.valueChanged.connect(self.mettre_a_jour_image)

        self.bouton_enregistrer = QPushButton("Enregistrer et Comparer")
        self.bouton_enregistrer.clicked.connect(self.enregistrer_et_comparer)
        self.bouton_enregistrer.setFixedSize(380, 50)
        self.bouton_enregistrer.setStyleSheet("background-color: gray; color: white; font-size: 16px;")

        self.bouton_retour = QPushButton("Retour")
        self.bouton_retour.setFixedSize(120, 50)
        self.bouton_retour.setStyleSheet("background-color: orange; color: white; font-size: 16px;")
        self.bouton_retour.clicked.connect(self.retour_interface_choix)
        
        self.bouton_multitaille = QPushButton("Réduction multitaille : OFF")
        self.bouton_multitaille.setFixedSize(250, 50)
        self.bouton_multitaille.setStyleSheet(
            "background-color: darkred; color: white; font-size: 16px;"
        )
        self.bouton_multitaille.clicked.connect(self.toggle_multitaille)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Taille du noyau d'érosion :"))
        layout.addWidget(self.kernel_slider)
        layout.addWidget(QLabel("Seuil de détection des étoiles : "))
        layout.addWidget(self.threshold_slider)
        layout.addWidget(self.label_image)

        layout_boutons = QHBoxLayout()
        layout_boutons.addWidget(self.bouton_retour)
        layout_boutons.addWidget(self.bouton_multitaille)
        layout_boutons.addWidget(self.bouton_enregistrer)
        layout.addLayout(layout_boutons)

        self.setLayout(layout)
        self.afficher_image(self.image_traitée)

    def retour_interface_choix(self):
        self.close()
        self.interface_choix = InterfaceChoix()
        self.interface_choix.showMaximized()

    def noyau_magnitude(self, mag):
        return 15 if mag < -5 else self.kernel_slider.value() | 1

    def mettre_a_jour_image(self):
        if self.multitaille_active:
            self.mettre_a_jour_image_multitaille()
        else:
            self.mettre_a_jour_image_simple()

    def mettre_a_jour_image_simple(self):
        THRESHOLD_SIGMA = self.threshold_slider.value() / 10.0
        
        # Calcul des statistiques de fond de ciel
        # moyenne : moyenne du fond
        # mediane : valeur du fond de ciel
        # std : écart-type du bruit
        moyenne, mediane, std = sigma_clipped_stats(self.image_float, sigma=3.0)
        
        # Initialisation de l’algorithme de détection d’étoile
        daofind = DAOStarFinder(fwhm=self.FWHM_PSF, threshold=THRESHOLD_SIGMA * std)

        # Détection des étoiles sur l’image après soustraction du fond (médiane)
        # sources contient les positions et caractéristiques des étoiles détectées
        sources = daofind(self.image_float - mediane)

        # Image finale
        image_finale = self.image_originale.astype(np.float32)

        
        # Vérification qu’au moins une étoile a été détectée
        if sources is not None:
            # Masque global
            masque_total = np.zeros_like(self.image_originale, dtype=np.float32)
            for star in sources:
                # Coordonnées du centre de l’étoile détectée
                x = int(star["xcentroid"])
                y = int(star["ycentroid"])
                kernel_size = self.noyau_magnitude(star["mag"])
                cv.rectangle(masque_total,
                             (x - self.ETOILES_RAYON, y - self.ETOILES_RAYON),
                             (x + self.ETOILES_RAYON, y + self.ETOILES_RAYON),
                             1.0, -1)
            # Flou et érosion
            masque_flou = cv.GaussianBlur(masque_total, (21, 21), 0)
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            image_eroded = cv.erode(self.image_originale, kernel, iterations=1)
            image_finale = masque_flou * image_eroded + (1 - masque_flou) * image_finale

        self.image_traitée = np.clip(image_finale, 0, 255).astype(np.uint8)
        self.afficher_image(self.image_traitée)

    def mettre_a_jour_image_multitaille(self):
        THRESHOLD_SIGMA = self.threshold_slider.value() / 10.0

        # Calcul des statistiques de fond de ciel
        # moyenne : moyenne du fond
        # mediane : valeur du fond de ciel
        # std : écart-type du bruit
        moyenne, mediane, std = sigma_clipped_stats(self.image_float, sigma=3.0)

        # Initialisation de l’algorithme de détection d’étoile
        daofind = DAOStarFinder(fwhm=self.FWHM_PSF, threshold=THRESHOLD_SIGMA * std)

        # Détection des étoiles sur l’image après soustraction du fond (médiane)
        # sources contient les positions et caractéristiques des étoiles détectées  
        sources = daofind(self.image_float - mediane)

        image_finale = self.image_originale.astype(np.float32)

        # Vérification qu’au moins une étoile a été détectée
        if sources is None:
            self.image_traitée = self.image_originale
            self.afficher_image(self.image_traitée)
            return

        # Masques par taille de noyau
        kernel_sizes = [3, 15]
        masques = {
            k: np.zeros_like(self.image_originale, dtype=np.uint8)
            for k in kernel_sizes
            }

        
        for star in sources:
            # Coordonnées du centre de l’étoile détectée
            x = int(star["xcentroid"])
            y = int(star["ycentroid"])
            mag = star["mag"]

            k = 15 if mag < -5 else 3
            if k not in masques:
                continue

            # Dessin d’un carré blanc centré sur chaque étoile
            cv.rectangle(masques[k],
                         (x - self.ETOILES_RAYON, y - self.ETOILES_RAYON),
                         (x + self.ETOILES_RAYON, y + self.ETOILES_RAYON),
                         255, -1
            )

        for kernel_size, masque in masques.items():
            # On vérifie si c'est pas nul sinon on passe au suivant
            if np.count_nonzero(masque) == 0:
                continue

            
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            image_eroded = cv.erode(self.image_originale, kernel, iterations=1).astype(np.float32)

            #On met en flou comme sur erosion.py 
            masque_flou = cv.GaussianBlur(masque, (21, 21), 0) / 255.0

            # On fusionne l'image eroder et la version flou (comme demander en phase 2)
            image_finale = (
                masque_flou * image_eroded +
                (1 - masque_flou) * image_finale
            )

        self.image_traitée = np.clip(image_finale, 0, 255).astype(np.uint8)
        self.afficher_image(self.image_traitée)

    def afficher_image(self, image):
        h, w = image.shape
        qimg = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label_image.width(),
            self.label_image.height(),
            Qt.KeepAspectRatio
        )
        self.label_image.setPixmap(pixmap)

    def enregistrer_et_comparer(self):
        self.interface_comp = ComparateurApplication(self.image_originale, self.image_traitée, self)
        self.interface_comp.showMaximized()
        self.hide()
    
    def toggle_multitaille(self):
        self.multitaille_active = not self.multitaille_active

        if self.multitaille_active:
            self.bouton_multitaille.setText("Réduction multitaille : ON")
            self.bouton_multitaille.setStyleSheet(
                "background-color: darkgreen; color: white; font-size: 14px;"
            )
        else:
            self.bouton_multitaille.setText("Réduction multitaille : OFF")
            self.bouton_multitaille.setStyleSheet(
                "background-color: darkred; color: white; font-size: 14px;"
            )

        self.mettre_a_jour_image()




# Interface 3 : Comparateur Avant / Après de la photo
class ComparateurApplication(QWidget):
    def __init__(self, image_originale, image_finale, interface_personnalisation):
        super().__init__()

        self.interface_personnalisation = interface_personnalisation

        self.setWindowTitle("Comparateur Avant / Après")
        self.resize(1200, 900)

        self.image_originale = image_originale
        self.image_finale = image_finale
        self.hauteur, self.largeur = self.image_originale.shape

        self.timer_clignotement = QTimer()
        self.timer_clignotement.timeout.connect(self.clignotement)
        self.affiche_originale = True

        self.label_image = QLabel()
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setMinimumSize(1000, 600)

        self.bouton_start = QPushButton("Démarrer clignotement")
        self.bouton_start.clicked.connect(self.demarrer_clignotement)
        self.bouton_start.setStyleSheet("background-color: green; color: white;")
        self.bouton_start.setFixedSize(380, 50)

        self.bouton_stop = QPushButton("Arrêter clignotement")
        self.bouton_stop.clicked.connect(self.arreter_clignotement)
        self.bouton_stop.setStyleSheet("background-color: red; color: white;")
        self.bouton_stop.setFixedSize(380, 50)

        self.slider_comparaison = QSlider(Qt.Horizontal)
        self.slider_comparaison.setRange(0, self.largeur)
        self.slider_comparaison.setValue(self.largeur // 2)
        self.slider_comparaison.valueChanged.connect(self.comparaison_curseur)

        self.label_avant = QLabel("Avant")
        self.label_apres = QLabel("Après")
        self.label_avant.setAlignment(Qt.AlignLeft)
        self.label_apres.setAlignment(Qt.AlignRight)
        
        self.bouton_retour = QPushButton("Retour")
        self.bouton_retour.setFixedSize(120, 50)
        self.bouton_retour.setStyleSheet("background-color: orange; color: white; font-size: 16px;")
        self.bouton_retour.clicked.connect(self.retour_interface_personnalisation)

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.label_avant)
        layout_slider.addWidget(self.slider_comparaison)
        layout_slider.addWidget(self.label_apres)

        layout_boutons = QHBoxLayout()
        layout_boutons.addWidget(self.bouton_retour)
        layout_boutons.addWidget(self.bouton_start)
        layout_boutons.addWidget(self.bouton_stop)

        layout = QVBoxLayout()
        layout.addWidget(self.label_image)
        layout.addWidget(QLabel("Comparaison : Déplacez le curseur ci-dessous pour voir les changements."))
        layout.addLayout(layout_slider)
        layout.addLayout(layout_boutons)
        self.setLayout(layout)

        self.afficher(self.image_finale)

    def demarrer_clignotement(self):
        if not self.timer_clignotement.isActive():
            self.timer_clignotement.start(500)

    def arreter_clignotement(self):
        self.timer_clignotement.stop()
        self.afficher(self.image_finale)

    def clignotement(self):
        self.afficher(self.image_originale if self.affiche_originale else self.image_finale)
        self.affiche_originale = not self.affiche_originale

    def comparaison_curseur(self, position):
        image_mixte = self.image_originale.copy()
        image_mixte[:, position:] = self.image_finale[:, position:]
        
        image_mixte = cv.cvtColor(image_mixte, cv.COLOR_GRAY2BGR)
        cv.line(
            image_mixte,
            (position, 0),
            (position, self.hauteur),
            (0, 0, 255),
            2
        )

        self.afficher(image_mixte)

    def afficher(self, image):
        if len(image.shape) == 3:
                image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

        h, w = image.shape
        qimg = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label_image.width(),
            self.label_image.height(),
            Qt.KeepAspectRatio
        )
        self.label_image.setPixmap(pixmap)
    
    def retour_interface_personnalisation(self):
        self.close()
        self.interface_personnalisation.showMaximized()



# Lancement de l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = InterfaceChoix()
    fenetre.showMaximized()
    sys.exit(app.exec())