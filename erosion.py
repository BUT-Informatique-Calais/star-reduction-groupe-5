from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
import matplotlib.pyplot as plt

import matplotlib.pyplot as plt
import cv2 as cv
import numpy as np
import os

# Open and read the FITS file
fits_file = './examples/HorseHead.fits'
output_dir = './results'
os.makedirs(output_dir, exist_ok=True)

# Taille du noyau pour l'érosion
EROSION_KERNEL = 5

# Calculer le rayon autour des étoiles
ETOILES_RAYON = 6 

# PSF taille moyenne des étoiles
FWHM_PSF = 2.0  

# Comme le nom de la fonction de DAOStarFinder
THRESHOLD_SIGMA = 0.7  


def kernel_magnitude(mag):
    """     
    Plus l'étoile est brillante (mag faible),
    plus le noyau d'érosion est grand
    """
    if mag < -5:
        return 15
    else:
        return 3

hdul = fits.open(fits_file)

# Display information about the file
hdul.info()

# Access the data from the primary HDU
data = hdul[0].data

# Access header information
header = hdul[0].header


# Handle both monochrome and color images
if data.ndim == 3:
    # Color image - need to transpose to (height, width, channels)
    if data.shape[0] == 3:  # If channels are first: (3, height, width)
        data = np.transpose(data, (1, 2, 0))
    # If already (height, width, 3), no change needed

    # Normalize the entire image to [0, 1] for matplotlib
    data_normalized = (data - data.min()) / (data.max() - data.min())
    
    # Save the data as a png image (no cmap for color images)
    plt.imsave('./results/original.png', data_normalized)

    # Normalize each channel separately to [0, 255] for OpenCV
    image = np.zeros_like(data, dtype='uint8')
    for i in range(data.shape[2]):
        channel = data[:, :, i]
        image[:, :, i] = ((channel - channel.min()) / (channel.max() - channel.min()) * 255).astype('uint8')

    # Pour DAOStarFinder → passage en niveaux de gris
    image_gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    image_float = image_gray.astype(np.float64)

else:
    # Monochrome image
    plt.imsave('./results/original.png', data, cmap='gray')
    
    # Convert to uint8 for OpenCV
    image = ((data - data.min()) / (data.max() - data.min()) * 255).astype('uint8')

    image_float = data.astype(np.float64)


# Calcul des statistiques de fond de ciel
# moyenne : moyenne du fond
# mediane : valeur du fond de ciel
# std : écart-type du bruit
moyenne, mediane, std = sigma_clipped_stats(image_float, sigma=3.0)

# Initialisation de l’algorithme de détection d’étoiles
daofind = DAOStarFinder(
    fwhm = FWHM_PSF,
    threshold = THRESHOLD_SIGMA * std
)

# Détection des étoiles sur l’image après soustraction du fond (médiane)
# sources contient les positions et caractéristiques des étoiles détectées
sources = daofind(image_float - mediane)

if sources is None:
    print("Nombre d'étoiles détectées : 0")
else:
    print(f"Nombre d'étoiles détectées : {len(sources)}")


# Masques par taille de noyau
kernel_sizes = [3, 15]

masque = {
    k: np.zeros(image.shape[:2], dtype=np.uint8)
    for k in kernel_sizes
}
# Vérification qu’au moins une étoile a été détectée
if sources is not None:
    for star in sources:
        # Coordonnées du centre de l’étoile détectée
        x = int(star['xcentroid'])
        y = int(star['ycentroid'])
        mag = star["mag"]

        k = kernel_magnitude(mag)
        if k not in masque:
            continue

        # Dessin d’un carré blanc centré sur chaque étoile
        cv.rectangle(masque[k], (x - ETOILES_RAYON, y - ETOILES_RAYON), (x + ETOILES_RAYON, y + ETOILES_RAYON), 255,-1)


for k, m in masque.items():
    cv.imwrite(f'./results/masque_kernel_{k}.png', m)


# Define a kernel for erosion
kernel = np.ones((EROSION_KERNEL, EROSION_KERNEL), np.uint8)

# Perform erosion
eroded_image = cv.erode(image, kernel, iterations=1)

# Save the eroded image 
cv.imwrite('./results/eroded.png', eroded_image)


image_finale = image.astype(np.float32)

for kernel_size, masque in masque.items():
    if np.count_nonzero(masque) == 0:
        continue

    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    image_eroded = cv.erode(image, kernel, iterations=1).astype(np.float32)

    masque_flou = cv.GaussianBlur(masque, (21, 21), 0) / 255.0

    if image.ndim == 3:
        masque_flou = masque_flou[..., None]

    image_finale = (masque_flou * image_eroded +(1 - masque_flou) * image_finale)

image_finale = np.clip(image_finale, 0, 255).astype(np.uint8)
cv.imwrite(f'./results/image_finale.png', image_finale)