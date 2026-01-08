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

        self.bouton_ouvrir = QPushButton("Ouvrir FITS")
        self.bouton_ouvrir.clicked.connect(self.ouvrir_fits)

        layout = QVBoxLayout()
        layout.addWidget(self.bouton_ouvrir)
        self.setLayout(layout)

    def ouvrir_fits(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un FITS", "", "*.fits")
        if not path:
            return

        # Lecture de l'image chosie
        data = fits.getdata(path)
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

        self.FWHM_PSF = 2.0
        self.ETOILES_RAYON = 6

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

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Taille du noyau d’érosion (étoiles faibles)"))
        layout.addWidget(self.kernel_slider)
        layout.addWidget(QLabel("Seuil de détection des étoiles"))
        layout.addWidget(self.threshold_slider)
        layout.addWidget(self.label_image)
        layout.addWidget(self.bouton_enregistrer)
        self.setLayout(layout)

        self.afficher_image(self.image_traitée)

    def noyau_magnitude(self, mag):
        return 15 if mag < -5 else self.kernel_slider.value() | 1 

    def mettre_a_jour_image(self):
        THRESHOLD_SIGMA = self.threshold_slider.value() / 10.0

        # Calcul des statistiques de fond de ciel
        # moyenne : moyenne du fond
        # mediane : valeur du fond de ciel
        # std : écart-type du bruit
        moyenne, mediane, std = sigma_clipped_stats(self.image_float, sigma=3.0)

        daofind = DAOStarFinder(fwhm=self.FWHM_PSF, threshold=THRESHOLD_SIGMA * std)
        sources = daofind(self.image_float - mediane)

        # Image finale
        image_finale = self.image_originale.astype(np.float32)

        if sources is not None:
            # Masque global
            masque_total = np.zeros_like(self.image_originale, dtype=np.float32)
            for star in sources:
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
        self.interface_comp = ComparateurApplication(self.image_originale, self.image_traitée)
        self.interface_comp.showMaximized()
        self.close()


# Interface 3 : Comparateur Avant / Après de la photo
class ComparateurApplication(QWidget):
    def __init__(self, image_originale, image_finale):
        super().__init__()
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

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.label_avant)
        layout_slider.addWidget(self.slider_comparaison)
        layout_slider.addWidget(self.label_apres)

        layout_boutons = QHBoxLayout()
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
        self.afficher(image_mixte)

    def afficher(self, image):
        h, w = image.shape
        qimg = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label_image.width(),
            self.label_image.height(),
            Qt.KeepAspectRatio
        )
        self.label_image.setPixmap(pixmap)


# Lancement de l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = InterfaceChoix()
    fenetre.showMaximized()
    sys.exit(app.exec())
