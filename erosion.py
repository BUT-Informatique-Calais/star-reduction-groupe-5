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


moyenne, mediane, std = sigma_clipped_stats(image_float, sigma=3.0)

daofind = DAOStarFinder(
    fwhm_psf = FWHM_PSF,
    threshold = THRESHOLD_SIGMA * std
)

sources = daofind(image_float - mediane)


masque = np.zeros(image.shape[:2], dtype=np.uint8)

if sources is not None:
    for star in sources:
        x = int(star['xcentroid'])
        y = int(star['ycentroid'])

        cv.circle(masque, (x, y), ETOILES_RAYON, 255, -1)

# Save the masque binaire
cv.imwrite('./results/masque_binaire.png', masque)


masque_adouci = cv.GaussianBlur(masque, (21, 21), 0)
masque_float = masque_adouci / 255.0

# Save the mask adouci 
cv.imwrite('./results/masque_adouci.png', masque_adouci)


# Define a kernel for erosion
kernel = np.ones((EROSION_KERNEL, EROSION_KERNEL), np.uint8)

# Perform erosion
eroded_image = cv.erode(image, kernel, iterations=1)

# Save the eroded image 
cv.imwrite('./results/eroded.png', eroded_image)


image_f = image.astype(np.float32)
eroded_f = eroded_image.astype(np.float32)

final = (masque_float[..., None] * eroded_f +(1 - masque_float[..., None]) * image_f) if image.ndim == 3 else  (masque_float * eroded_f + (1 - masque_float) * image_f)

final = np.clip(final, 0, 255).astype(np.uint8)

# Save the final image
cv.imwrite('./results/image_finale.png', final)


hdul.close()