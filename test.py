import sys
import cv2 as cv
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QTimer


class ComparateurApplication(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comparateur Avant / Après - SAÉ")
        self.resize(900, 700)

        self.image_originale = cv.imread("./results/original.png", cv.IMREAD_GRAYSCALE)
        self.image_finale = cv.imread("./results/image_finale.png", cv.IMREAD_GRAYSCALE)

        if self.image_originale is None or self.image_finale is None:
            raise RuntimeError("Impossible de charger les images")

        self.timer_clignotement = QTimer()
        self.timer_clignotement.timeout.connect(self.clignotement)
        self.affiche_originale = True

        self.label_image = QLabel()
        self.label_image.setAlignment(Qt.AlignCenter)
        self.label_image.setMinimumSize(800, 500)

        self.bouton_clignotement = QPushButton("Clignotement ON / OFF")
        self.bouton_clignotement.clicked.connect(self.toggle_clignotement)

        layout = QVBoxLayout()
        layout.addWidget(self.label_image)
        layout.addWidget(self.bouton_clignotement)

        self.setLayout(layout)

        self.afficher_image_finale()

    def toggle_clignotement(self):
        if self.timer_clignotement.isActive():
            self.timer_clignotement.stop()
        else:
            self.timer_clignotement.start(500)

    def clignotement(self):
        if self.affiche_originale:
            self.afficher(self.image_originale)
        else:
            self.afficher(self.image_finale)

        self.affiche_originale = not self.affiche_originale

    def afficher_difference(self):
        difference = cv.absdiff(self.image_originale, self.image_finale)
        self.afficher(difference)

    def afficher_image_finale(self):
        self.afficher(self.image_finale)

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
