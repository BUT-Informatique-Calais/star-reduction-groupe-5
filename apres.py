import sys
import cv2 as cv
import numpy as np

from PySide6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QSlider)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QTimer


class ComparateurApplication(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comparateur Avant / Après")
        self.resize(900, 700)

        # CHarger les deux images pour les afficher ensuite
        self.image_originale = cv.imread("./results/original.png", cv.IMREAD_GRAYSCALE)
        self.image_finale = cv.imread("./results/image_finale.png", cv.IMREAD_GRAYSCALE)

        if self.image_originale is None or self.image_finale is None:
            raise RuntimeError("Impossible de charger les images")

        self.hauteur, self.largeur = self.image_originale.shape

        # Timer qui permet de jongler entre les deux images
        self.timer_clignotement = QTimer()
        self.timer_clignotement.timeout.connect(self.clignotement)
        self.affiche_originale = True

        self.label_image = QLabel()
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setMinimumSize(1000, 600)

        # Bouton pour démarrer le clignotement
        self.bouton_start = QPushButton("Démarrer clignotement") # Texte dans le bouton
        self.bouton_start.clicked.connect(self.demarrer_clignotement) # Relié à la fonction du clignotement
        self.bouton_start.setStyleSheet("background-color: green; color: white;") # couleur du bouton et du texte
        self.bouton_start.setFixedSize(380, 50)  # largeur, hauteur du bouton

        # Bouton pour arrêter le clignotement
        self.bouton_stop = QPushButton("Arrêter clignotement")
        self.bouton_stop.clicked.connect(self.arreter_clignotement)
        self.bouton_stop.setStyleSheet("background-color: red; color: white;")
        self.bouton_stop.setFixedSize(380, 50)

        # SLider qui permet de faire la comparaison interactive entre les deux images
        self.slider_comparaison = QSlider(Qt.Horizontal)
        self.slider_comparaison.setMinimum(0)
        self.slider_comparaison.setMaximum(self.largeur)
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


        # Regroupe les boutons de clignotement
        layout_boutons = QHBoxLayout()
        layout_boutons.addWidget(self.bouton_start)
        layout_boutons.addWidget(self.bouton_stop)

        # Assemblage de toute l'interface
        layout = QVBoxLayout()
        layout.addWidget(self.label_image)
        layout.addWidget(QLabel("Comparaison : Déplacez le cursor ci-dessous pour voir les changements."))
        layout.addLayout(layout_slider)
        layout.addLayout(layout_boutons)
        self.setLayout(layout)
        self.afficher(self.image_finale)

    # Permet de démarrer le clignotement
    def demarrer_clignotement(self):
        if not self.timer_clignotement.isActive():
            self.timer_clignotement.start(500)

    # Permet d'arrêter le clignotement
    def arreter_clignotement(self):
        self.timer_clignotement.stop()
        self.afficher(self.image_finale)

    # Permet de jongler entre les deux images
    def clignotement(self):
        if self.affiche_originale:
            self.afficher(self.image_originale)
        else:
            self.afficher(self.image_finale)

        self.affiche_originale = not self.affiche_originale

    # Permet de faire la comparaison interactive entre les deux images
    def comparaison_curseur(self, position):
        image_mixte = np.zeros_like(self.image_originale)

        image_mixte[:, :position] = self.image_originale[:, :position]
        image_mixte[:, position:] = self.image_finale[:, position:]

        self.afficher(image_mixte)

    # Permet d'afficher une image dans le label
    def afficher(self, image):
        h, w = image.shape
        qimage = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.label_image.width(),
            self.label_image.height(),
            Qt.KeepAspectRatio
        )
        self.label_image.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = ComparateurApplication()
    fenetre.show()
    sys.exit(app.exec())
